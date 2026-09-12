# 任务 70：current/tasks.md 瘦身归档（先读 01-shared-execute.md）

## 你能动的文件
`agent-memory/current/tasks.md`、新建 `agent-memory/archive/2026/tasks-2026-09-已完成.md`（目录 archive/2026/ 需要创建）。

## 做法
1. `mem.py outline agent-memory/current/tasks.md` 看结构（58k 字、15 个二级节）。
2. 判据：任务块「已完成且已部署/已上线」或「已完成且明确不再跟进」→ 整块原文移入归档文件（保留原标题、日期与全部内容，按原顺序），归档文件 Front Matter：type archive、status archived、priority low、load rarely、summary 写明覆盖哪些任务与日期范围。
3. 「已完成但未部署」「进行中」「阻塞」「待办」保留在 tasks.md，但每块要压缩：保留 当前状态 / 未完成的待办 / 需人工决策 / 阻塞原因 / 指向 session 或决策文件的路径；把过程叙述（几点几分做了什么、第几轮、容器 id、md5 这类）删掉——**删之前确认对应 session 文件里已有**，没有的话把那段追加到对应 `sessions/2026/` 文件末尾一个「补录自 tasks.md」小节（这是唯一允许动 sessions 的情况，写 results 时列出）。
4. 目标：tasks.md ≤ 8,000 字符；顶部加一个「一眼总表」：任务 | 状态 | 阻塞/下一步 | 详情文件，≤ 10 行。
5. tasks.md Front Matter：summary 改成能反映当前真正在做/阻塞的事；updated_at 更新。

## 交付
results-70.md：前后字数、归档了哪些块、保留了哪些块、补录到 sessions 的段落清单。
