# 任务 90：把旧索引的「问题 → 文件」路由迁成各文件的 `questions:` 字段（先读 01-shared-execute.md）

## 背景
`01-index.md` 即将改为脚本生成物（`scripts/mem/mem.py index --write`），它原有的「关键词索引」一节（约 45 个 `### 问法1 / 问法2 …` 小节，每节下面 `→ 文件; 代码路径…`）是人工维护的高质量路由，不能丢。旧内容已快照到 `SCRATCH/variants/index-current.md`（**以它为准，不要读 agent-memory/01-index.md，它可能已被重生成**）。

## 你能动的文件
`agent-memory/` 下除 `00-overview.md`、`01-index.md` 之外所有文件的 **Front Matter**（`questions:`、`keywords:`、`updated_at`），以及在目标文件正文**追加**一小节「代码位置」（仅当旧路由里有代码路径且正文没有时）。不要改正文其他内容。

## 做法
1. 逐个小节处理：小节标题按 ` / ` 拆成问法；`→` 后列出的 `.md` 是目标文件（可能已被拆分或改名：用 `mem.py search <问法>` 或 `ls` 确认现在的落点；找不到的记到 results）。
2. 给每个目标文件 Front Matter 加 `questions:`（YAML 块列表，每条一个问句，3~6 条，同一文件被多个小节指向时合并去重，超过 6 条挑最有区分度的）；问法里有专有名词/标识符（`config.Config`、`13001`、`X-HS-Client-Context`）而 `keywords` 没有的，补进 `keywords`。
3. 旧路由里的代码路径（如 `services/gateway/queue_admin/alert.go`(引擎与 6 条规则)…）：检查目标文件正文是否已有；没有则在文件末尾追加 `## 代码位置` 小节（一行一条，原样搬过去）。
4. 小节指向 `sessions/` 的：把 questions 写到该 session 提炼后的 knowledge/procedures 文件上（任务 80 已把 res_lc 会话提炼进 `knowledge/architecture-api.md` 与 nc-js 拆分文件；其他情况用 search 找提炼文件，确实没有的才写到 session 文件上并在 results 里列出「待提炼」）。
5. 「当前该做什么」「密钥、安全」这类指向 `current/tasks.md`、`02-user-preferences.md` 的照常处理。
6. 每改一个文件更新 `updated_at`。结束后运行 `scripts/mem/mem.py index --write`，再 `scripts/mem/mem.py lint`，确保没有「元数据缺失」「悬空引用」新增。

## 交付
results-90.md：处理了多少小节 / 改了多少文件 / 追加了几处「代码位置」/ 找不到落点或待提炼的清单。
