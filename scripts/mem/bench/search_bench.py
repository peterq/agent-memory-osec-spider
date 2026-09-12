#!/usr/bin/env python3
"""检索方案对比基准: 量化 mem.py search 不同配置(词法模式/语义模型/RRF 参数/切块大小/文档 boost)
在 gold.jsonl(原始问法) 和 gold_paraphrased.jsonl(改写问法, 存在则跑) 上的检索质量与耗时。

直接 import scripts/mem/mem.py 里的 load_all/lexical_scores/semantic_index/semantic_scores/fuse_scores,
不 subprocess 逐条跑, 且尽量按 (jieba开关, 语义模型, 切块大小) 分组复用词法/语义打分,
RRF 融合参数(K/语义权重/min_sim/boost)在同一组打分结果上"重算融合"几乎零成本, 不重复计时。

用法:
  python3 scripts/mem/bench/search_bench.py                 # 跑全部配置, 打印 Markdown 表格到 stdout
  python3 scripts/mem/bench/search_bench.py --quick          # 只跑核心配置(跳过 chunk/模型扫参), 用于冒烟
  python3 scripts/mem/bench/search_bench.py --skip-models bge-m3   # 跳过指定模型(未装/下载失败时)
  python3 scripts/mem/bench/search_bench.py --dump-json out.json   # 额外把逐 query 明细写成 json, 供失败案例分析

依赖: 复用 ROOT 现有环境里的 jieba / fastembed / numpy(已安装), 不额外装包。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
MEM_DIR = BENCH_DIR.parent
ROOT = MEM_DIR.parent.parent
sys.path.insert(0, str(MEM_DIR))
import mem  # noqa: E402

ALWAYS_EXCLUDED = True  # 题面要求: 排除 load: always 文件


def load_gold(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def get_docs():
    docs = mem.load_all()
    if ALWAYS_EXCLUDED:
        docs = [d for d in docs if d.fm.get("load") != "always"]
    return docs


# ---------- 词法/语义打分缓存(按 query 维度, 组内复用) ----------

def set_jieba(enabled: bool):
    """临时切换 mem.tokenize 的分词方式: enabled=True 用 jieba, False 强制退化为字二元切分。
    不改 mem.py 的默认加载逻辑, 只是运行期切换模块级缓存 _jieba, 不影响其他进程/后续默认调用。"""
    if enabled:
        mem._jieba = None  # 触发重新 import jieba
        mem._get_jieba()
        if mem._jieba is False:
            print("!! 警告: jieba 未安装, 无法测试 lexical-jieba", file=sys.stderr)
    else:
        mem._jieba = False  # 强制退化为 bigram, 不再尝试 import


class LexCache:
    def __init__(self, docs):
        self.docs = docs
        self.cache: dict[str, dict] = {}
        self.time_total = 0.0
        self.n = 0

    def get(self, query: str) -> dict:
        if query not in self.cache:
            t0 = time.perf_counter()
            q = mem.tokenize(query)
            lex = mem.lexical_scores(self.docs, q) if q else {}
            self.time_total += time.perf_counter() - t0
            self.n += 1
            self.cache[query] = lex
        return self.cache[query]

    def avg_ms(self):
        return (self.time_total / self.n * 1000) if self.n else 0.0


class SemCache:
    def __init__(self, docs, model_name, chunk_chars, quiet=True):
        self.docs = docs
        t0 = time.perf_counter()
        self.model, self.idx = mem.semantic_index(docs, quiet=quiet, model_name=model_name, chunk_chars=chunk_chars)
        self.index_build_s = time.perf_counter() - t0
        self.cache: dict[str, dict] = {}
        self.time_total = 0.0
        self.n = 0
        self.ok = self.model is not None

    def get(self, query: str) -> dict:
        if not self.ok:
            return {}
        if query not in self.cache:
            t0 = time.perf_counter()
            sem = mem.semantic_scores(self.model, self.idx, self.docs, query)
            self.time_total += time.perf_counter() - t0
            self.n += 1
            self.cache[query] = sem
        return self.cache[query]

    def avg_ms(self):
        return (self.time_total / self.n * 1000) if self.n else 0.0


# ---------- 评测指标 ----------

def eval_config(gold: list[dict], by: dict, lex_of, sem_of, mode: str,
                 K: float, sem_weight: float, min_sim: float, boost: bool,
                 record_fail=None) -> dict:
    """对一批 (query, expected) 跑一次配置, 返回 Hit@1/3/5/MRR。record_fail 非空时把没命中 Hit@5 的
    (topic, query, expected, top5) 记进去, 供失败案例分析。"""
    hit1 = hit3 = hit5 = 0
    mrr_sum = 0.0
    n = 0
    for item in gold:
        expected = set(item["expected"])
        for q in item["queries"]:
            lex = lex_of(q)
            sem = sem_of(q)
            ranked = mem.fuse_scores(lex, sem, by, mode=mode, K=K, sem_weight=sem_weight,
                                      min_sim=min_sim, boost=boost)
            rels = [r for r, _ in ranked]
            n += 1
            first_rank = None
            for i, r in enumerate(rels):
                if r in expected:
                    first_rank = i + 1
                    break
            if first_rank:
                mrr_sum += 1.0 / first_rank
                if first_rank <= 1:
                    hit1 += 1
                if first_rank <= 3:
                    hit3 += 1
                if first_rank <= 5:
                    hit5 += 1
            if record_fail is not None and (first_rank is None or first_rank > 5):
                record_fail.append({
                    "topic": item["topic"], "query": q, "expected": sorted(expected),
                    "top5": rels[:5], "first_rank": first_rank,
                })
    return {
        "n": n,
        "hit1": hit1 / n if n else 0.0,
        "hit3": hit3 / n if n else 0.0,
        "hit5": hit5 / n if n else 0.0,
        "mrr": mrr_sum / n if n else 0.0,
    }


# ---------- 配置定义 ----------

MODELS = {
    "bge-small-zh": "BAAI/bge-small-zh-v1.5",
    "bge-m3": "BAAI/bge-m3",
    "jina-v2-zh": "jinaai/jina-embeddings-v2-base-zh",
}
DEFAULT_MODEL = "bge-small-zh"
DEFAULT_CHUNK = mem.CHUNK_CHARS   # 600
DEFAULT_K = 30.0
DEFAULT_W = 1.3
DEFAULT_MINSIM = 0.35


def build_config_list(skip_models: set[str], quick: bool) -> list[dict]:
    cfgs = []
    # 1) 词法两种分词
    cfgs.append({"name": "lexical-bigram", "mode": "lexical", "jieba": False})
    cfgs.append({"name": "lexical-jieba", "mode": "lexical", "jieba": True})
    # 2) 语义-only, 三个模型
    for mname in MODELS:
        if mname in skip_models:
            continue
        cfgs.append({"name": f"semantic-only-{mname}", "mode": "semantic", "jieba": True,
                     "model": mname, "chunk": DEFAULT_CHUNK, "min_sim": DEFAULT_MINSIM})
    # 3) hybrid 默认(基线) + 换模型
    cfgs.append({"name": "hybrid-default(bge-small-zh)", "mode": "hybrid", "jieba": True,
                 "model": DEFAULT_MODEL, "chunk": DEFAULT_CHUNK,
                 "K": DEFAULT_K, "w": DEFAULT_W, "min_sim": DEFAULT_MINSIM, "boost": True,
                 "is_baseline": True})
    if not quick:
        for mname in MODELS:
            if mname == DEFAULT_MODEL or mname in skip_models:
                continue
            cfgs.append({"name": f"hybrid-{mname}", "mode": "hybrid", "jieba": True,
                         "model": mname, "chunk": DEFAULT_CHUNK,
                         "K": DEFAULT_K, "w": DEFAULT_W, "min_sim": DEFAULT_MINSIM, "boost": True})
        # 4) RRF 参数扫描(基于 bge-small-zh, chunk=600)
        for w in (1.0, 1.6, 2.0):  # 1.3 已是基线
            cfgs.append({"name": f"rrf-w{w}", "mode": "hybrid", "jieba": True,
                         "model": DEFAULT_MODEL, "chunk": DEFAULT_CHUNK,
                         "K": DEFAULT_K, "w": w, "min_sim": DEFAULT_MINSIM, "boost": True})
        for K in (10.0, 60.0):  # 30 已是基线
            cfgs.append({"name": f"rrf-K{int(K)}", "mode": "hybrid", "jieba": True,
                         "model": DEFAULT_MODEL, "chunk": DEFAULT_CHUNK,
                         "K": K, "w": DEFAULT_W, "min_sim": DEFAULT_MINSIM, "boost": True})
        for ms in (0.3, 0.45):  # 0.35 已是基线
            cfgs.append({"name": f"rrf-minsim{ms}", "mode": "hybrid", "jieba": True,
                         "model": DEFAULT_MODEL, "chunk": DEFAULT_CHUNK,
                         "K": DEFAULT_K, "w": DEFAULT_W, "min_sim": ms, "boost": True})
        # 5) 切块大小扫描(600 已是基线, 需要重新建索引)
        for ch in (300, 1200):
            cfgs.append({"name": f"chunk{ch}", "mode": "hybrid", "jieba": True,
                         "model": DEFAULT_MODEL, "chunk": ch,
                         "K": DEFAULT_K, "w": DEFAULT_W, "min_sim": DEFAULT_MINSIM, "boost": True})
        # 6) boost 开关(on 已是基线)
        cfgs.append({"name": "boost-off", "mode": "hybrid", "jieba": True,
                     "model": DEFAULT_MODEL, "chunk": DEFAULT_CHUNK,
                     "K": DEFAULT_K, "w": DEFAULT_W, "min_sim": DEFAULT_MINSIM, "boost": False})
    return cfgs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="只跑核心配置(词法两种+语义三模型+hybrid基线), 跳过 RRF/chunk 扫参")
    ap.add_argument("--skip-models", default="", help="逗号分隔, 跳过指定模型简称(bge-small-zh/bge-m3/jina-v2-zh)")
    ap.add_argument("--dump-json", help="把逐 query 明细(含失败案例)写到此 json 文件")
    ap.add_argument("--gold", default=str(BENCH_DIR / "gold.jsonl"))
    ap.add_argument("--paraphrased", default=str(BENCH_DIR / "gold_paraphrased.jsonl"))
    a = ap.parse_args()

    skip_models = set(x for x in a.skip_models.split(",") if x)
    gold_sets = {}
    g1 = load_gold(Path(a.gold))
    if g1:
        gold_sets["原始问法(gold.jsonl)"] = g1
    g2 = load_gold(Path(a.paraphrased))
    if g2:
        gold_sets["改写问法(gold_paraphrased.jsonl)"] = g2
    if not gold_sets:
        sys.exit("没有可用的 gold 文件")

    docs = get_docs()
    by = {d.mrel: d for d in docs}
    print(f"# 检索方案对比 (文档 {len(docs)} 篇, 已排除 load:always)\n", file=sys.stderr)
    for gname, g in gold_sets.items():
        nq = sum(len(it["queries"]) for it in g)
        print(f"- {gname}: {len(g)} topic / {nq} query", file=sys.stderr)

    cfgs = build_config_list(skip_models, a.quick)

    # 按 (jieba, model, chunk) 分组复用打分, 组内多个融合参数变体只是重算 fuse_scores(近乎零成本)
    lex_cache_by_jieba: dict[bool, LexCache] = {}
    sem_cache_by_key: dict[tuple, SemCache] = {}
    index_build_time: dict[str, float] = {}

    def get_lex_cache(jieba_on: bool) -> LexCache:
        if jieba_on not in lex_cache_by_jieba:
            set_jieba(jieba_on)
            lex_cache_by_jieba[jieba_on] = LexCache(docs)
        return lex_cache_by_jieba[jieba_on]

    def get_sem_cache(model_key: str, chunk: int) -> SemCache:
        key = (model_key, chunk)
        if key not in sem_cache_by_key:
            model_full = MODELS[model_key]
            print(f"(建索引: {model_key} chunk={chunk} …)", file=sys.stderr)
            sc = SemCache(docs, model_full, chunk)
            sem_cache_by_key[key] = sc
            index_build_time[f"{model_key}@{chunk}"] = sc.index_build_s
            if not sc.ok:
                print(f"!! {model_key} 加载失败, 跳过依赖它的配置", file=sys.stderr)
        return sem_cache_by_key[key]

    results = []  # (gold_name, cfg_name, metrics, lex_ms, sem_ms)
    fails_by_gold: dict[str, list] = defaultdict(list)

    for cfg in cfgs:
        jieba_on = cfg.get("jieba", True)
        lexc = get_lex_cache(jieba_on)
        semc = None
        model_key = cfg.get("model")
        if model_key:
            if model_key in skip_models:
                print(f"跳过 {cfg['name']}(模型 {model_key} 已跳过)", file=sys.stderr)
                continue
            semc = get_sem_cache(model_key, cfg.get("chunk", DEFAULT_CHUNK))
            if not semc.ok:
                continue

        def lex_of(q, _lexc=lexc):
            return _lexc.get(q)

        def sem_of(q, _semc=semc):
            return _semc.get(q) if _semc else {}

        for gname, g in gold_sets.items():
            is_baseline_paraphrase_final = (gname.startswith("改写") and cfg.get("is_baseline"))
            fails = [] if is_baseline_paraphrase_final else None
            metrics = eval_config(g, by, lex_of, sem_of, cfg["mode"],
                                   K=cfg.get("K", DEFAULT_K), sem_weight=cfg.get("w", DEFAULT_W),
                                   min_sim=cfg.get("min_sim", DEFAULT_MINSIM), boost=cfg.get("boost", True),
                                   record_fail=fails)
            lex_ms = lexc.avg_ms()
            sem_ms = semc.avg_ms() if semc else 0.0
            results.append({
                "gold": gname, "cfg": cfg["name"], **metrics,
                "lex_ms": lex_ms, "sem_ms": sem_ms,
                "index_build_s": index_build_time.get(f"{model_key}@{cfg.get('chunk', DEFAULT_CHUNK)}", 0.0) if model_key else 0.0,
            })
            if fails:
                fails_by_gold[gname] = fails

    # 也单独跑一遍「原始问法」下 hybrid-default 的失败案例(若改写问法不存在, 用原始问法兜底分析)
    if "原始问法(gold.jsonl)" in gold_sets and "改写问法(gold_paraphrased.jsonl)" not in gold_sets:
        base = next(c for c in cfgs if c.get("is_baseline"))
        jieba_on = True
        lexc = get_lex_cache(jieba_on)
        semc = get_sem_cache(base["model"], base["chunk"])
        fails = []
        eval_config(gold_sets["原始问法(gold.jsonl)"], by, lambda q: lexc.get(q), lambda q: semc.get(q),
                    base["mode"], K=base["K"], sem_weight=base["w"], min_sim=base["min_sim"], boost=base["boost"],
                    record_fail=fails)
        fails_by_gold["原始问法(gold.jsonl)"] = fails

    # ---------- 输出 Markdown ----------
    print("## 配置对比结果\n")
    for gname in gold_sets:
        print(f"### {gname}\n")
        print("| 配置 | Hit@1 | Hit@3 | Hit@5 | MRR | 词法ms/query | 语义ms/query | 语义建索引(s) |")
        print("|---|---|---|---|---|---|---|---|")
        for r in results:
            if r["gold"] != gname:
                continue
            print(f"| {r['cfg']} | {r['hit1']:.3f} | {r['hit3']:.3f} | {r['hit5']:.3f} | {r['mrr']:.3f} "
                  f"| {r['lex_ms']:.2f} | {r['sem_ms']:.2f} | {r['index_build_s']:.1f} |")
        print()

    print("## 失败案例(未命中 Hit@5)\n")
    for gname, fails in fails_by_gold.items():
        print(f"### {gname} 下 hybrid-default 的失败案例 (共 {len(fails)} 条 query 未命中)\n")
        topic_fail_count = Counter = defaultdict(int)
        for f in fails:
            topic_fail_count[f["topic"]] += 1
        top5_topics = sorted(topic_fail_count.items(), key=lambda x: -x[1])[:5]
        for topic, cnt in top5_topics:
            print(f"- **{topic}** (错 {cnt} 条 query)")
            for f in fails:
                if f["topic"] == topic:
                    print(f"  - query: {f['query']!r}")
                    print(f"    expected: {f['expected']}")
                    print(f"    实际top5: {f['top5']}")
        print()

    if a.dump_json:
        dump = {
            "results": results,
            "fails_by_gold": {k: v for k, v in fails_by_gold.items()},
        }
        Path(a.dump_json).write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"(逐条明细已写入 {a.dump_json})", file=sys.stderr)


if __name__ == "__main__":
    main()
