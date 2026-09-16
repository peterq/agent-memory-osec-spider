---
title: 搜索监控与匿名搜索防护（网关 search_admin 模块）+ 分享链接总览（lifecycle.ShareOverview）
type: knowledge
status: active
created_at: 2026-09-16T07:40:00+08:00
updated_at: 2026-09-16T08:15:00+08:00
priority: high
keywords: [search_admin, SearchAdminRpc, 搜索总览, 匿名搜索防护, search_guard, SLS, ShareOverview, 分享链接总览, sls-probe, search-admin-check]
questions:
  - 后台搜索总览/Top 榜数据从哪来, source=sls-scan 是什么意思
  - 匿名搜索被关闭了怎么回事, 在哪手动开放/调阈值
  - 分享链接总览的检测数为什么早期是 0, 新增按来源怎么算
  - 上线后怎么验证 search_admin 和 ShareOverview
summary: 网关 search_admin 模块（SLS 搜索日志聚合、p90 巡检→邮件+关闭匿名搜索、redis 键约定、SQL/扫描双路径）与 lifecycle.ShareOverview（res_lc_event+按类型计数器+ES client 聚合）的架构、配置、验证工具与已知口径限制
load: on-demand
related:
  - agent-memory/decisions/decision-2026-09-16-搜索p90告警关闭匿名搜索与总览数据源.md
  - agent-memory/knowledge/architecture-api.md
  - agent-memory/knowledge/architecture-queue-admin.md
  - agent-memory/knowledge/architecture-nc-js-qiankun与后台页面.md
---

# 搜索监控 / 匿名搜索防护 / 分享链接总览

正本文档：SPIDER `services/gateway/search_admin/README.md`、`services/gateway/lifecycle/README.md`「分享链接总览」节、任务简报 `agent-tasks/2026-09-16-share-search-overview/`。本文只记跨会话要知道的事实与坑。

## 1. 位置与契约
- [事实] 契约 COMMON `rpc/spider/search_admin_rpc/search_admin.proto`（`SearchAdminRpc`：Overview/Top/GuardStatus/SetAnonymous/UpdateGuardParams）与 `lifecycle_rpc/lifecycle.proto` 的 `ShareOverview`；生成脚本 `rpc/spider/gen.sh` 与 NC-JS `packages/catalyst/scripts/devops/protc_gen.sh` 都已登记新 proto。
- [事实] 网关模块 `services/gateway/search_admin/`（与 queue_admin/proxy_admin/lifecycle 同模式并入网关，`gateway.go Start()` 注册，失败只记日志）。配置节 `services.search_admin`（`config/config.go` `SearchAdminConfig`），线上不分发也可运行：SLS 凭据回落 `gw_config.AliLog`，`log_store` 缺省 `resource-backend`（API 日志库，**与网关自己的 `resource-spider` 不是一个库**）。
- [事实] API 侧 `osec-resource-api/services/search-guard`（`SearchApi`/`SearchApiV3` 对 `uid=="anonymous"` 读键即 403/50008「请登陆后再搜索」，redis 出错 fail-open，1s 本地缓存，配置节 `search_guard`）。
- [事实] 前端 spiderAdmin 4 页：「资源生命周期 → 分享链接总览」（`pages/lifecycle/ShareOverviewPage.tsx`）、新菜单组「搜索监控」：搜索总览 / 搜索词 Top1000 / 匿名搜索防护（`pages/search/*`）；共用 `pages/common/TimeRangeBar.tsx`；mock 开关 `searchAdminMock`（localStorage）。

## 2. 搜索总览数据口径
- 检索前缀 `service:resource-search-api and (stage:search or stage:search-v3)`；字段取自 `data` JSON（kw/uid/ip/duration/backend/result.total/guard）。`v2Count = count - v3Count`；`distinctUids` 排除 anonymous/空。
- **SQL 优先、失败降级扫描**：`sls.sql=auto` 启动探测 + 每小时重探 + 查询报错当场降级；降级时 `source=sls-scan`，拉原始日志上限 `max_scan_lines`（缺省 5 万）→ `truncated=true`。**看数据先看 source/truncated/note**。
- [事实 2026-09-16 上线实测] `resource-backend` logstore 的 SQL 分析可用：Overview/Top `source=sls-sql`，1 小时窗口 30~200ms；若将来变成 `sls-scan`，先看 `note` 再查 SLS 索引配置。
- [事实] 检索前缀 `stage:search` 会分词命中 gin 访问日志 `GET:/api/v2/search`，已在 SQL 加 `where stage in (...)`、扫描路径 `filterByEntry` 精确过滤（`65a1bf8`）→ `lessons/failure-SLS字段检索按分词匹配误命中其他stage.md`。
- 结果缓存 60s；`toMs` 贴近当前时刻时向下对齐整分钟做缓存 key。

## 3. 匿名搜索防护
- leader-only 巡检（锁 `search_guard:leader`），缺省：每 60s 查最近 300s，`p90>3000ms` 连续 2 次且样本 ≥30 → 邮件（source `search-guard`，去抖 1800s）+ `autoClose` 时 `SET search_guard:anonymous_closed <json> EX 1800`（已关闭则续期）。到期自动开放并记 `auto_expire` 事件。
- 参数热更新在 redis hash `search_guard:params`（后台「匿名搜索防护」页可改，不用重启）；`autoClose=false` 只告警不关闭。
- 应急：`redis-cli DEL search_guard:anonymous_closed` 立即开放（正常走后台页面，会记事件 + 发邮件）。
- redis 键全表见 README；**API 与网关必须同一套键约定，改一侧必须同步另一侧**。

## 4. 分享链接总览口径（ShareOverview）
- created/updated/invalid/moved/legacy_invalid_hint ← `res_lc_event` 按桶 GROUP BY（`AggregateEvents`，走 `idx_created`）；**updated = 再爬发现 version 变化 = "检测有更新"**，检测本身只判有效性不判更新。
- checked/valid/invalid/error ← 新按类型计数器 `resLc:cnth:<name>:<type>:YYYYMMDDHH`（35 天）/`resLc:cntd:<name>:<type>:YYYYMMDD`（400 天），起算时间 `resLc:cnt:since`；上线前的时间段为 0 并在 warnings 说明。旧全局分钟/天桶与 `LastHour/LastDays` 未变。
- 新增按来源 ← ES `client` terms（`ctime` 区间，别名 `res_lc_all`，父文档过滤 `term join=resource`）；与事件 created 并列展示不做对账。[待确认] `term join=resource` 与 `exists type` 两种过滤线上对拍（README 给了 curl）。
- 跨度 ≤92 天；hour/day 桶按容器本地时区（基础镜像 `app-env-docker/ubuntu` 已设 Asia/Shanghai）；任一数据源失败只进 warnings；60s 缓存（失败结果也缓存）。

## 5. 上线记录（2026-09-16）
- COMMON `f2f0881`；SPIDER 主干 `2e34623`（功能）→ `65a1bf8`（stage 修复）→ `6cb69db`（工具），网关 res1/res2 `deploy.sh gateway` 部署两次；API `2458a52` 两台部署（res2 首次 ssh 超时，用 `source <(sed -n "1,48p" deploy.sh); deploy pplabs@osec-res2; dockerRun pplabs@osec-res2` 单机补部）；NC-JS `dbbbbcc` `pnpm build` 上传 OSS。
- 端到端：`tools/search-guard-ctl -close -minutes 1` 后 res1 出现 403 + `guard=anonymous_closed`；两台只有一台 `leader=true`（重部后 leader 会换主机）。
- 首次 24h ShareOverview 在冷 ES 上 41s、之后 0.6s；ES `esCreated` 明显小于事件 `created`（quark 19k vs 32k），属并列口径，未对账。

## 6. 验证与排障工具
- `osec-spider-go/tools/search-admin-check`：ssh 隧道到网关 :8082 后一条命令打印搜索总览 / Top / 防护状态 / 分享链接总览（只读）；两台各跑一次确认只有一台 `leader=true`。
- `osec-spider-go/tools/search-guard-ctl`：命令行手动关闭/开放匿名搜索（同后台页面接口，记事件 + 发邮件），应急与验证用。
- `osec-spider-go/tools/sls-probe`：对任意 logstore 跑一条 SLS 查询/分析语句（凭据走环境变量）。[事实] 在 Claude Code auto 模式下本机直连生产 SLS 会被分类器按「Production Reads」拦截。
