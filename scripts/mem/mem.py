#!/usr/bin/env python3
"""agent-memory 加载/检索/体检工具。核心功能零依赖; 装 jieba/fastembed 后检索质量更好(见 requirements.txt)。

子命令:
  boot                       会话启动包: 从全部文件的 Front Matter 生成紧凑目录(含 questions)
  index --write              把启动包写成 agent-memory/01-index.md(索引是生成物, 禁止手改)
  outline <file>...          输出文件章节结构(标题/起止行/字数), 用于决定只读哪一段
  body <file> [--section 标题|--lines a:b] [--no-fm]   只输出正文(默认剥离 Front Matter), 可选只取某章节
  search <关键词>... [-k N] [--dir lessons,...]        词法(jieba+BM25)+语义(bge-small-zh)融合检索, 未装依赖自动退化
  embed                      预热/刷新 embedding 缓存(search 也会自动增量刷新)
  lint                       体检: 元数据缺失/超长/悬空引用/updated_at 落后 git/valid_until 过期/索引过期
  stat                       统计各目录字数、始终加载体积等
  dup                        跨文件重复段落检测(量化 overview/tasks/sessions 之间的复制粘贴)
  recent [--days N]          用 git 历史列出最近变更, 替代手工维护的"最近更新"

用法示例:
  scripts/mem/mem.py boot
  scripts/mem/mem.py search 代理池 无数据 -k 5
  scripts/mem/mem.py outline agent-memory/lessons/patterns-长周期生产巡检.md
  scripts/mem/mem.py body agent-memory/lessons/patterns-长周期生产巡检.md --section 实测数据
"""
from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEM = ROOT / "agent-memory"

PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
DIR_ORDER = ["", "current", "decisions", "procedures", "lessons", "knowledge", "sessions", "archive"]

# ---------- 解析 ----------

@dataclass
class Doc:
    path: Path
    fm: dict = field(default_factory=dict)
    body_start: int = 0            # 正文起始行号(0-based), Front Matter 之后
    lines: list[str] = field(default_factory=list)

    @property
    def rel(self) -> str:
        return str(self.path.relative_to(ROOT))

    @property
    def mrel(self) -> str:
        return str(self.path.relative_to(MEM))

    @property
    def body(self) -> str:
        return "".join(self.lines[self.body_start:])

    @property
    def chars(self) -> int:
        return sum(len(l) for l in self.lines)

    def headings(self) -> list[tuple[int, int, str]]:
        """返回 (行号0-based, 级别, 标题文本), 跳过代码块内的 #。"""
        out, in_code = [], False
        for i, l in enumerate(self.lines[self.body_start:], start=self.body_start):
            if l.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", l)
            if m:
                out.append((i, len(m.group(1)), m.group(2)))
        return out

    def sections(self) -> list[tuple[str, int, int, int]]:
        """返回 (标题, 起始行, 结束行(不含), 字数)。"""
        hs = self.headings()
        res = []
        for idx, (ln, lvl, title) in enumerate(hs):
            end = len(self.lines)
            for ln2, lvl2, _ in hs[idx + 1:]:
                if lvl2 <= lvl:
                    end = ln2
                    break
            res.append((("  " * (lvl - 1)) + title, ln, end, sum(len(x) for x in self.lines[ln:end])))
        return res


def _parse_scalar(v: str):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [x.strip().strip("'\"") for x in re.split(r"[,，]", inner) if x.strip()] if inner else []
    return v.strip("'\"")


def parse_front_matter(lines: list[str]) -> tuple[dict, int]:
    """极简 YAML 子集解析(标量/行内列表/块列表), 足够覆盖本仓库的 Front Matter。"""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fm, i, key = {}, 1, None
    while i < len(lines):
        l = lines[i].rstrip("\n")
        if l.strip() == "---":
            return fm, i + 1
        if re.match(r"^\s+-\s", l) and key:
            item = re.sub(r"^\s+-\s*", "", l)
            item = re.sub(r"\s+#.*$", "", item)  # 去掉行尾 # 注释
            item = re.sub(r"\s*[（(].*$", "", item)  # 去掉行尾 (说明) 注释
            fm.setdefault(key, [])
            if isinstance(fm[key], list):
                fm[key].append(item.strip().strip("'\""))
        else:
            m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", l)
            if m:
                key, val = m.group(1), m.group(2)
                fm[key] = _parse_scalar(val) if val.strip() else []
        i += 1
    return fm, 0


def load_all(subdirs: list[str] | None = None) -> list[Doc]:
    docs = []
    for p in sorted(MEM.rglob("*.md")):
        rel = p.relative_to(MEM)
        top = rel.parts[0] if len(rel.parts) > 1 else ""
        if subdirs is not None and top not in subdirs:
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        fm, start = parse_front_matter(lines)
        docs.append(Doc(p, fm, start, lines))
    return docs


def resolve(arg: str) -> Path:
    for cand in (Path(arg), ROOT / arg, MEM / arg):
        if cand.is_file():
            return cand.resolve()
    sys.exit(f"找不到文件: {arg}")


def load_one(arg: str) -> Doc:
    p = resolve(arg)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    fm, start = parse_front_matter(lines)
    return Doc(p, fm, start, lines)


def _kw(fm: dict) -> list[str]:
    k = fm.get("keywords", [])
    return k if isinstance(k, list) else [str(k)]


def _date(fm: dict, key: str) -> str:
    v = str(fm.get(key, ""))
    return v[:10]

# ---------- boot ----------

def _questions(fm: dict) -> list[str]:
    q = fm.get("questions", [])
    return q if isinstance(q, list) else [str(q)]


def render_boot(docs: list[Doc], kw: int = 3, sessions: bool = False, recent_sessions: int = 3, with_questions: bool = True,
                summary_max: int = 70, max_questions: int = 3) -> str:
    """评测(2026-09-12): 紧凑版(关键词 3 个、summary 截断)比全量更准, 噪声更少。archive/ 只给计数不列条目。
    2026-09-16: 启动包逼近 20,000 上限, questions 只给 critical/high 文件展示且最多 3 条; medium/low 的 questions 仍参与 search 检索。"""
    by_dir: dict[str, list[Doc]] = defaultdict(list)
    for d in docs:
        parts = d.path.relative_to(MEM).parts
        by_dir[parts[0] if len(parts) > 1 else ""].append(d)
    out = [f"# agent-memory 启动包（脚本生成, {len(docs)} 文件）— 格式: 路径 | 优先级 | 更新 | summary | 关键词; ? 后为该文件能回答的问题"]
    for top in DIR_ORDER + sorted(set(by_dir) - set(DIR_ORDER)):
        if top not in by_dir:
            continue
        items = by_dir[top]
        if top == "archive":
            out.append(f"\n## archive/ ({len(items)} 个, 已归档不列出; 需要时 mem.py search --dir archive)")
            continue
        if top == "sessions" and not sessions:
            recent = sorted(items, key=lambda d: _date(d.fm, "updated_at"), reverse=True)[:recent_sessions]
            out.append(f"\n## sessions/ ({len(items)} 个, 仅列最近 {len(recent)} 个; 其余用 mem.py search 找)")
            items = recent
        else:
            out.append(f"\n## {top + '/' if top else '根目录'} ({len(items)})")
        items = sorted(items, key=lambda d: (PRIORITY_RANK.get(str(d.fm.get("priority")), 9), d.mrel))
        for d in items:
            st = d.fm.get("status", "")
            flag = "" if st == "active" else f" [{st}]"
            kws = "、".join(_kw(d.fm)[:kw])
            sm = str(d.fm.get("summary", ""))
            if len(sm) > summary_max:
                sm = sm[:summary_max - 1] + "…"
            line = f"- {d.mrel}{flag} | {str(d.fm.get('priority','?'))[:4]} | {_date(d.fm,'updated_at')} | {sm} | {kws}"
            show_q = with_questions and str(d.fm.get("priority")) in ("critical", "high")
            qs = _questions(d.fm) if show_q else []
            if qs:
                line += "\n  ? " + " / ".join(qs[:max_questions])
            out.append(line)
    return "\n".join(out)


def cmd_boot(a):
    docs = load_all()
    text = render_boot(docs, kw=a.kw, sessions=a.sessions, recent_sessions=a.recent_sessions, with_questions=not a.no_questions)
    print(text)
    print(f"\n<!-- 启动包 {len(text)} 字; 检索: mem.py search <问题>; 看结构: mem.py outline <file>; 读正文: mem.py body <file> --section <标题> -->")


INDEX_HEADER = """---
title: 记忆索引（脚本生成）
type: index
status: active
created_at: 2026-09-02T10:55:00+08:00
updated_at: {now}
priority: critical
keywords: [索引, 导航, 启动包, mem.py]
summary: 由 scripts/mem/mem.py index --write 从各文件 Front Matter 自动生成，禁止手工编辑；改 summary/keywords/questions 后重新生成
load: always
---

# 记忆索引（脚本生成，勿手改）

本文件 = `scripts/mem/mem.py boot --kw {kw}` 的输出快照。找文件先看这里；找不到就 `mem.py search <自然语言问题>`；
定位到文件后 `mem.py outline <file>` 看章节，再 `mem.py body <file> --section <标题>` 只读需要的一段。
维护方式：改目标文件 Front Matter（summary / keywords / questions），然后运行 `scripts/mem/mem.py index --write`。

"""


def cmd_index(a):
    docs = [d for d in load_all() if d.mrel != "01-index.md"]
    now = datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).isoformat()
    text = INDEX_HEADER.format(now=now, kw=a.kw) + render_boot(docs, kw=a.kw, sessions=False, recent_sessions=a.recent_sessions) + "\n"
    if a.write:
        (MEM / "01-index.md").write_text(text, encoding="utf-8")
        print(f"已写入 agent-memory/01-index.md ({len(text)} 字, {len(docs)} 文件)")
    else:
        print(text)


# ---------- outline / body ----------

def cmd_outline(a):
    for f in a.files:
        d = load_one(f)
        print(f"## {d.rel}  (共 {len(d.lines)} 行 / {d.chars} 字; Front Matter 占 {d.body_start} 行)")
        if d.fm.get("summary"):
            print(f"summary: {d.fm['summary']}")
        for title, s, e, n in d.sections():
            print(f"  L{s+1}-{e}\t{n:>6}字\t{title}")
        print()


def cmd_body(a):
    d = load_one(a.file)
    if a.lines:
        s, e = a.lines.split(":")
        sys.stdout.write("".join(d.lines[int(s) - 1: int(e)]))
        return
    if a.section:
        for title, s, e, _ in d.sections():
            if a.section in title.strip():
                sys.stdout.write("".join(d.lines[s:e]))
                return
        sys.exit(f"没有匹配的章节: {a.section}; 用 outline 查看可用标题")
    if a.no_fm:
        sys.stdout.write(d.body)
    else:
        sys.stdout.write("".join(d.lines))

# ---------- search ----------

TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-\.]*|[\u4e00-\u9fff]+")
_jieba = None


def _get_jieba():
    global _jieba
    if _jieba is None:
        try:
            import logging, warnings
            warnings.filterwarnings("ignore")
            import jieba  # type: ignore
            jieba.setLogLevel(logging.ERROR)
            _jieba = jieba
        except Exception:
            _jieba = False
    return _jieba


def tokenize(text: str) -> list[str]:
    """英文/数字按词; 中文优先 jieba 搜索模式分词, 未安装时退化为字二元切分(bigram)。"""
    jb = _get_jieba()
    toks = []
    for m in TOKEN_RE.finditer(text):
        t = m.group(0)
        if re.match(r"[\u4e00-\u9fff]", t):
            if jb:
                toks.extend(w for w in jb.lcut_for_search(t) if w.strip())
            elif len(t) == 1:
                toks.append(t)
            else:
                toks.extend(t[i:i + 2] for i in range(len(t) - 1))
        else:
            toks.append(t.lower())
    return toks


# ---------- 语义检索(可选, 依赖 fastembed; 缓存在 scripts/mem/.cache) ----------

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
EMBED_MODEL = "jinaai/jina-embeddings-v2-base-zh"  # 2026-09-12 基准评测: 改写问法 Hit@1 0.59→0.68, 见 scripts/mem/bench
CHUNK_CHARS = 600

# 供 bench/search_bench.py 对比实验用: 非默认 embedding 模型需要自定义注册(fastembed 未内置)。
# 注册函数幂等, 重复调用安全; 只在 bench 脚本里按需调用, 不影响默认路径。
_CUSTOM_MODELS_REGISTERED = False


def register_custom_embed_models():
    global _CUSTOM_MODELS_REGISTERED
    if _CUSTOM_MODELS_REGISTERED:
        return
    _CUSTOM_MODELS_REGISTERED = True
    try:
        from fastembed import TextEmbedding  # type: ignore
        from fastembed.common.model_description import PoolingType, ModelSource  # type: ignore
    except Exception:
        return
    try:
        TextEmbedding.add_custom_model(
            model="BAAI/bge-m3",
            pooling=PoolingType.CLS,
            normalization=True,
            sources=ModelSource(hf="BAAI/bge-m3"),
            dim=1024,
            model_file="onnx/model.onnx",
            additional_files=["onnx/model.onnx_data"],
            size_in_gb=2.27,
        )
    except Exception:
        pass


def _chunks_of(d: Doc, chunk_chars: int = CHUNK_CHARS) -> list[tuple[str, str]]:
    """把文档切成 (章节名, 文本) 块: 头块=标题+summary+关键词, 其余按章节, 过长章节再按 chunk_chars 切。"""
    head = f"{d.fm.get('title', d.path.stem)}\n{d.fm.get('summary', '')}\n{' '.join(_kw(d.fm))}"
    out = [("(摘要)", head)]
    secs = d.sections() or [("(正文)", d.body_start, len(d.lines), 0)]
    for title, s_, e_, _ in secs:
        text = "".join(d.lines[s_:e_]).strip()
        if not text:
            continue
        for i in range(0, len(text), chunk_chars):
            out.append((title.strip(), f"{title.strip()}\n{text[i:i + chunk_chars]}"))
    return out


def _embedder(model_name: str = EMBED_MODEL):
    try:
        import warnings
        warnings.filterwarnings("ignore")
        from fastembed import TextEmbedding  # type: ignore
    except Exception:
        return None
    if model_name != EMBED_MODEL:
        register_custom_embed_models()
    model_dir = Path.home() / ".cache" / "fastembed"
    model_dir.mkdir(parents=True, exist_ok=True)
    return TextEmbedding(model_name, cache_dir=str(model_dir))


def _cache_file_name(model_name: str, chunk_chars: int) -> str:
    """缓存文件名始终带模型名与切块大小: 换模型后向量维度不同, 绝不能混用同一份缓存。"""
    safe = re.sub(r"[^A-Za-z0-9]+", "-", model_name)
    return f"embeddings__{safe}__{chunk_chars}.pkl"


def _load_embed_cache(cache_name: str = "embeddings.pkl"):
    import pickle
    f = CACHE_DIR / cache_name
    if f.exists():
        try:
            return pickle.loads(f.read_bytes())
        except Exception:
            pass
    return {}


def _save_embed_cache(cache, cache_name: str = "embeddings.pkl"):
    import pickle
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / cache_name).write_bytes(pickle.dumps(cache))


def semantic_index(docs: list[Doc], quiet=False, model_name: str = EMBED_MODEL, chunk_chars: int = CHUNK_CHARS):
    """增量刷新 embedding 缓存, 返回 (model, cache); 未安装 fastembed 返回 (None, None)。
    model_name/chunk_chars 非默认值时使用独立缓存文件(见 _cache_file_name), 供 bench 脚本对比不同配置。"""
    import hashlib
    model = _embedder(model_name)
    if model is None:
        return None, None
    cache_name = _cache_file_name(model_name, chunk_chars)
    cache = _load_embed_cache(cache_name)
    todo = []
    for d in docs:
        entry = cache.get(d.mrel)
        h = hashlib.sha1("".join(d.lines).encode()).hexdigest()
        if entry and entry.get("hash") == h:
            continue
        todo.append((d, h))
    if todo:
        import numpy as np
        texts, owners = [], []
        for d, h in todo:
            ch = _chunks_of(d, chunk_chars)
            for title, text in ch:
                texts.append(text); owners.append((d.mrel, title))
        if not quiet:
            print(f"(embedding {len(todo)} 个文件 / {len(texts)} 块…)", file=sys.stderr)
        vecs = np.array(list(model.embed(texts, batch_size=32)), dtype="float32")
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
        for d, h in todo:
            cache[d.mrel] = {"hash": h, "titles": [], "vecs": []}
        for (rel, title), v in zip(owners, vecs):
            cache[rel]["titles"].append(title); cache[rel]["vecs"].append(v)
        for d, h in todo:
            cache[d.mrel]["vecs"] = np.array(cache[d.mrel]["vecs"], dtype="float32")
        # 清理已删除文件
        alive = {d.mrel for d in docs}
        for k in [k for k in cache if k not in alive]:
            del cache[k]
        _save_embed_cache(cache, cache_name)
    return model, cache


def semantic_scores(model, cache, docs: list[Doc], query: str) -> dict[str, tuple[float, str]]:
    """返回 {文件: (最高相似度, 命中章节)}。"""
    import numpy as np
    qv = np.array(list(model.query_embed([query])), dtype="float32")[0]
    qv /= np.linalg.norm(qv) + 1e-9
    out = {}
    for d in docs:
        e = cache.get(d.mrel)
        if not e or len(e["vecs"]) == 0:
            continue
        sims = e["vecs"] @ qv
        i = int(sims.argmax())
        out[d.mrel] = (float(sims[i]), e["titles"][i])
    return out


def cmd_embed(a):
    docs = load_all()
    model, cache = semantic_index(docs)
    if model is None:
        sys.exit("未安装 fastembed: python3 -m pip install -r scripts/mem/requirements.txt")
    n = sum(len(v["vecs"]) for v in cache.values())
    print(f"embedding 缓存就绪: {len(cache)} 文件 / {n} 块 → {CACHE_DIR / 'embeddings.pkl'}")


def lexical_scores(docs: list[Doc], q: list[str]) -> dict[str, tuple[float, float]]:
    """字段加权 BM25 变体, 返回 {文件: (分数, 覆盖率)}。"""
    W = {"title": 6.0, "keywords": 6.0, "summary": 4.0, "headings": 3.0, "body": 1.0}
    fields_of: list[dict[str, Counter]] = []
    for d in docs:
        fields_of.append({
            "title": Counter(tokenize(str(d.fm.get("title", "")) + " " + d.path.stem)),
            "keywords": Counter(tokenize(" ".join(_kw(d.fm)) + " " + " ".join(d.fm.get("questions", []) if isinstance(d.fm.get("questions"), list) else []))),
            "summary": Counter(tokenize(str(d.fm.get("summary", "")))),
            "headings": Counter(tokenize(" ".join(h[2] for h in d.headings()))),
            "body": Counter(tokenize(d.body)),
        })
    N = len(docs)
    df = Counter()
    for f in fields_of:
        seen = set()
        for c in f.values():
            seen |= set(c)
        df.update(seen)
    avg_body = sum(sum(f["body"].values()) for f in fields_of) / max(N, 1)
    out = {}
    for d, f in zip(docs, fields_of):
        score, hit = 0.0, set()
        blen = sum(f["body"].values())
        for t in q:
            idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
            for name, w in W.items():
                tf = f[name][t]
                if not tf:
                    continue
                hit.add(t)
                if name == "body":
                    tf = tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * blen / max(avg_body, 1)))
                else:
                    tf = min(tf, 3)
                score += w * idf * tf
        if hit:
            cover = len(hit) / len(q)
            out[d.mrel] = (score * (0.5 + cover), cover)
    return out


def _doc_boost(d: Doc, enable: bool = True) -> float:
    if not enable:
        return 1.0
    b = {"critical": 1.05, "high": 1.05, "medium": 1.0, "low": 0.9}.get(str(d.fm.get("priority")), 1.0)
    if d.chars > 20000:
        b *= 0.8   # 巨型文件什么都沾边, 压一压, 逼着人去读专门文件
    if d.fm.get("status") in ("archived", "deprecated"):
        b *= 0.5
    if d.mrel.startswith("sessions/"):
        b *= 0.7   # 会话摘要性价比低, 降权
    return b


def fuse_scores(lex: dict, sem: dict, by: dict, mode: str = "hybrid",
                 K: float = 30.0, sem_weight: float = 1.3, min_sim: float = 0.35,
                 boost: bool = True) -> list[tuple[str, float]]:
    """RRF(倒数排名融合): 词法/语义各自按分数排名取倒数名次分, 再乘文档 boost。
    抽成独立函数供 cmd_search 与 bench/search_bench.py 复用, 便于扫参数。"""
    fused: dict[str, float] = defaultdict(float)
    if mode != "semantic":
        for r, (rel, _) in enumerate(sorted(lex.items(), key=lambda x: -x[1][0])):
            fused[rel] += 1.0 / (K + r)
    if mode != "lexical":
        for r, (rel, _) in enumerate(sorted(sem.items(), key=lambda x: -x[1][0])):
            if sem[rel][0] >= min_sim:
                fused[rel] += sem_weight / (K + r)   # 自然语言问句语义更可靠, 默认略高于词法
    for rel in list(fused):
        fused[rel] *= _doc_boost(by[rel], enable=boost)
    return sorted(fused.items(), key=lambda x: -x[1])


def cmd_search(a):
    subdirs = a.dir.split(",") if a.dir else None
    docs = load_all(subdirs)
    if not a.include_always:
        docs = [d for d in docs if d.fm.get("load") != "always"]  # 常驻文件已在上下文里, 不参与检索
    query = " ".join(a.query)
    q = tokenize(query)
    if not q:
        sys.exit("请提供关键词")
    by = {d.mrel: d for d in docs}
    lex = lexical_scores(docs, q)
    sem = {}
    mode = "lexical"
    if a.mode in ("hybrid", "semantic"):
        model, cache = semantic_index(load_all() if subdirs else docs, quiet=a.quiet)
        if model is not None:
            sem = semantic_scores(model, cache, docs, query)
            mode = a.mode
        elif a.mode == "semantic":
            sys.exit("未安装 fastembed, 无法语义检索: python3 -m pip install -r scripts/mem/requirements.txt")
    ranked = fuse_scores(lex, sem, by, mode=mode, min_sim=a.min_sim)
    if not ranked:
        print("无匹配")
        return
    print(f"# search[{mode}]: {query}  (候选 {len(ranked)} / {len(docs)})")
    for rel, _ in ranked[: a.k]:
        d = by[rel]
        cov = f"词{lex[rel][1]:.0%}" if rel in lex else "词-"
        sm = f"语义{sem[rel][0]:.2f}@{sem[rel][1]}" if rel in sem else ""
        print(f"- {rel} | {d.fm.get('priority','?')} | {cov} {sm} | {d.fm.get('summary','')}")
        if a.snippets:
            for l in d.lines[d.body_start:]:
                if set(tokenize(l)) & set(q) and l.strip() and not l.startswith("#"):
                    print(f"    > {l.strip()[:120]}")
                    break


# ---------- lint / stat ----------

MEM_TOPS = ("00-overview", "01-index", "02-user", "03-project", "current/", "decisions/", "knowledge/", "lessons/", "procedures/", "sessions/", "archive/")
REQUIRED = ["title", "type", "status", "created_at", "updated_at", "priority", "keywords", "summary", "load"]
LINK_RE = re.compile(r"`((?:agent-memory/)?(?:[\w\-一-鿿]+/)*[\w\-一-鿿]+\.md)(?:[`#§])")


def git_last_change(rel: str) -> str:
    try:
        out = subprocess.run(["git", "log", "-1", "--diff-filter=M", "--format=%cI", "--", rel], cwd=ROOT,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return out[:10]
    except Exception:
        return ""


def cmd_lint(a):
    docs = load_all()
    known = {d.mrel for d in docs}
    problems = 0
    hints = 0  # 提示不计入问题, 不阻塞任务完成
    now = datetime.now(timezone(timedelta(hours=8)))

    def rep(kind, d, msg):
        nonlocal problems
        problems += 1
        print(f"[{kind}] {d.mrel}: {msg}")

    for d in docs:
        missing = [k for k in REQUIRED if k not in d.fm or d.fm[k] in ("", [])]
        if missing:
            rep("元数据缺失", d, ",".join(missing))
        # 长度采用双阈值: 超过硬上限 max_chars 才算问题, 一旦触发必须一次压到 target_chars 以下(留出 6~8k 的增长空间,
        # 避免"压到 7,9xx → 下次改动又超"的反复 lint); warn_chars~max_chars 之间只提示不计入问题
        exempt = d.fm.get("status") == "archived" or d.mrel.startswith("archive/") or d.mrel == "01-index.md"  # archive/ 永不整读, 豁免
        if not exempt and d.chars > a.max_chars:
            rep("超长", d, f"{d.chars} 字 > {a.max_chars}, 必须压缩/拆分/归档到 < {a.target_chars}")
        elif not exempt and d.chars > a.warn_chars:
            hints += 1
            print(f"[提示] {d.mrel}: {d.chars} 字 > {a.warn_chars}, 临近上限 {a.max_chars}; 下次改动顺手压到 < {a.target_chars}")
        # 常驻文件: 总览等按 always_max 单线; 01-index.md(生成物, 随文件数线性增长)也用双阈值:
        # > index_max 才算问题, > index_warn 只提示(手段: 精简 summary/questions、把低价值文件归档或 deprecated)
        if d.fm.get("load") == "always":
            if d.mrel == "01-index.md":
                if d.chars > a.index_max:
                    rep("常驻超长", d, f"{d.chars} 字 > {a.index_max}, 直接吃启动 token; 精简 summary/questions 或归档低价值文件到 < {a.index_warn}")
                elif d.chars > a.index_warn:
                    hints += 1
                    print(f"[提示] {d.mrel}: {d.chars} 字 > {a.index_warn}, 临近上限 {a.index_max}; 下次整理时精简 summary/questions 或归档")
            elif d.chars > a.always_max:
                rep("常驻超长", d, f"{d.chars} 字 > {a.always_max}, 直接吃启动 token")
        # related 与正文引用的悬空检查
        rels = d.fm.get("related", [])
        refs = set(r.replace("agent-memory/", "") for r in (rels if isinstance(rels, list) else []))
        refs |= {m.group(1).replace("agent-memory/", "") for m in LINK_RE.finditer(d.body)}
        for r in sorted(refs):
            if not r.startswith(MEM_TOPS):
                continue  # 指向其他仓库(site-discovery/、PRD/ 等)的路径不在本工具检查范围
            if r not in known and not (MEM / r).exists():
                rep("悬空引用", d, r)
        # updated_at 与 git 提交日期对比
        if a.git:
            g = git_last_change(d.rel)
            u = _date(d.fm, "updated_at")
            if g and u and g > u:
                rep("updated_at 落后于 git", d, f"fm={u} git={g}")
        # 有保质期的结论
        vu = str(d.fm.get("valid_until", "")).strip()
        if vu:
            try:
                if datetime.fromisoformat(vu[:10]).date() < now.date():
                    rep("已过保质期", d, f"valid_until={vu[:10]}, 需重验或标记 deprecated")
            except Exception:
                rep("valid_until 非日期", d, vu)
        # 长期未更新的 current/ 文件
        try:
            u = datetime.fromisoformat(str(d.fm.get("updated_at")))
            if d.mrel.startswith("current/") and (now - u).days > a.stale_days:
                rep("current 陈旧", d, f"{(now - u).days} 天未更新")
        except Exception:
            rep("updated_at 非 ISO", d, str(d.fm.get("updated_at")))
    # 01-index.md 应是生成物: 比较正文是否与当前 boot 一致
    idx = next((d for d in docs if d.mrel == "01-index.md"), None)
    if idx is not None:
        expect = render_boot([d for d in docs if d.mrel != "01-index.md"], kw=a.index_kw, sessions=False, recent_sessions=3)
        if expect.strip() not in "".join(idx.lines):
            problems += 1
            print("[索引过期] 01-index.md 与当前 Front Matter 不一致, 运行 scripts/mem/mem.py index --write")
    tail = f", 另 {hints} 条提示(不阻塞)" if hints else ""
    print(f"\n共 {problems} 条问题{tail}, {len(docs)} 个文件")


def cmd_stat(a):
    docs = load_all()
    by = defaultdict(lambda: [0, 0])
    always = 0
    for d in docs:
        parts = d.path.relative_to(MEM).parts
        top = parts[0] if len(parts) > 1 else "(根)"
        by[top][0] += 1
        by[top][1] += d.chars
        if d.fm.get("load") == "always":
            always += d.chars
    total = sum(v[1] for v in by.values())
    print("目录\t文件\t字数\t占比")
    for k, (n, c) in sorted(by.items(), key=lambda x: -x[1][1]):
        print(f"{k}\t{n}\t{c}\t{c / total:.0%}")
    print(f"合计\t{len(docs)}\t{total}")
    print(f"load=always 合计 {always} 字 (≈{always // 1.3:.0f} token 量级)")
    print("\n最大的 10 个文件:")
    for d in sorted(docs, key=lambda d: -d.chars)[:10]:
        print(f"  {d.chars:>6}\t{d.mrel}")


def _norm_line(l: str) -> str:
    l = re.sub(r"[\s`*_>#|\-]+", "", l)
    return l


def cmd_dup(a):
    """跨文件重复段落检测: 归一化后 ≥ min_len 字的行, 在多个文件中出现即视为重复。"""
    docs = load_all()
    owner: dict[str, list[str]] = defaultdict(list)
    for d in docs:
        seen = set()
        for l in d.lines[d.body_start:]:
            n = _norm_line(l)
            if len(n) >= a.min_len and n not in seen:
                seen.add(n)
                owner[n].append(d.mrel)
    pair = Counter()
    dup_chars = Counter()
    for n, files in owner.items():
        if len(files) < 2:
            continue
        for f in files:
            dup_chars[f] += len(n)
        fs = sorted(set(files))
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                pair[(fs[i], fs[j])] += len(n)
    print(f"# 重复内容(≥{a.min_len} 字的相同行) 文件 TOP {a.k}: 文件 | 重复字数")
    for f, c in dup_chars.most_common(a.k):
        print(f"- {f} | {c}")
    print(f"\n# 重复最多的文件对 TOP {a.k}:")
    for (x, y), c in pair.most_common(a.k):
        print(f"- {c} 字 | {x} <-> {y}")


def cmd_recent(a):
    """用 git 历史代替手工维护的"最近更新"章节。"""
    try:
        out = subprocess.run(["git", "-c", "core.quotepath=false", "log", f"--since={a.days} days ago", "--format=%h %cd %s", "--date=short", "--name-status", "--", "agent-memory"],
                             cwd=ROOT, capture_output=True, text=True, timeout=15).stdout
    except Exception as e:
        sys.exit(f"git 不可用: {e}")
    print(f"# agent-memory 最近 {a.days} 天变更(git)")
    print(out.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("boot"); p.add_argument("--sessions", action="store_true", help="列出全部 sessions")
    p.add_argument("--recent-sessions", type=int, default=3); p.add_argument("--kw", type=int, default=3, help="每文件最多列几个关键词(评测: 3 比 6 更准)")
    p.add_argument("--no-questions", action="store_true"); p.set_defaults(fn=cmd_boot)
    p = sp.add_parser("index"); p.add_argument("--write", action="store_true", help="写入 agent-memory/01-index.md, 否则打印")
    p.add_argument("--kw", type=int, default=3); p.add_argument("--recent-sessions", type=int, default=3); p.set_defaults(fn=cmd_index)
    p = sp.add_parser("outline"); p.add_argument("files", nargs="+"); p.set_defaults(fn=cmd_outline)
    p = sp.add_parser("body"); p.add_argument("file"); p.add_argument("--section"); p.add_argument("--lines", help="a:b 1-based 闭区间")
    p.add_argument("--no-fm", action="store_true", default=True); p.add_argument("--with-fm", dest="no_fm", action="store_false")
    p.set_defaults(fn=cmd_body)
    p = sp.add_parser("search"); p.add_argument("query", nargs="+"); p.add_argument("-k", type=int, default=8)
    p.add_argument("--dir", help="限定顶层目录, 逗号分隔, 如 lessons,decisions"); p.add_argument("--no-snippets", dest="snippets", action="store_false")
    p.add_argument("--include-always", action="store_true", help="也检索 load=always 的常驻文件")
    p.add_argument("--mode", choices=["hybrid", "lexical", "semantic"], default="hybrid", help="默认 hybrid: 词法+语义融合; 未装 fastembed 自动退化为 lexical")
    p.add_argument("--min-sim", type=float, default=0.35, help="语义相似度阈值, 低于此不计入")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(fn=cmd_search)
    p = sp.add_parser("lint")
    p.add_argument("--max-chars", type=int, default=12000, help="硬上限: 超过即 [超长], 必须压缩/拆分/归档")
    p.add_argument("--target-chars", type=int, default=6000, help="压缩目标: 触发超长后一次压到该值以下, 留足增长空间")
    p.add_argument("--warn-chars", type=int, default=9000, help="提示线: 超过只打 [提示] 不计入问题")
    p.add_argument("--always-max", type=int, default=5500, help="00-overview 等常驻文件的硬上限")
    p.add_argument("--index-max", type=int, default=20000, help="01-index.md(生成物)的硬上限")
    p.add_argument("--index-warn", type=int, default=17000, help="01-index.md 提示线(约 110 文件 × 150 字), 超过只提示")
    p.add_argument("--stale-days", type=int, default=14); p.add_argument("--index-kw", type=int, default=3); p.add_argument("--no-git", dest="git", action="store_false"); p.set_defaults(fn=cmd_lint)
    p = sp.add_parser("stat"); p.set_defaults(fn=cmd_stat)
    p = sp.add_parser("embed"); p.set_defaults(fn=cmd_embed)
    p = sp.add_parser("dup"); p.add_argument("--min-len", type=int, default=30); p.add_argument("-k", type=int, default=15); p.set_defaults(fn=cmd_dup)
    p = sp.add_parser("recent"); p.add_argument("--days", type=int, default=7); p.set_defaults(fn=cmd_recent)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
