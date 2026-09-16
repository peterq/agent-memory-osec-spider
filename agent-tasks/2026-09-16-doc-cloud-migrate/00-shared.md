# 云端文档脚本迁入 NC-JS —— 合并清单（2026-09-16）

背景与决策：`agent-memory/decisions/decision-2026-09-16-云端文档脚本迁入NC-JS.md`。

| 仓库 | worktree | 分支 | commit | 内容 |
|---|---|---|---|---|
| NC-JS | `/home/peterq/dev/projects/1s/ncjs-wt-doc-cloud` | `feat/doc-cloud-spider` | `4d921bf` | 新包 `apps/doc-cloud-spider`（源码/单测/夹具/验证脚本/README）、根 README、`vitest.workspace.ts`、`pnpm-lock.yaml`、spiderAdmin 一行注释 |
| SPIDER | `/home/peterq/dev/projects/1s/spider-wt-doc-cloud` | `feat/doc-cloud-spider` | `8c9b1c0` | `config/config.go`、`services/doc_crawler/doc_crawler.go` 各两行注释 |

## 合并步骤（用户确认后执行）
```bash
cd /home/peterq/dev/projects/1s/nc-js && git merge --ff-only feat/doc-cloud-spider && git worktree remove ../ncjs-wt-doc-cloud && git branch -d feat/doc-cloud-spider
cd /home/peterq/dev/projects/1s/osec-spider-go && git merge --ff-only feat/doc-cloud-spider && git worktree remove ../spider-wt-doc-cloud && git branch -d feat/doc-cloud-spider
# 人工: cd nc-js && pnpm install --filter @nc/doc-cloud-spider... && cd apps/doc-cloud-spider && pnpm build && pnpm upload
```
主工作树若已有其他分支先合入 main/master，ff 失败就改 `git merge`（新包目录独立，预期无冲突；`pnpm-lock.yaml` 可能需要重新 `pnpm install`）。

## 未纳入
- 个人仓库 `userscripts` 的 `src/cloud/` 等过时副本未删（用户自行决定）。
- PC 端油猴调度器插件未迁（见决策「影响」）。
