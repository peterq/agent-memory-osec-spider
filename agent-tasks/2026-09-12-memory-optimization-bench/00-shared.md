# 共享上下文：记忆系统优化方案对比实验

## 背景
仓库 `/home/peterq/dev/projects/peterq/agent-memory-osec-spider`（下称 ROOT）用 `agent-memory/` 目录做 Agent 跨会话记忆，100 个 Markdown 文件、42 万字。
问题：启动常驻文件（`00-overview.md` 26.8k 字 + `01-index.md` 24.3k 字）过大，新会话找文件找不准。
已有工具 `ROOT/scripts/mem/mem.py`（`--help` 看子命令；文档 `ROOT/scripts/mem/README.md`），
方案文件 `ROOT/agent-memory/decisions/decision-2026-09-12-记忆系统瘦身与脚本化加载.md`。
本轮目标：**用数据对比不同方案的效果**，为拍板提供依据，不是直接改造记忆内容。

## 评测基准
`ROOT/scripts/mem/bench/gold.jsonl`：41 个主题，每行 `{"topic", "queries":[原始问法...], "expected":[期望文件(相对 agent-memory/)...]}`。
来源是 `01-index.md` 的「关键词索引」，所以 **原始问法对 01-index.md 是泄露的**，跨方案比较时要用改写问法 `gold_paraphrased.jsonl`（由 20-paraphrase 任务产出，同目录）。

## 硬性约束
- 全程只读 `agent-memory/`，**禁止修改任何记忆文件**、禁止改 `AGENTS.md`。
- 可以改 `scripts/mem/mem.py`，但必须保持现有子命令默认行为不变（只能加参数/加子命令）；新脚本放 `ROOT/scripts/mem/bench/`。
- 可以 `python3 -m pip install` 依赖（注意：`pip` 命令本身坏了，用 `python3 -m pip`）。fastembed 模型缓存目录 `~/.cache/fastembed`。
- 中文输出、中文注释。脚本要能被复用，写清用法。
- 产出统一写到本目录 `results-<任务编号>.md`（简洁：表格 + 结论 + 建议），中间产物放各自任务说明里指定的位置。
- 不要 git commit；主控统一提交。
