---
title: SPIDER 队列约定（队列 v2，网关统一调度）
type: knowledge
status: active
created_at: 2026-09-12T11:25:00+08:00
updated_at: 2026-09-16T09:30:00+08:00
priority: medium
keywords: [队列, 队列v2, resourcePreCheck, gw_remote_queue, res_scheduler, keywordSubscribed, gateway_v2, QueueDefine, 去重, taskKey, consumer, devops_migrate_legacy_queues]
summary: SPIDER 队列 v2 的固定队列名、去重键、消费者并发度与通用队列接口约定
questions:
  - 我要写新的网关队列消费者，代码放哪
  - 关键词站点怎么收关键词
  - 爬虫怎么提交链接给网关
load: on-demand
related:
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/decisions/decision-2026-09-04-队列v2统一走网关.md
---

# SPIDER 队列约定（队列 v2，网关统一调度）

本文件是 `architecture-spider.md` 拆出的一部分，专记队列名/去重键/消费者并发度等细节。
仓库结构、入口子命令、编译状态、配置读取见 `architecture-spider.md`。

**[事实] 跨进程任务投递一律走网关，爬虫进程不再直连 redis 队列。** 决策见
`decisions/decision-2026-09-04-队列v2统一走网关.md`。

- `res_scheduler` 固定队列名（常量在 COMMON `rpc/spider/res_scheduler_rpc/res_rpc.go`，`ResourceQueueNames()` 列全）：
  - `resourcePreCheck`：所有分享链接的统一入口，taskKey = `ResTaskKey(typ,id)` = `<type>:<id>`。
    网关内置消费者（`services/gateway/res_scheduler/pre_check.go`，8 协程）做：识别类型 → `ShareLinkFromId` 规范化 +
    从 `?pwd=` 补提取码 → redis `resDealAt:<typ>:<id>:<pwd>` 6h 去重 → 路由到下游；下游 waiting≥2000 时背压等待并 keepalive；
    推下游失败会回滚去重 key 再交网关重试（maxRetry=3）。
  - 下游：`bndInputPwd`(百度带码) / `bndLoadShare` / `aliLoadShare` / `quarkLoadShare` / `xlLoadShare`，taskKey = 分享 id。
  - 关键词：网关 `CommitKeyword` 直接 8h 去重（`keywordDealAt:<kw>`）并扇出到 `keywordSubscribed:<site>`（单队列上限 2000）；
    站点通过 Pop 自动注册进 ZSET `kwSiteListeners`（5 分钟心跳有效），关键词就是 taskKey，maxRetry=2。
- 客户端辅助 `services/v2/gw_remote_queue/res_queue_helpers.go`：`NewResConsumer(resCli, q)`、`NewKeywordConsumer(resCli, site)`、
  `PushResTask(s)`、`PushKeywords`、`IsTaskExists`。
- 生产者：爬虫一律 `spider_common.NewResLinkCommitter().CommitResLink()`（内部按需建网关连接，调用方标识取 `os.Args[1]`），
  链接已在预检队列中返回 `resource.ErrDupTask`。外部系统走网关 `SpiderRpc.CommitResource/CommitKeyword`。
- 消费者模式：`queue_task.StartQueueRemoteConsumer(name, opts, gw_remote_queue.NewXxxConsumer(...), handler)`；
  handler 返回 nil=成功，`queue_task.MarkPermanentError(err)`=永久失败出队，其他 error=网关重试。
  各消费者：`v2bndInputPwd`/`v2bndLoadShare`(50)、`v2aliLoadShare`(20)、`v2quarkLoadShare`(50)、`v2xlLoadShare`(20)，
  代码在 `services/v2/res_crawler/{bnd,ali,quark,xl}`；`keyword_*` 6 站各 20。
- `gateway_v2` 通用队列（下载链路专用）：`QueueDefine[T]{Namespace, QueueName, Version}`，默认 JSON 编解码，`FullQueueLen` 本地 dev=10 / 线上=1000。
  命名空间 `resDlAcc`、`resDl`、`webResDl`，见 `services/gateway/gw_contract/gw_queues.go`。
- **[已废弃 2026-09-04]** `illuminate/queue-task/service.go` 的 `Service`（redis list `service:<name>:queue:task`）及
  `share`/`share_pwd`/`ad_share`/`quark_share`/`xunlei_share`/`keyword_filter`/`file_bot`/`urn` 命令已删除。
- 旧队列存量迁移：`./spider devops_migrate_legacy_queues`（默认 dry-run；`--apply --dry-run=false` 才写），
  把 17 个旧 list/pending hash 迁到网关队列，README 在 `services/devops/2609/migrate_legacy_queues/`。
- 运维调试代理：`v2aliLoadShare`/`v2xlLoadShare` 进程起 `:9527` 的 `/proxy?url=&method=`（经代理池转发），
  公共实现 `services/spider-common/debug_proxy_server.go`，同机第二个进程绑不上端口只记 Warn。
- 仍直连 redis 的例外：`devops_check_and_push_clear_queue`（`Queue2` 直连，线上 4 台在跑）与网关 clear 消费者配套，未迁移。
</content>

## 代码位置

- `services/keyword/sp2023/funletu.go`（关键词站点消费者参考实现）
