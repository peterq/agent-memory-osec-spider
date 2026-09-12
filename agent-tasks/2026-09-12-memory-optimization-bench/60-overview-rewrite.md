# 任务 60：正式重写总览 + changelog + 回写总览独有事实（先读 01-shared-execute.md）

## 你能动的文件
`agent-memory/00-overview.md`、新建 `agent-memory/current/changelog.md`、`agent-memory/02-user-preferences.md`、`agent-memory/current/risks.md`、`agent-memory/procedures/workflow-本地构建与验证.md`、`agent-memory/procedures/workflow-子agent任务简报.md`、`agent-memory/procedures/workflow-站点发现.md`、`agent-memory/procedures/workflow-新站点调研.md`、`agent-memory/decisions/decision-2026-09-08-后台登录改为github-oauth.md`。

## 做法
1. 先读 `results-30.md`、`results-50.md`、`SCRATCH/variants/overview-trace.md`。草案 `SCRATCH/variants/overview-trimmed.md` 是起点，`SCRATCH/variants/changelog.md` 是 changelog 起点。
2. **回写 6 条总览独有事实**到正本（results-30「需回写的 6 条」）：Go 目录型 replace 不校验 module 名 与 SPIDER 存量 go vet 告警 → `workflow-本地构建与验证.md`；子 Agent 两种失败模式 → `workflow-子agent任务简报.md`；明文 AK/SK 禁写记忆 → `02-user-preferences.md`「已确认的硬性要求」新增一条 + `current/risks.md`；PanSou/PanHub 渠道 → `workflow-站点发现.md`；论坛站「游客可见率」 → `workflow-新站点调研.md`。已有等价内容的就不重复写。
3. results-50 的三处补回：「先网关后前端」上线顺序 直接写进总览 §2 对应条目，并补进 `decision-2026-09-08-后台登录改为github-oauth.md` 的「影响」节；队列 v2「无回滚路径」→ `current/risks.md`；§2 里的日期通配指针全部改成精确文件名。
4. 以草案为底写正式 `00-overview.md`，**上限 5,500 字符**（`python3 -c "print(len(open(p).read()))"`），§5 决策、§6 经验各放回 ≤ 10 条。§8 改为 ≤ 6 行：`scripts/mem/mem.py boot`（或已由 hook 注入）→ `search` → `outline` → `body --section`，并说明 01-index.md 是脚本生成物。保留 Front Matter 的 created_at，更新 updated_at 与 summary。
5. `current/changelog.md`：以草案 changelog 为底，但**压成「日期 + 一句话 + 指向 session/决策文件」**，不保留原文长段（原文在 sessions 里都有；trace 表里标了）。Front Matter：type knowledge、priority low、load rarely。
6. 原总览 §8 里 8 条指向代码仓库路径的导航项（trace 表有列）：并入对应 knowledge/procedures 文件正文（如果没有的话），文件不在你的可动列表里的就写到 results-60.md 交给主控。

## 交付
results-60.md：最终字数、回写清单（事实 → 文件 → 是否新增或已有）、交给主控的遗留项。
