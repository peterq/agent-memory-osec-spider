---
title: queue-admin 队列监控管理系统
type: knowledge
status: active
created_at: 2026-09-04T18:10:00+08:00
updated_at: 2026-09-08T16:00:00+08:00
priority: high
keywords: [queue-admin, 队列监控, QueueAdminRpc, detailSchema, 7542, 抢主锁, dlock, 巡检, 告警]
summary: 队列 v2 的监控管理系统：已并入网关进程的架构、端口、schema 解耦机制、抢主锁、巡检工具与已知数据缺口
load: on-demand
related:
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/knowledge/architecture-nc-js.md
  - agent-memory/decisions/decision-2026-09-04-管理服务并入网关.md
  - agent-memory/sessions/2026/2026-09-04-队列监控系统queue-admin.md
---

# queue-admin 队列监控管理系统

## 一句话

监控/管理网关 res_scheduler 全部队列（6 资源队列 + 动态关键词队列 + clearExpire），
队列读写全走 `Queue2` Lua 脚本保证与网关 seq 语义一致。

> **[事实 2026-09-04 晚] 已由独立进程并入 `spider_gateway` 进程**，见
> `decisions/decision-2026-09-04-管理服务并入网关.md`。下文均为并入后的现状；
> 早期"独立进程 / 7543 / 7581 / 独立 rtc_token"的描述已全部作废。

## 架构与位置

- PRD（需求唯一来源）：`osec-spider-go/PRD/queue-admin/README.md`（v1.2）
- 契约：COMMON `rpc/spider/queue_admin_rpc/queue_admin.proto`（`QueueAdminRpc`，13 个方法）
- 后端：SPIDER **`services/gateway/queue_admin/`**，入口是 `register.go` 的
  `Register(rtcServer, grpcServer, gwRds)`，由 `services/gateway/gateway.go` 的 `Start()` 调用
  （注册失败只记日志，不阻断网关启动）。**没有独立子命令**。
  另给 `illuminate/queue-task` 新增了 4 个只读方法（`DecodeScore`/`GetQueuedKeysWithScores`/
  `GetTaskScore`/`GetOldestKeepalive`），零侵入。
- 前端：NC-JS **`admin/spiderAdmin/src/pages/queue/`**（左侧栏"队列监控"分组的 4 个页面），
  RPC 与其余网关服务共用**同一条** RTC 连接。
- 部署：**随网关一起**，`./deploy.sh deploy gateway`（osec-res1 + osec-res2）。
  配置继承网关：`services.queue_admin` 节线上不分发，redis / SLS 凭据缺省从 `gw_config` 继承。
- 端口/鉴权：网关 RTC **7542** + 网关原生 gRPC **:8082**，鉴权与网关握手共用同一套机制
  （[事实 2026-09-08] 已改为 GitHub OAuth 会话票据，`RtcToken` 降为可关闭兜底，见
  `decisions/decision-2026-09-08-后台登录改为github-oauth.md`，代码未部署前仍是旧的
  `gw_config.RtcToken` 单一校验）。

## 关键机制

- **detailSchema 前后端解耦**：后端 `schema.go` 注册表 → `GetDetailSchemas` 下发 JSON →
  前端通用渲染器（`SchemaRenderer.tsx`）按 matcher（queues 数组 / queuePrefix）匹配渲染；
  未知 widget/无 schema 一律 `JsonTree.tsx` 兜底。**新增任务类型只在后端注册 schema，前端零改动**。
- **双实例抢主锁**（`worker_leader.go`）：网关跑在两台机，指标采集轮询（`metrics.go`
  `startMetricsPoller` 三个 goroutine）与告警巡检（`alert.go` `run()`）每轮开始判 `IsLeader()`，
  非 leader 直接跳过。锁用 `dlock`，前缀 `queueAdmin:worker`，TTL 90s / 续期 30s / 抢不到 10s 重试。
  leader 掉线后靠 TTL 过期自动切换。
  ⚠️ 已知限制：告警 `sustain()` 的持续时长是**进程内存态**，leader 切换会重置计时。
- **年龄指标不靠 meta**：网关所有 Push 调用点传 nil meta，`enqueueAt` 从不落 hash；
  waiting/pending zset 的 score = `priority<<48 | 入队毫秒时间戳`，用 `DecodeScore` 解出
  入队时间（redis double 53 位精度，误差最多 1~2 秒）。`ListTasks/GetTask` 的 enqueueAtMs 同源回填。
- **写操作安全**：seq 必须非零且一致（底层 Lua 对 seq=0 是"跳过校验"宽松语义，应用层强制收紧）；
  批量操作强制 dryRun 先行 + limit≤500 + delete 默认仅 waiting。
- 告警 6 条规则内置于进程（积压/老化/停摆/关键词失联/失败率/自身异常），邮件走 notify_admin，
  redis 键 `queueAdmin:alertDebounce:*` 去抖 1 小时。
- 指标 `queue_admin_*` 经 COMMON prom 推 ARMS；吞吐/失败 counter 从 SLS SQL 聚合。
  `queue_admin_poll_error_total` 带 `host` label（**无 label 的 Counter 会被非 leader 的 0 值
  覆盖**——`prom.New` 只用 job 做 pushgateway grouping key，不带 instance）。

## 运维

- 巡检工具：`osec-spider-go/tools/queue-admin-check/`（`-state waiting|pending`，`-touch` 做
  "改优先级为原值"的无害写闭环）。默认 `-addr 127.0.0.1:8082`（网关原生 gRPC）。
  远程用法：`ssh -N -L 18082:127.0.0.1:8082 osec-res1 &` 后 `-addr 127.0.0.1:18082`。
- 前端连接：无需任何额外配置，与网关同一条连接、同一把管理秘钥；Mock 开关在顶栏（开启时显示紫色 Tag）。

## 已知数据缺口（网关侧既有问题，PRD 约束不改网关）

- 资源队列 `queue_push_total` / `QueueStats.push` 无数据（网关入队不打结构化日志）
- 总览 `consumerHosts` 在生产恒为 0（网关 Pop 传 nil meta，不写 consumeHost）
- waiting 常态为 0（消费者阻塞式秒取），积压类指标只在真出问题时才非零——这是正常现象
