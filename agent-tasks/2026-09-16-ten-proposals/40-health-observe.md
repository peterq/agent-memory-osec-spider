# 角色 40：账号池/站点健康告警 + 队列可观测性（提案 6、7 后端）

短名 `health-observe`。worktree：`common-wt-health-observe`、`spider-wt-health-observe`（分支 `feat/health-observe`）。前端页面由另一角色在你交付契约后做，**契约要先定稿并提交**（见 §设计 1）。

## 目标

1. **账号池健康**：转存下载链路的网盘账号（阿里 refresh token、百度 BDUSS）失效后目前无告警、无效重试空转。要做：定时（leader-only）探测账号可用性 → 失效自动出队（调用已有 `SetEnablePanAccount(false)` 语义）+ 告警邮件 + 事件记录；RPC 暴露账号健康列表与手动重检。
2. **站点/爬虫健康**：按爬虫（`client`/队列名）统计近 1h/24h 任务成功率、连续失败次数、最近成功时间；连续 N 小时零成功自动进入「下线候选」并告警（背景：`keyword_funletu` TLS 证书错误长期失败、三个 keyword 站 0 成功却无人知道）。RPC 暴露列表。
3. **队列可观测性**：`gateway_v2.QueueLength/ListTask` 契约已有，核对 `spider_gateway_service.go` 的实现是否覆盖队列 v2 全部队列（含 lifecycle `dueBacklog`、clearExpire、动态关键词队列）；缺的补齐；所有队列长度/积压/消费速率导出 Prometheus 指标（网关已有 `queue_admin/metrics.go` 风格），并给 `queue_admin` 的告警引擎加「绝对阈值」规则类型（现有规则看 `alert_rules.go`）。

## 必读

1. `agent-memory/knowledge/domain-转存下载链路.md`（账号池现状、失效表现）；SPIDER `services/gateway/download_scheduler/download_scheduler_service.go`（`SetEnablePanAccount` 约 393 行）、`pan_download/pan_acc_worker.go`、`resolve_worker/resolve_mgr.go`（账号模型与失效表现）。
2. `agent-memory/knowledge/architecture-queue-admin.md`；SPIDER `services/gateway/queue_admin/{alert_rules.go,stats.go,metrics.go,alert_logs.go,worker_leader.go}`。
3. `agent-tasks/2026-09-16-share-search-overview/00-shared.md` §4.4（模块注册、配置节、leader 锁、告警邮件写法）。
4. COMMON `rpc/spider/download_scheduler_rpc/*.proto`、`queue_admin_rpc/queue_admin.proto`、`rpc/spider/gen.sh`（生成方式；`go_package` 有旧仓库名需 sed 的坑见 `agent-memory/current/tasks-backlog.md`）。

## 设计

1. **契约（先做，单独提交，汇报里给 hash）**：COMMON 新 `rpc/spider/health_rpc/health.proto`：`HealthRpc { AccountHealth, RecheckAccount, SiteHealth, SetSiteDownlineCandidate(ack/ignore) }`；`queue_admin.proto` 的告警规则加 `abs_threshold` 类字段（保持向后兼容，只加不改）。每个字段写中文注释：口径、缺省、上限。用 `gen.sh` 生成 Go；TS 生成不归你（前端角色做）。
2. SPIDER 新模块 `services/gateway/health/`：`register.go`（照 `proxy_admin/register.go`）、`accounts.go`、`sites.go`、`alert.go`、`config`（节 `services.health`，缺省值内置：探测间隔 10 分钟、零成功判定 6 小时、去抖 1 小时）。探测账号用现有下载链路里的「刷新 token / 取用户信息」调用，**不能真的发起转存**。
3. 站点健康数据源：`queue_admin` 已有的队列统计/trace（`stats.go`/`trace.go`），不要另起一套采集；缺的字段在 `queue_admin` 里补。
4. 事件落 redis list（`health:events`，LPUSH+LTRIM 500）；告警走 `lifecycle/alert.go` 的 `fire()` 风格（去抖）。
5. 全部旁路、可降级；leader-only。

## 文件所有权

COMMON：`rpc/spider/health_rpc/**`、`rpc/spider/queue_admin_rpc/queue_admin.proto`（只加字段）+ 生成物、`rpc/spider/gen.sh`（只加一行）。
SPIDER：`services/gateway/health/**`、`services/gateway/queue_admin/{alert_rules.go,metrics.go,stats.go}`（只加）、`services/gateway/spider_gateway/spider_gateway_service.go`（QueueLength/ListTask 补全）、`services/gateway/gateway.go`（加一行注册）、`config/gateway/gateway.go`（加字段）、`services/gateway/download_scheduler/**`（只加探测入口，不改现有行为）。

## 验证

`go build ./...`；`go vet`/`go test` 覆盖 `services/gateway/health`、`queue_admin`；单测用假账号探测器与 miniredis。

## 交付

契约提交 hash（前端角色依赖）、RPC 方法与字段说明、告警规则说明、测试输出、需主控在生产核对的事项。
