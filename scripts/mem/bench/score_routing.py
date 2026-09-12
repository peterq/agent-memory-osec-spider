#!/usr/bin/env python3
"""给「启动上下文变体 → 找文件」实验打分。

用法: score_routing.py <gold_paraphrased.jsonl> <routing-*.jsonl>...
每个 routing 文件一行 {"topic","query","picks":[...]}；按 topic+query 对上 gold 的 expected，
命中 = picks 里任一文件在 expected 中。输出 Hit@1 / Hit@3 / 未作答数，以及每个变体错得最多的 topic。
"""
import json, sys
from collections import Counter, defaultdict


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def norm(f):
    return f.strip().strip("`").replace("agent-memory/", "")


def main():
    gold_path, *runs = sys.argv[1:]
    gold = {}
    for g in load(gold_path):
        for q in g["queries"]:
            gold[(g["topic"], q)] = set(g["expected"])
    print(f"gold: {len(gold)} 题\n")
    print("| 变体 | 作答 | Hit@1 | Hit@3 |")
    print("|---|---|---|---|")
    per_topic = {}
    for r in runs:
        rows = load(r)
        h1 = h3 = n = 0
        miss = Counter()
        for row in rows:
            key = (row["topic"], row["query"])
            exp = gold.get(key)
            if exp is None:
                # 容错: 只按 query 匹配
                cand = [v for (t, q), v in gold.items() if q == row["query"]]
                exp = cand[0] if cand else None
            if exp is None:
                continue
            n += 1
            picks = [norm(x) for x in row.get("picks", [])]
            if picks[:1] and picks[0] in exp:
                h1 += 1
            if any(p in exp for p in picks[:3]):
                h3 += 1
            else:
                miss[row["topic"][:30]] += 1
        name = r.split("/")[-1].replace("routing-", "").replace(".jsonl", "")
        print(f"| {name} | {n}/{len(gold)} | {h1/max(n,1):.0%} | {h3/max(n,1):.0%} |")
        per_topic[name] = miss
    print()
    for name, miss in per_topic.items():
        print(f"{name} 错最多: " + "; ".join(f"{t}({c})" for t, c in miss.most_common(4)))


if __name__ == "__main__":
    main()
