---
title: API 查询服务结构
type: knowledge
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T12:10:00+08:00
priority: high
keywords: [API, osec-resource-api, gin, 路由, 限流, 黑名单, 搜索, res_lc, 分表, 资源列表, 事件流水, 表诊断, LifecycleRpc]
summary: osec-resource-api 的路由表、中间件链、依赖服务与后台管理模块；另含 SPIDER 网关 LifecycleRpc 新增的 res_lc 分表数据只读接口（资源列表/分表统计/事件流水/表诊断，供 NC-JS 后台用）
questions:
  - 我要改查询接口/限流/搜索
  - 后台怎么看 res_lc_* 分表数据（资源列表/分表统计/事件流水/表诊断接口）
load: on-demand
related:
  - agent-memory/knowledge/architecture-系统总览.md
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/knowledge/architecture-nc-js-qiankun与后台页面.md
  - agent-memory/sessions/2026/2026-09-08-res_lc数据纳入后台.md
---

# API（`1s/osec-resource-api`，module `github.com/PPIO/enfi-resource-api`）

## 入口 `api-starter.go`

启动顺序：加载配置 → 起 cron（定时刷新 apitoken、违禁关键词）→ 初始化 ES → gin 路由 →
起 `:8089` Prometheus → 注册 `remoteservice`(连 SPIDER gateway) → `valid.NewValidService` → `controller.NewEnfiResourceApi` → `resource_admin.InitApplication` → 优雅退出。

配置文件查找顺序：环境变量 `CONFIG_FILE` → `./config_dev.yaml` → `./config.yaml`。

> `main()` 里有一段硬编码：主机名为 `asus` 时设置 `LOCAL_CONFIG_PATH` 指向 `_note/config.dev.yaml`（作者本机开发用）。

## 中间件链（全局，按顺序）

1. `Metric()` —— `http_request_duration_seconds` / `http_requests_total`
2. `auth.PrivateIpCheck()`
3. `gin.LoggerWithConfig` —— 日志走阿里 SLS（`logger`），跳过 `/api/health/check`
4. `cors`
5. `throttle.Throttle` —— 60s 窗口，配置 `limit_config.minute_rate`，key 为 `api.<clientIP>`

`blackStrategy`（仅挂在重接口上）：10s / 5m / 30m 三档限流，触发后 `throttle.AddBlackIp` 拉黑。
挂了 blackStrategy 的接口：`v2/search`、`v2/fileCtx`、`v2/detail`、`v2/recommend`、`enfi/search`、`enfi/detail`、`enfi/recommend`。

## 路由表

| 分组 | 路由 |
|---|---|
| `/api/v2` | `POST report`、`POST userSubmit`、`POST checkValid`、`POST queryValidAndPwd`、`GET search`、`POST validShareLink`、`GET fileCtx`、`GET detail`、`GET query`、`GET recommend`、`GET suggest`、`POST complaint`、`POST likes`、`POST dislikes` |
| `/api/v2/bt` | `GET detail`、`GET file`、`POST report`、`GET search`、`GET recommend`、`POST magnet` |
| `/api/enfi/` | `GET search`、`GET detail`、`GET query`、`GET recommend` |
| 其他 | `HEAD /api/health/check`、`GET /api/token/get`、`GET :8089/api/metrics` |

## 目录

```text
controller/     api.go(主接口)、bt-api.go(磁力/种子)、com-api.go(健康/token/加解密)、green-api.go(内容安全)
services/
  search/       ES 查询构造（search.go / model.go / bittorrent.go）
  valid/        链接有效性校验（bnd/quark/xunlei api）
  remoteservice/gRPC 客户端（连 SPIDER gateway），cmd/ 下有命令行工具
  apitoken/ blackip/ forbidden/ complaint/ report/ initdata/ parallel-control/ aliyun/
middleware/     auth（PrivateIpCheck）、throttle（限流+拉黑）
resource-admin/ 后台管理模块（InitApplication 注入 service）
resource-config/
api-error/      错误码
util/           GetClientIP 等
```

> `README.md` 内容与本服务无关（是微信服务号 lua 脚本需求文档的残留），不要当作 API 文档读。

## res_lc 分表数据只读能力（2026-09-08 新增）

> ⚠️ 注意归属：以下接口**不属于本服务（osec-resource-api）**，而是 SPIDER 网关 `spider.lifecycle.LifecycleRpc`
> 的新增方法，NC-JS 后台经 WebRTC gRPC 直连网关调用（见 `architecture-nc-js-网关对接.md`）。放在本文件是因为
> 这是目前记忆库里"接口层"知识的落点；proto 定义在 COMMON `rpc/`，Go 实现在 SPIDER `services/gateway/lifecycle/`。

来源：`sessions/2026/2026-09-08-res_lc数据纳入后台.md`。后台此前只能按 url/id 精确查单条 `res_lc_*`
分表资源（`QueryResource`），本次补齐 4 个**纯只读**方法，前端对应页面见
`architecture-nc-js-qiankun与后台页面.md`「res_lc 分表数据后台页面」一节：

| RPC 方法 | 能力 | 关键参数/口径 |
|---|---|---|
| `ListResources` | 分表资源列表（多条件筛选 + 分页） | 必须先指定 `type`（把扫描面收敛到该类型 16 个槽再查，不允许跨类型全表扫）；`dueOnly` 口径与 `ScanDue`/`withDueBacklog` 一致（`status=1 AND next_check_at<=now`） |
| `TableStats` | 分表统计看板（行数与维度分布） | 默认按 `information_schema` 估算，精确统计需显式开启慢查询开关 |
| `ListEvents` | `res_lc_event` 事件流水查询 | `resId` 为空时必须指定时间范围，否则拒绝（防全表扫） |
| `TableDiagnostics` | 67 张表体检 + DB↔ES 对拍 | 只读诊断：报告缺表/缺列/缺索引/对拍差值，建议命令（如 `lifecycle_init_tables`）放进 `suggestions` 交人工执行，**不执行任何 DDL**；DB↔ES 对拍数字来自 `Service.Stats()` 的 ≤60 秒缓存快照，而非实时全量 `COUNT`（bootstrap 高写入压力下避免每次诊断都全表扫描），口径写在响应 `note` 字段 |

已知坑（proto 与前端契约相关）：
- `status` 与 `dueOnly` 是**独立**筛选条件，同时选「失效」+「只看到期」会拼出
  `status=2 AND … AND status=1 AND …` 恒空查询且不报错，前端已加防呆，新增类似筛选组合时要留意。
- `TableDiagnostics` 的 `diff` 字段有 `-1`（未知态）哨兵值，proto3 零值与 `-1` 哨兵冲突的通用坑见
  `lessons/failure-proto3零值与负一哨兵冲突.md`，未知态不能与"有差异"合并处理。
- 8 个相关 proto 的 `go_package` 一度还是重命名前的 `github.com/PPIO/...`，已统一改为 `github.com/1s/...`；
  重跑 COMMON `rpc/spider/gen.sh` 前确认这一点，否则生成代码会把失效 import 写回去导致 `go build` 报错。
