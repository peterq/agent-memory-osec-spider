# 任务 50：总览瘦身草案的信息保真评测（先读 00-shared.md）

## 目标
验证「瘦身后的总览 + 按需读一个文件」能否回答原总览能回答的「当前状态类」问题。

## 做法
1. 先**只读原总览** `agent-memory/00-overview.md`，从中出 15 道「一个新会话 Agent 开工前必须知道」的问题（覆盖：当前阻塞、未部署项、上线顺序约束、生产环境硬事实、禁止事项、近期关键决策），把题目和标准答案（引用原总览原句）写到 `SCRATCH/results/overview-qa.md`。
2. 然后模拟只拿到瘦身草案 `SCRATCH/variants/overview-trimmed.md` 的新会话：对每道题，先只凭草案作答；答不出时**最多再打开一个**草案里指向的文件（可用 `mem.py body <file> --section <标题>` 只读一段），记录打开了什么、读了多少字（`wc -m`）。
3. 打分：每题 完整 / 部分 / 失败，以及本题额外读取字数。

SCRATCH = `/tmp/claude-1000/-home-peterq-dev-projects-peterq-agent-memory-osec-spider/edcb70a1-a862-43ac-9227-02c51ee68d85/scratchpad`

## 交付
`results-50.md`：15 题得分表（题目 / 结果 / 额外读取文件与字数）、总额外读取字数 vs 原总览 26.8k 字的对比、哪些信息草案必须补回。
