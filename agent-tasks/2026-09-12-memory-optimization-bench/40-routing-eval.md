# 任务 40：启动上下文变体的「找文件准确率」评测（先读 00-shared.md）

你是被评测的对象：模拟一个刚启动的新会话 Agent，**只能看到一份启动上下文**，要为每个问题判断该去读哪些记忆文件。

## 做法
1. 只读你被分配的那一份变体文件（路径在派发 prompt 里给出）。**禁止**读 `agent-memory/` 下任何文件、禁止运行 `mem.py search`（那是另一条路线，不在本实验里）。
2. 读 `ROOT/scripts/mem/bench/gold_paraphrased_questions.jsonl`（只含 topic 与 queries，没有答案）。**禁止**读同目录的 gold.jsonl / gold_paraphrased.jsonl。
3. 对每个主题的每条改写问法，凭变体文件给出你会去读的文件路径 Top3（相对 agent-memory/，按把握排序）。
4. 输出 `SCRATCH/results/routing-<变体名>.jsonl`，每行 `{"topic":..., "query":..., "picks":[...]}`，共 123 行。

SCRATCH = `/tmp/claude-1000/-home-peterq-dev-projects-peterq-agent-memory-osec-spider/edcb70a1-a862-43ac-9227-02c51ee68d85/scratchpad`

## 交付
只交 jsonl；不要写分析（主控统一打分）。最后用一行说明你读了哪个变体、字数多少。
