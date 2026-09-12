# 第二轮共享上下文：正式执行记忆瘦身（用户 2026-09-12 已拍板）

先读 00-shared.md 了解背景与工具。本轮**允许修改 agent-memory/ 下的文件**，但每个任务只能动自己任务单里列出的文件，其他文件一律不碰（其他 Agent 在并行改）。
仍然禁止：改 AGENTS.md、git commit、删除任何内容（只能移动/归档）。

通用规则（来自 AGENTS.md）：
- 每个 .md 必须有完整 Front Matter；改动文件必须更新 updated_at（ISO 8601 +08:00，用当前时间），created_at 不得改；新文件 created_at=updated_at=现在。
- 新文件的 summary 要一句话说清「不读正文也能判断是否要加载」，keywords 写检索会用到的词（含英文标识符）。
- 中文；不写敏感信息（AK/SK/口令）。
- 完成后跑 `scripts/mem/mem.py lint` 看自己改的文件没有新报错（"updated_at 落后于 git"这一类忽略）。
- 实验产物目录 SCRATCH = /tmp/claude-1000/-home-peterq-dev-projects-peterq-agent-memory-osec-spider/edcb70a1-a862-43ac-9227-02c51ee68d85/scratchpad

结果写 results-<编号>.md（简短：做了什么、动了哪些文件、有疑问的取舍）。
