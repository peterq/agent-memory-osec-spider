# 共享上下文：分享链接总览 + 搜索总览纳入管理后台

> 所有参与本任务的子 Agent 都必须先读完本文件，再读自己那份角色简报。

## 1. 任务目标（用户原话）

1. 将**分享链接总览**（按时间段、类型）纳入管理后台，包括新增数（按来源分）、检测数、检测有无更新数、失效数，以及其他可能需要或有用的指标。
2. 主要通过 **SLS 日志**实现：将**搜索情况总览**纳入管理后台，包括搜索量、延迟、客户端 IP 数、用户数，搜索量 top10 的 IP 和 uid，top1000 搜索词，以及其他可能需要的指标。对 **p90 指标监控进行报警，并关闭匿名搜索 30 分钟**。

## 2. 仓库、分支与工作树

| 角色 | 路径 | 分支 | 说明 |
|---|---|---|---|
| COMMON（契约中心） | `/home/peterq/dev/projects/1s/enfi-resource-common` | master，契约已提交 `f2f0881` 并 push | **不要改契约**，有问题告诉主控 |
| SPIDER 主工作树（lifecycle 角色用） | `/home/peterq/dev/projects/1s/osec-spider-go` | `feat/share-search-overview`（已建好） | 网关模块在 `services/gateway/` |
| SPIDER 第二工作树（search_admin 角色用） | `/home/peterq/dev/projects/1s/osec-spider-go-wt-search` | `feat/search-admin`（git worktree，已建好） | 同一仓库的另一份检出，避免两个角色互相踩文件；`go.mod` 的 `replace ../enfi-resource-common` 在这里同样成立 |
| API | `/home/peterq/dev/projects/1s/osec-resource-api` | `feat/search-guard`（已建好） | module `github.com/1s/enfi-resource-api` |
| NC-JS（后台前端） | `/home/peterq/dev/projects/1s/nc-js` | `feat/share-search-overview`（已建好） | 只改 `admin/spiderAdmin` 与 `packages/catalyst/contract/rpc/spiderGw` |

代码注释、界面文案、提交信息一律**中文**。每个角色只在自己的分支/工作树里提交，**不要 push**，不要 checkout 别的分支；主控负责合并与上线。
提交信息**禁止**出现 `Co-Authored-By` 或任何邮箱（仓库 commit-msg 钩子会拒绝）。

## 3. 契约（已定稿，任何人不得修改）

- `enfi-resource-common/rpc/spider/lifecycle_rpc/lifecycle.proto` 末尾「分享链接总览」一节：`LifecycleRpc.ShareOverview`。
- `enfi-resource-common/rpc/spider/search_admin_rpc/search_admin.proto`（全新）：`SearchAdminRpc`（Overview / Top / GuardStatus / SetAnonymous / UpdateGuardParams）。

**必须完整读一遍对应 proto 里的注释**：数据来源口径、字段语义、缺省值、上限都写在注释里，实现与前端展示都以它为准。
生成产物已生成（**不要重新生成**）：Go 在 COMMON 同目录 `*.pb.go`；TS 在 `nc-js/packages/catalyst/contract/rpc/scheduler/proto/{lifecycle_rpc,search_admin_rpc}/`。

## 4. 系统事实（实现时直接用，不要再花时间考古）

### 4.1 日志与 SLS
- API 服务（osec-resource-api）与 SPIDER 各进程都用 `github.com/1second/pan/common/utils/logger`（源码 `/home/peterq/dev/projects/1s/pan/common/utils/logger/`）写阿里云 SLS；每条日志的顶层字段：`content / environment / host / level / service / location / type(logger 名) / stage / data(JSON 字符串)`（见 `ali-log.go` `groupHook.Fire`）。
- API 日志：project `resource-backend`，logstore **`resource-backend`**，`service=resource-search-api`。
  - v2 搜索入口 `GET /api/v2/search`：`type=resource-api`，`stage=search`，`data` 含 `kw/uid/ip/userAgent/duration(ms)/backend(v2|v3)/canaryPercent/result{total,size}` 及全部 query 参数（`controller/api.go` `SearchApi`）。
  - v3 搜索入口 `GET /api/v3/search`：`type=resource-api-v3`，`stage=search-v3`，字段同上（无 backend）（`controller/api_v3.go`）。
  - 搜索出错时 `level=error`（`ErrorOrInfo`）；gin 访问日志另有 `stage=GET:/api/v2/search` 一类记录（`data.latency/status/ip`），**总览以 stage=search/search-v3 为准**。
- SPIDER 网关日志：同 project，logstore `resource-spider`（与 API 不同库）。
- 网关已有 SLS 只读封装可抄：`osec-spider-go/services/gateway/queue_admin/sls.go`（`GetLogs` + 字段映射）。SDK `github.com/aliyun/aliyun-log-go-sdk`：`GetLogs(project, logstore, topic, from, to, query, maxLine, offset, reverse)`，query 里 `<检索> | select ...` 即为查询分析（SQL）；结果 `resp.Logs []map[string]string`，SQL 结果列名即 map 键。
- **SLS `resource-backend` logstore 的 `data` 字段是否开启了「统计（SQL 分析）」未知**（主控的只读探针被 auto 模式分类器拦截，未能验证）。只读探针工具已写好：`osec-spider-go/tools/sls-probe`（凭据从环境变量读，不打印）。实现方**必须**做双路径：SQL 优先，探测失败（返回错误含 `IndexConfigNotExist`/`analysis`/`not enable statistics` 等）自动降级为「拉原始日志逐条聚合」。
- 凭据：网关配置 `gw_config.Get().AliLog`（endpoint/ak/sk/project，线上 `_note/config/spider.prod.yaml` 的 `ali_log`，**不要把 ak/sk 写进代码、日志、提交、简报**）。

### 4.2 Redis
- API 与网关使用**同一个 redis**：`192.168.7.145:16379 db 6`（API `config.GetRedis()`；网关 `gw_config.Get().Redis`）。因此「关闭匿名搜索」用共享键即可，无需新增服务间调用。
- 键约定（API 与网关都按此实现，**不得各改各的**）：
  - `search_guard:anonymous_closed`：值为 JSON `{"reason":"…","by":"auto|manual:<user>","closedAtMs":…,"untilMs":…}`，TTL = 关闭时长；**键不存在 = 开放**。
  - `search_guard:params`（hash，热更新参数覆盖）、`search_guard:state`（hash，leader 写的最近巡检结果）、`search_guard:events`（list，LPUSH + LTRIM 200）、`search_guard:alert_debounce:<rule>`（SETNX 去抖）、`search_guard:leader`（抢主锁）。
- lifecycle 已有 redis 计数器：`osec-spider-go/services/gateway/lifecycle/stats.go`（`resLc:cnt:<name>:YYYYMMDDHHMM` 分钟桶 TTL 2h，`resLc:cntd:<name>:YYYYMMDD` 天桶 TTL 10d，name ∈ valid/invalid/error，**目前不分类型**）。

### 4.3 数据库 / ES（分享链接总览用）
- `res_lc_event`（`lifecycle/models.go` `ResEventModel`）：`res_id/type/event/from_index/to_index/detail/operator/created_at`，索引 `idx_created(created_at)`、`idx_res(res_id)`。事件常量 `EventCreated="created"`、`EventUpdated="updated"`、`EventInvalid="invalid"`、`EventMoved="moved"`、`EventLegacyInvalidHint="legacy_invalid_hint"`。写入点：`rpc_service.go ReportUpsert`（created/updated 仅当 `changed=true`；moved）、`result.go onCheckInvalid`（invalid）、`legacy_hint.go`。
- 检测结果处理：`result.go` `onCheckValid/onCheckInvalid/onCheckError` → `metricCheckResultTotal`（Prometheus，带 type 标签）+ `s.counts.Add(counterValid|counterInvalid|counterError, 1)`。
- 存量快照：`Service.Stats()`（≤60s 缓存，`stats.go`）→ `StatsSnapshot.ByType[type]{Active,Invalid,DueBacklog}`；`rpc_service.go Overview` 里已有转成 `lifecycle_rpc.TypeStat` 的代码可复用。
- ES：网关 `lifecycle` 持有 `esapi` 客户端（`esops.go`，`s.es`），别名 `res_lc_cur/prev/long/all`（`s.conf.AliasAll`），旧索引 `gw_config.Get().EsResourceIndex`。资源文档字段（`lifecycle/assets/template_res_short.json`）：`type`(keyword，取值是 ES 侧名 baidu/aliyundrive/quark/xunleipan，与 spider_contract 常量的映射见 `lifecycle/typemap.go`)、`client`(keyword，爬虫/提交端名，= 来源)、`ctime`(date, 收入时间)、join 字段 `resource/file`。**统计前先按 `lessons/patterns-统计ES索引先查文档形态.md` 核对文档形态**（父子文档混杂，直接 count 会把文件子文档算进去；要用 `type` 存在或 join=resource 过滤，并用两种写法对拍）。

### 4.4 网关模块注册方式
`services/gateway/gateway.go` `Start()` 里依次 `queue_admin.Register / proxy_admin.Register / lifecycle.Register`（注册失败只记日志不阻断）。新模块照 `proxy_admin/register.go` 的写法；配置节放 `config/gateway/gateway.go` 的 `Services` 下（参考 `Services.Lifecycle`/`Services.QueueAdmin` 的声明与 `applyDefault` 回落写法；配置按进程拆的是**代码**不是文件，见 `decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`）。
leader 抢主锁写法：`queue_admin/worker_leader.go` 或 `lifecycle/leader.go`（两台网关 osec-res1/res2 都在跑，巡检类后台任务必须 leader-only）。
告警邮件写法：`lifecycle/alert.go` `fire()`（POST `notify_url` JSON `{subject, htmlContent, source}`，redis SETNX 去抖）。

### 4.5 前端
- 后台是 `nc-js/admin/spiderAdmin`（Vue 3 + TSX `defineComponent` + ant-design-vue），**没有路由表**：`layout/navState.ts` 加 `MenuKeys` → `layout/AppLayout.tsx` 的 `<Menu>` 加项 + `LazyKeepAlive` 插槽加 `<Page>`。
- RPC 客户端在 `packages/catalyst/contract/rpc/spiderGw/spidergw.ts` `useGwClient()` 里用同一条 RTC 连接创建（看 `lifecycleRpc` / `proxyAdminRpc` 的创建与返回，照抄）；mock 开关 `lifecycle.ts` + `lifecycleMock.ts`。
- 可复用组件：`pages/queue/MiniLineChart.tsx`（SVG 折线图，`series: {name,color,points:{ts,value}[]}[]`）；页头 `layout/Page.tsx`/`PageHeader.tsx`；格式化 `pages/lifecycle/format.ts`、`pages/proxy/format.ts`。
- 测试：`admin/spiderAdmin/src/pages/lifecycle/__tests__/smoke.test.tsx` 是 mock 冒烟测试范本（绕开 `useGwClient`，直接 Provider + mock 客户端挂载）。

## 5. 硬性约束（违反会返工或出事故）

1. **绝对不要运行 NC-JS 的 `pnpm build`/`build-only`**：会真实上传生产 OSS 并改写 apps.json（`lessons/failure-ncjs构建脚本会自动上传OSS.md`）。只允许 `vitest`、`vue-tsc`/type-check、`lint`。
2. **不要 ssh 生产主机、不要跑 deploy.sh、不要改线上配置、不要对生产 ES/MySQL/redis 做写操作**。本地联调只用本地 redis/mysql/单测桩。读线上 SLS 只允许通过 `tools/sls-probe`（若被权限拦截就放弃，改用桩数据并在汇报里说明）。
3. **敏感信息**：`_note/config/*`、`config*.yaml` 里的 ak/sk/口令**只能读不能抄**，不得出现在代码、测试、日志、提交信息、汇报邮件里。
4. 旁路功能（监控/告警/统计）的初始化必须**可降级**：SLS 未配置、redis 抖动、ES 超时都不能让网关或 API 主流程 panic/Fatal（`lessons/failure-旁路能力初始化拖垮主流程.md`）。API 侧读 redis 失败一律 **fail-open**（放行匿名搜索并记日志）。
5. proto3 零值语义：`0`/空串 = 不过滤/用缺省，需要「未知」态时不要用 `-1` 与零值混用（`lessons/failure-proto3零值与负一哨兵冲突.md`）。
6. 所有 RPC 的时间范围参数要做上限校验（proto 注释写了上限），拒绝无界查询；长查询要有 60s 级缓存（key 含全部参数）。
7. 每个角色完成后 `go vet ./...` / `go test ./<改动包>/...` 必须通过；前端 `vitest` + type-check 必须通过。

## 6. 汇报

- 完成或被阻塞（权限拦截、契约有问题、依赖缺失）时，在最终回复里按各自简报「交付」一节汇报；**不要**自行发邮件（主控统一发）。
- 若发现契约与实现无法自洽（字段缺失/语义冲突），停下来在最终回复里说明，不要私自改 proto。
