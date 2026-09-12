# 任务 20：生成改写问法（先读 00-shared.md）

## 目标
为 gold.jsonl 的 41 个主题各写 3 条**自然语言改写问法**，模拟真实用户/Agent 在新会话里的提问，用于无泄露评测。

## 要求
- 输出 `ROOT/scripts/mem/bench/gold_paraphrased.jsonl`，每行结构与 gold.jsonl 相同（`topic` 原样保留，`expected` 原样保留，`queries` 换成 3 条改写）。
- 改写规则：尽量不复用原问法里的中文实词（专有名词如 haisou、qiankun、bootstrap、res_lc 可以保留，因为真实提问也会带）；一条口语化、一条描述现象/报错、一条带任务意图（"我要…/怎么…"）。
- 写之前用 `mem.py body <expected 文件> | head -40` 看一眼目标文件，确保改写问法是该文件真正能回答的问题，不要凭 topic 字面瞎编。
- 不做检索评测，只产出文件；最后自检 JSON 每行可解析、41 行。

## 交付
`gold_paraphrased.jsonl` + `results-20.md`（一段话说明规则与抽样 5 条示例）。
