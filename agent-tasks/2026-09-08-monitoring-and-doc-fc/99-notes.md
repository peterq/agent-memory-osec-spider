# 99-notes —— 主控追加的裁定与环境约定（所有角色必读）

## 1. 工作目录分配（**非常重要**）

SPIDER 仓库用 git worktree 隔离，每个角色只在自己的目录里干活：

| 角色 | SPIDER 工作目录 | 分支 |
|---|---|---|
| 10-alert | `/home/peterq/dev/projects/1s/spider-wt-alert-admin` | `feat/alert-admin` |
| 20-proxy | `/home/peterq/dev/projects/1s/spider-wt-proxy-monitor` | `feat/proxy-monitor` |
| 30-trace | `/home/peterq/dev/projects/1s/spider-wt-link-trace` | `feat/link-trace` |
| 41-doccrawler | `/home/peterq/dev/projects/1s/spider-wt-doc-crawler` | `feat/doc-crawler` |

⚠️ **主检出 `/home/peterq/dev/projects/1s/osec-spider-go` 严禁改动、严禁切分支。**
上面正跑着生产用的动态 rps 守护脚本（`scripts/lc_adaptive_rps.sh`，PID 1664230，
守护 P4 全量 bootstrap 作业 id=8）。bash 会在运行中重新读取脚本文件，改动那个目录
可能直接搞坏正在跑的生产守护。只读地看代码没问题，**任何写操作都必须在自己的 worktree 里**。

worktree 已由主控用 `scripts/new_worktree.sh` 建好（含 gitignore 掉的
`services/proxy-provider/change_proxy_config.go` 凭据文件），分支从 `master` 拉出，
直接 `cd` 进去就能 `go build ./...`。

其它仓库（各自只有一个角色会动，直接在主检出上开分支即可）：

| 仓库 | 谁在动 | 分支 |
|---|---|---|
| COMMON `/home/peterq/dev/projects/1s/enfi-resource-common` | 40-fcchrome（新增 `fc-chrome/`） | `feat/fc-chrome` |
| API `/home/peterq/dev/projects/1s/osec-resource-api` | 20-proxy | `feat/proxy-monitor` |
| userscripts `/home/peterq/dev/projects/peterq/userscripts` | 40-fcchrome | `feat/kdoc-cloud` |
| NC-JS `/home/peterq/dev/projects/1s/nc-js` | 10 / 20 / 30 / 40 **四个角色共用主检出** | 见下 |

## 2. NC-JS 的特殊规则：**不要 git commit，也不要开分支**

四个角色同时在 NC-JS 主检出（分支 `main`）上改**互不相同的文件**，所以直接改就行，但：

- **禁止在 NC-JS 里执行任何 `git commit` / `git checkout` / `git stash` / `git add -A`**，
  否则会把别人正在写的半成品一起提交或冲掉。
- 改完把**你改动的 NC-JS 文件清单**写进汇报，主控会按角色分别提交。
- 各角色的 NC-JS 文件边界：
  - 10-alert：`admin/spiderAdmin/src/pages/queue/{AlertHistoryPage,AlertRulesPage,OverviewPage,QueueCtxProvider}.tsx`
  - 20-proxy：`admin/spiderAdmin/src/pages/proxy/*`
  - 30-trace：`admin/spiderAdmin/src/pages/queue/TracePage.tsx`
  - 40-fcchrome：`apps/cdp-driver/*`、`admin/login3rd/src/task/task.ts`
- 越界要动别人的文件（或 `navState.ts` / `AppLayout.tsx` / `spidergw.ts` 这类共享文件）之前，
  **先在汇报里说明**，尽量不要动。
- 类型检查：`cd /home/peterq/dev/projects/1s/nc-js && pnpm -F @nc/spider-admin type-check`
  （Phase 0 之后是通过的）。**注意别人可能同时在改，出现的报错如果指向不属于你的文件，
  说明是并发状态，不是你的问题——在汇报里记一笔即可，不要去替别人修。**

## 3. 20-proxy 专属：怎么验证 API 仓库能编译

API 的 `go.mod` 里 `replace github.com/1s/enfi-spider-go => ../osec-spider-go`（**主检出**），
看不到你 worktree 里的改动。临时改 replace 验证，验证完必须还原：

```bash
cd /home/peterq/dev/projects/1s/osec-resource-api
go mod edit -replace github.com/1s/enfi-spider-go=/home/peterq/dev/projects/1s/spider-wt-proxy-monitor
go build ./...            # 这才是真实验证
go mod edit -replace github.com/1s/enfi-spider-go=../osec-spider-go
git diff --stat go.mod    # 必须为空, 确认已还原
```

`go.sum` 若被改动也要 `git checkout -- go.sum` 还原。**提交里不得包含 go.mod/go.sum 的 replace 变更。**

## 4. 通用

- 生产 P4 bootstrap 在跑，**网关禁止重启，本轮不部署任何东西**。
- 不要 ssh 生产、不要跑 `deploy.sh`、不要碰 `_note/config/*.yaml`。
- 遇到需要人工提供的信息（凭据、域名、Aliyun 账号、生产验证），**记进汇报的"需要人工"清单，
  然后按最合理的缺省值把功能做完整、能编译、能单测**，不要停下来等。
- 不要转派子 Agent 然后停在"等待回报"上；自己做完。
- 汇报要基于**实际执行过的命令输出**，不要写"应该没问题"。
