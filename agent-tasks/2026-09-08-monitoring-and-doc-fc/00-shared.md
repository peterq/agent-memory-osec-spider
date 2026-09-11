# 00-shared —— 2026-09-08 并行四任务（监控增强 + 文档爬虫上云）

所有角色都要读本文件。你自己的角色文件里才有落点与验收细节。

## 1. 本轮四个任务（互相独立，并行开发）

| 角色文件 | 任务 | 主要仓库 |
|---|---|---|
| `10-alert.md` | 告警加入后台（含现场日志）+ 队列失败率告警按队列可配、默认 10min/50% → 1h/60% | COMMON / SPIDER / NC-JS |
| `20-proxy.md` | 代理池监控纳入 admin 后台（供给量 + 按场景成功率/失败分类/延迟分位） | SPIDER / NC-JS |
| `30-trace.md` | 资源链接爬取路径追踪（SLS 日志拼时间线） | COMMON / SPIDER / NC-JS |
| `40-docfc.md` | 文档爬虫 FC 自动化（新 Chrome FC 实例 + doc-crawler 服务端进程 + 移植金山文档油猴脚本） | COMMON / SPIDER / userscripts |

## 2. 仓库速查（磁盘目录名 ≠ Go module 名）

| 角色 | 磁盘路径 | module / 技术栈 |
|---|---|---|
| COMMON | `/home/peterq/dev/projects/1s/enfi-resource-common` | `github.com/1s/enfi-resource-common`，**唯一契约中心**，所有 `.proto` 在 `rpc/` 下 |
| SPIDER | `/home/peterq/dev/projects/1s/osec-spider-go` | `github.com/1s/enfi-spider-go`，爬虫 + 网关 |
| STORAGE | `/home/peterq/dev/projects/1s/enfi-resource-storage` | `enfi-resource-storage` |
| API | `/home/peterq/dev/projects/1s/osec-resource-api` | `github.com/1s/enfi-resource-api` |
| NC-JS | `/home/peterq/dev/projects/1s/nc-js` | 前端 mono repo（pnpm + Vite6 + Vue3 TSX + ant-design-vue 4） |
| userscripts | `/home/peterq/dev/projects/peterq/userscripts` | 油猴脚本仓库（**已有未提交改动，不要 `git checkout`/`stash` 别人的东西**） |
| nerve-center | `/home/peterq/dev/projects/1s/nerve-center` | 存量 FC Chrome 环境 `fc-entry/`（**只读参考，有未提交改动，禁止修改**） |

## 3. 主控已完成的 Phase 0（契约先行，不要重复做）

主控已经在 COMMON 里写好并生成了本轮需要的 proto，**你直接用，不要改已有字段编号**；
确实需要加字段就加在末尾并在角色文件的交付里说明。

- `rpc/spider/queue_admin_rpc/queue_admin.proto`：追加了 4 个告警方法与 `AlertRecord` /
  `AlertRuleConfig` 等消息（任务 10）。
- `rpc/spider/proxy_admin_rpc/proxy_admin.proto`：新建 `ProxyAdminRpc`（任务 20）。
- 任务 30 的契约见 `30-trace.md`。

**前端 Phase 0 也已完成（NC-JS `main` 分支提交 `627e47b`），你不要重做**：

- `packages/catalyst/scripts/devops/protc_gen.sh` 已加入 `proxy_admin_rpc`，TS 契约已生成
  （`contract/rpc/scheduler/proto/{queue_admin_rpc,proxy_admin_rpc}/`）。**只有你改了 proto 才需要重新生成。**
- `useGwClient()` 已多返回一个 `proxyAdminRpc`。
- `admin/spiderAdmin/src/layout/navState.ts` 已加好 5 个 `MenuKeys`：
  `QueueAlerts` / `QueueAlertRules` / `QueueTrace` / `ProxyOverview` / `ProxyScenes`。
- `admin/spiderAdmin/src/layout/AppLayout.tsx` 已加好菜单项、`LazyKeepAlive` 插槽与 props 传递。
- 5 个页面文件已作为**占位组件**存在，你要做的是**替换文件内容**，不是新建：
  `src/pages/queue/{AlertHistoryPage,AlertRulesPage,TracePage}.tsx`、
  `src/pages/proxy/{ProxyOverviewPage,ProxySceneDetailPage}.tsx`
- `packages/catalyst/contract/rpc/spiderGw/queueAdminMock.ts` 已补齐 5 个新方法的 mock，
  mock 数据刻意覆盖了易漏测分支（抓日志失败 / 通知失败 / 只覆盖部分字段的告警配置 / 未埋点阶段）。
  **改页面时请用 mock 开关实际跑一遍这些分支。**

⇒ 因此：**尽量不要再改 `navState.ts` / `AppLayout.tsx` / `spidergw.ts`**。确需改（比如你的页面
需要额外 props），改动要最小化并在汇报里点名，主控合并时会重点看这几个文件。
`vue-tsc --build` 在 Phase 0 后是通过的，你提交前必须让它仍然通过。

Go 侧生成命令（在 COMMON 里跑）：

```bash
cd /home/peterq/dev/projects/1s/enfi-resource-common/rpc/spider && bash gen.sh
```

前端 TS 契约生成（在 NC-JS 里跑）：

```bash
cd /home/peterq/dev/projects/1s/nc-js && pnpm -F @nc/catalyst gen:proto
```

（脚本 `packages/catalyst/scripts/devops/protc_gen.sh`，已修好路径；新增 proto 要把文件名加进该脚本的生成列表。）

## 4. 硬性约束 / 环境禁忌（违反会导致返工或生产事故）

1. **绝对不要在 NC-JS 的 `admin/*` 子应用里跑 `pnpm build`**：`@nc/build` 的 `mfe()` 插件默认
   `deploy:true`，挂在不看 mode 的 `closeBundle` 上，**会把产物真实上传到生产 OSS**，且构建报错
   不代表没上传。要验证构建，先临时给 `vite.config.ts` 的 `mfe()` 传 `{ deploy: false }`，
   验证完 `git checkout -- vite.config.ts` 还原。类型检查用 `pnpm -F <包名> type-check`（不部署）。
2. **不要部署任何东西**：生产 P4 全量 bootstrap 作业 id=8 正在跑，**网关禁止重启**。
   本轮只做到"代码完成 + 本地构建/测试通过 + 提交"。不要执行 `deploy.sh`、不要 ssh 生产改东西。
3. **不要碰 `_note/config/*.yaml`**（含明文密钥，Agent 无权限）。也不要把任何 AK/SK、口令、token
   写进代码、注释、文档或提交信息。
4. 线上非 gateway 服务的 `config.yaml` 不由 `deploy.sh` 分发：**新增配置节必须有完整内置缺省值**，
   开关字段用 `*bool`（nil 视为开启），否则线上会静默空跑。
5. **不要顺手修存量问题**：SPIDER 仓库有大量存量 `go vet` 告警与测试失败
   （`services/alipan`、`services/quark`、`services/gateway/*`、`services/devops/*` 等）。
   只保证你新增/修改的包干净，存量问题如实报告但不要改。
6. **proto3 不要用 `-1`/`0` 当"未设置"哨兵**（0 常是合法业务值）。需要"是否设置"语义就用
   proto3 `optional`（protoc 3.21 + protobuf-ts 2.9.4 都支持）。
   见 `agent-memory/lessons/failure-proto3零值与负一哨兵冲突.md`。
   例外：**返回值**里用 `-1` 表示"无数据/不适用"是本项目既有约定（如 `oldestWaitingAgeSec`），
   proto 注释里已写明的照做。
7. **管理类功能一律放 `services/gateway/` 之下，不新增进程**（决策 2026-09-04）。
   唯一例外是任务 40 的 `doc-crawler`（用户明确要求独立进程）。
8. **后台前端一律加到 `admin/spiderAdmin` 的左侧菜单**，不要新建 qiankun 子应用。
9. `ant-design-vue` 组件的 `style` **一律传对象，不要传字符串**（`Row`/`Menu.Item` 会用
   `Object.assign` 合并，传字符串会运行时抛 `CSSStyleDeclaration` 索引属性错）。
10. 不要动别人的工作区：只提交你自己改的文件，`git add` 用明确路径，不要 `git add -A`。

## 5. 关键架构事实（省得你重新调研）

- **前端只连 SPIDER 网关**，走 WebRTC DataChannel 上自实现的 gRPC，不调任何 HTTP/REST。
  入口 hook：`packages/catalyst/contract/rpc/spiderGw/spidergw.ts` 的 `useGwClient()`，
  一次返回 `resSchedulerRpc / spiderRpc / docRpc / downloadRpc / queueAdminRpc`。
  **新增一个 service 就在这里多返回一个 client**，并在 `admin/spiderAdmin` 的
  `layout/AppLayout.tsx` 往下传。
- 网关鉴权已改 GitHub OAuth（代码已合并未部署），对本轮开发无影响，照抄现有注册方式即可。
- `services/gateway/queue_admin/` 是本轮"后台功能"的最佳范式：`register.go`(注册到 RTC + 原生 gRPC)、
  `service.go`、`worker_leader.go`(双实例抢主锁 `IsLeader()`)、`sls.go`(SLS 薄封装)、
  `metrics.go`(prom 推送)、`audit.go`(写操作审计)、`errors.go`(错误码)。
- **网关跑两台机（osec-res1 / osec-res2）**：任何"定时轮询/采集/告警"逻辑必须先判
  `leader.IsLeader()`，否则会双份执行。
- 前端页面写法范式：
  - 页面外壳与菜单：`admin/spiderAdmin/src/layout/{navState.ts, AppLayout.tsx, LazyKeepAlive.tsx, Page.tsx}`
  - 分页表格 + 自动刷新：`src/pages/queue/QueueDetailPage.tsx`、`src/pages/doc/comps/queuedTasks.vue`
  - 配置编辑页：`src/pages/lifecycle/ParamsPage.tsx`
  - 曲线：`src/pages/queue/MiniLineChart.tsx`；JSON 兜底：`src/pages/queue/JsonTree.tsx`
  - 时间/数字格式化：`src/pages/queue/format.ts`
  - **int64 在 TS 侧是 BigInt**：传参 `BigInt(x)`，展示 `Number(x)`。
- SLS（阿里云日志）薄封装在 `services/gateway/queue_admin/sls.go`：
  - `search(query, fromMs, toMs, limit)`，**limit 被硬夹到 ≤200**
  - `buildStageQuery(service, loggerType, stage, extra)` 拼 `service:X and type:Y and stage:Z`
  - 日志字段是扁平的 `level/service/stage/host/content/data`，`data` 是结构化 JSON 字符串
  - 本进程日志的 `service` 值 = `"spider-" + os.Args[1]`（如 `spider-gateway`）
  - SLS 未配置时 `enabled=false`，所有方法优雅降级返回 `errSlsNotConfigured`，**不许 panic**

## 6. 验证命令（提交前必须全过）

```bash
# COMMON
go build ./... && go vet ./rpc/...

# SPIDER（全仓 build 必须过；vet/test 只看你新增的包）
cd /home/peterq/dev/projects/1s/osec-spider-go && go build ./... && go vet ./<你的新包>/... && go test ./<你的新包>/...

# NC-JS 类型检查（不会部署）
cd /home/peterq/dev/projects/1s/nc-js && pnpm -F @nc/catalyst type-check && pnpm -F @nc/spider-admin type-check
```

## 7. 交付要求

- 代码写完 → 跑通上面的验证命令 → **在各自仓库分支上提交**（见角色文件指定的分支名），
  提交信息用中文，遵循 `feat(...)/fix(...)` 前缀，末尾加：
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
- **不要 push，不要合并到 master/main**，由主控统一合并。
- 汇报里必须包含：改了哪些文件、每条验证命令的真实输出结论、**没做完的部分和原因**、
  以及"需要人工提供的信息"清单（现在无人值守，缺信息就先留 TODO 把功能做完整可编译，
  不要卡住等待）。
- 不要采信"应该没问题"，每条结论都要有实际执行过的命令支撑。
