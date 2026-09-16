# scripts/dev —— 多仓库并行开发辅助脚本

| 脚本 | 用途 |
|---|---|
| `new_worktree_all.sh <分支> <短名> <repo>...` | 一次为 common/spider/api/storage/ncjs 建同级 worktree（目录 `<repo>-wt-<短名>`），基线 master（nc-js 为 main）；SPIDER 复用其自带 `scripts/new_worktree.sh` 补齐 gitignore 源码 |
| `integration_check.sh <repo> <集成名> <分支>...` | 合并预演：建 `integration/<集成名>` 集成 worktree，按顺序 `merge --no-ff`，冲突则记录并 abort 继续，最后 `go build ./...`；下游仓库 go.mod 的 replace 以 `temp(integration)` 提交临时指向 `../common-wt-<集成名>`（合并 master 前必须撤销） |

流程正本：`agent-memory/procedures/workflow-并行多任务开发与合并预演.md`。
