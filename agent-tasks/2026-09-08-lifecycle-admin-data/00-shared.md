# 共享上下文：把 res_lc_* 数据纳入管理后台

> 所有参与本任务的子 Agent 都必须先读完本文件，再读自己那份角色简报。

## 1. 任务目标

「资源生命周期」管理后台目前只能按 url / id **精确查单条**资源（`QueryResource`），
64 张资源分表 + `res_lc_event` 事件表没有任何列表化、统计、诊断入口。
本次为后台补齐 4 块**纯只读**能力：

| # | 能力 | rpc |
|---|---|---|
| 1 | 资源列表浏览（多条件筛选 + 分页） | `ListResources` |
| 2 | 分表统计看板（行数与维度分布） | `TableStats` |
| 3 | 事件流水查询（`res_lc_event`） | `ListEvents` |
| 4 | 分表运维诊断（表/列/索引/大小 + DB↔ES 对拍） | `TableDiagnostics` |

用户已明确：**本期只读**。不做批量写操作，不做批量改 status。
第 4 项的"运维"也只做**诊断报告**——发现缺表缺列时把建议命令列进 `suggestions` 字段
交人工执行，后台自己不执行任何 DDL。

## 2. 仓库与分支

| 角色 | 路径 | 分支 |
|---|---|---|
| COMMON（契约中心） | `/home/peterq/dev/projects/1s/enfi-resource-common` | master，契约已提交 `3c0f4f8` |
| SPIDER（网关后端） | `/home/peterq/dev/projects/1s/osec-spider-go` | `feat/lifecycle-admin-data`（已建好并切换） |
| NC-JS（后台前端） | `/home/peterq/dev/projects/1s/nc-js` | `feat/lifecycle-admin-data`（已建好并切换） |

代码注释、界面文案、提交信息一律**中文**。

## 3. 契约（已定稿，任何人不得修改）

契约源文件：
`/home/peterq/dev/projects/1s/enfi-resource-common/rpc/spider/lifecycle_rpc/lifecycle.proto`

**必须完整读一遍文件末尾「res_lc_* 数据浏览(只读)」一节。** 那里的注释是硬性设计约束，
且写清了每个字段的语义、取值范围、`-1`/`0` 表示"不过滤"的约定，以及
`maxOffset` / `withTotal` / `exact` 这几个开关为什么存在。字段语义弄错会导致查错数据。

生成产物（已生成，**不要重新生成**）：

- Go：`rpc/spider/lifecycle_rpc/lifecycle.pb.go`、`lifecycle_grpc.pb.go`
  （SPIDER 经 go.mod replace 指向本地 COMMON 路径）
- TS：`nc-js/packages/catalyst/contract/rpc/scheduler/proto/lifecycle_rpc/lifecycle.ts`、`lifecycle.client.ts`

## 4. 硬性约束

### 4.1 绝对只读

不得有任何 INSERT / UPDATE / DELETE / DDL。前端不得出现任何新的写操作按钮
（资源详情页已有的单条「立即检测 / 搬迁」是既有功能，可以复用跳转，不算新增）。

### 4.2 生产背景：全量 bootstrap 正在跑

线上此刻正在跑资源全量 bootstrap 作业，这 64 张分表处于**极高写入压力**（数千行/秒），
MySQL 与 ES 都不能被后台查询拖垮。由此推导出契约里的四条约束：

1. `ListResources` 的 `type` 必填 —— 把扫描面从 64 张表收敛到 16 张，不允许全表扫描；
2. `maxOffset` 限制深翻页 —— 代价随 offset 线性放大，超限服务端直接报错；
3. 精确 `count(*)` 默认关闭 —— 千万级分表上是慢查询，必须由调用方显式置
   `exact` / `withTotal` 才做；缺省走 `information_schema` 估算或只回 `hasMore`；
4. 所有查询强制带超时，超时返回明确错误，不许挂死。

### 4.3 不要碰正在生产跑的代码

SPIDER `services/gateway/lifecycle/` 下的 `bootstrap*.go`、`repair*.go`、`mover.go`、
`rotation.go`、`jobs.go` 正在生产运行，本次不修改它们，也不改任何现有方法的行为。

### 4.4 环境禁忌（踩过的坑）

- **绝对不要在 NC-JS 跑 `pnpm build`**：子应用的 `mfe()` 构建插件默认 `deploy:true`，
  `pnpm build` 会把产物**真实上传到生产 OSS**，且构建报错也不代表没部署。本项目踩过一次。
  想看渲染效果就用 `pnpm dev` + Mock 开关。
- 本次**只开发与本地验证，不部署**。网关双机现在跑的是 `hotfix/p4-bootstrap` 分支，
  bootstrap 完成前不能动。

## 5. 交付要求（所有角色通用）

- 在**自己仓库的 `feat/lifecycle-admin-data` 分支**上 `git commit`，
  提交信息用中文、遵循该仓库现有的 conventional commits 风格，末尾加一行：
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
- **不要 push**（由主控统一验收后处理）。
- 汇报内容：新增/修改了哪些文件、实现要点、验证命令的**实际输出**、
  以及任何你认为契约设计有问题或对端需要注意的地方。
