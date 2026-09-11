---
title: SPIDER 爬虫仓库结构
type: knowledge
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-09T01:40:00+08:00
priority: high
keywords: [SPIDER, osec-spider-go, 爬虫, gateway, 子命令, 队列, 队列v2, resourcePreCheck, gw_remote_queue, bnd, 下载调度, bbs, kkpans]
summary: osec-spider-go 的入口子命令、目录分层、gateway 四大调度器与队列约定
load: on-demand
related:
  - agent-memory/knowledge/architecture-系统总览.md
  - agent-memory/procedures/workflow-部署.md
---

# SPIDER（`1s/osec-spider-go`，module `github.com/1s/enfi-spider-go`）

## 入口

`spider.go` 是单二进制多子命令：`./spider <cmd>`，无参数打印全部命令列表。
命令表是 `main()` 里的 `commands` 切片（name / desc / fn），新增服务在这里加一行。
子命令启动时会 `config.SetStdLogFile(cmd)`，日志落到 `<cmd>.log`。

命令分类：
- **分享页爬虫（网关队列消费者，2026-09-04 起）**：`v2bndInputPwd`、`v2bndLoadShare`(百度)、`v2aliLoadShare`(阿里)、
  `v2quarkLoadShare`(夸克)、`v2xlLoadShare`(迅雷)。旧的 `share`/`share_pwd`/`ad_share`/`quark_share`/`xunlei_share` 已删除。
- **站点遍历型爬虫**：`bbs_*`（`services/bbs/`，全站翻页而非关键词驱动）：kkpans/dyyjmax/feikuai/fuxipan/kuakes/misoso
- **关键词站点爬虫**：`keyword_*`（`keyword_aipanso`、`keyword_upyunso`、`keyword_funletu`、`keyword_juzi`、`keyword_xuebapan`、
  `keyword_pansearch_me`；`keyword_haisou` 已下线默认不启动），全部消费网关 `keywordSubscribed:<site>` 队列；`keyword_filter` 已删除（去重扇出移到网关）
- **网关**：`gateway`
- **转存下载链路**：`share_download_push_resolve_*`、`share_download_resolve_link`、`share_download_download`
- **网页资源链路**：`webResSearchEngine`、`webResHeadUrl`、`webResDownloadUrl`
- **运维一次性任务**：`devops_*`、`proxy`（`urn`、`file_bot` 已随队列 v2 删除）

> `spider.go` 文件底部注释记录了 2023-04-11 已下线的站点及原因，判断某站点是否还在用先看那里。

## 目录分层

```text
config/        配置加载(config_dev.yaml / config.prod.yaml，支持 OSS_CONFIG_URL 远程配置)
db/            Redis / MySQL / ES 连接
resource/      资源提交到 STORAGE 的封装（baidu.go / magnet.go / big-res.go / res-contract.go）
illuminate/    基础设施：http_requester、keepalive、proxy-client、proxy-pool、queue-task
captcha/       验证码识别
bnd/           百度网盘客户端底层
services/
  gateway/           ★ 网关（唯一有状态服务）
    gateway.go         进程入口：初始化 redis/es/mysql/阿里日志，注册所有 gRPC service
    gw_rpc_server.go   gRPC server 装配
    res_scheduler/     资源与关键词任务调度、账号黑名单、失效清理
    doc_scheduler/     文档站点抓取调度
    download_scheduler/网盘转存/解析/下载调度（含 pan_download/{bnd,alipan,quark}_download、web_res、FC 函数计算）
    gw_contract/       通用队列定义 QueueDefine[T] + GwQueue（对接 gateway_v2 RPC）
    gw_config/         网关自身配置
    spider_dao/        gorm 数据访问（doc/download/res）
    spider_gateway/    旧版 SpiderRpc 实现
    valid/             各网盘链接有效性检测（bnd/alipan/quark/xunlei checker）
    rtc-gateway/       基于 WebRTC/UDP 的内网穿透网关（grpc_proxy、json-rpc、pc、udp-mux、limiter）
  bbs/                            站点遍历型爬虫（全站翻页，非关键词驱动）
    kkpan.com.go                    www.kkpans.com，命令 bbs_kkpans，配置节 services.kkpans
  spider-common/spider_contract/  网盘类型常量、链接正则、爬前钩子
  v2/res_crawler/{bnd,ali,quark,xl}/  网关队列消费者（百度/阿里/夸克/迅雷），网盘客户端仍复用 services/{share,aliyun-drive,quark,xunlei-pan}
  v2/gw_remote_queue/             网关队列客户端适配与辅助（NewResConsumer/NewKeywordConsumer/PushResTask/PushKeywords）
  keyword/, keyword2024/, sp2023/, fuck0fy/  各代关键词站点爬虫
  devops/                         按时间分目录的一次性运维脚本（2408/2409/2511/26/…）
scripts/       ai.sh、clear_oss.sh、export.sh、download/
_note/         线上配置源、SQL、临时笔记（config/spider.prod.yaml 是**全部进程共用**的唯一配置源, 2026-09-09 起）
```

## 队列约定（2026-09-04 队列 v2 之后）

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

## 编译状态

`go build ./...` 全部通过（2026-09-02）。此前两处存量编译错误已修复：

1. `bnd_resolver/bnd_resolver_check.go`
   - `startCheckFid` 的形参类型写成了不存在的 `gw_contract.GwQueue[spider_task.BndTransferTask]`，
     改为与结构体字段一致的 `QueueTransfer2Tmp`（即 `GwQueue[spider_task.BndTransfer2TmpTask]`）。
   - `PushTask` 收的是 `gw_contract.PushTaskParam[T]` 包装结构而不是裸 payload 指针，
     已改为 `PushTaskParam{Id: task.Id, Priority: ..., MaxRetry: ..., Payload: &BndTransfer2TmpTask{...}}`；
     转存任务与检查任务一一对应，复用同一个 `task.Id` 让队列侧天然去重。
2. `services/devops/devops_res_reindex/devops_res_reindex.go`（未挂到 `spider.go` 命令表，是半成品运维脚本）
   - `search_export.GetEsClient` 不存在 → 改用 `devops_utils.InitProdEs()`（`tools/search_export/search_export.go:297` 的同款用法）
   - `SetGetSaveDir` 回调空实现缺 return → 补为 `path.Join(localRoot, scene, resourceType)`
   - 导出根目录只在本地环境定义过，非本地环境 `ExportBndLinks()` 直接 panic 退出
     （用户 2026-09-02 决定），避免把导出文件写到文件系统根目录

> 遗留：`bnd_resolver_check.go:160` 有一条 **既有**的 `go vet` 告警
> —— `resource.SaveBaiduResource(res)` 按值传递 `storage.Resource`（protobuf 消息含 `sync.Mutex`）。
> 这是 `SaveBaiduResource` 的全局签名问题，`bnd_load_share.go` 等处同样存在，未在本次改动范围内。

## 关键类型速查（`bnd_resolver` 包）

`bnd_resolver.go` 顶部用类型别名把泛型队列收敛成短名，写代码时优先用这些别名：
`TaskCheckFid`/`QueueCheckFid`、`TaskTransfer2Tmp`/`QueueTransfer2Tmp`、
`TaskCollect`/`QueueCollect`、`TaskBatchResolve`/`QueueBatchResolve`。

`GwQueue[T].PushTask` 的入参是 `gw_contract.PushTaskParam[T]{Id, Priority, MaxRetry, WorkerName, Payload *T}`
（**值**传递，不是指针），参考实现 `services/gateway/download_scheduler/web_res/head_url.go:153`。

## 写新爬虫时的可复用要点

- 链接统一走 `spider_common.NewResLinkCommitter().CommitResLink()`，它把链接推到网关 `resourcePreCheck` 队列
  （taskKey `<type>:<id>`），由网关识别类型、去重、分发。
  **`TypeFromUrl` 返回空串就必须提前跳过**，否则会刷 `unsupported type` 错误日志。
  爬虫进程需要能连到 `config.SpiderGateway`（本地 dev 指向 127.0.0.1:8082，要先起本地 gateway）。
- `ResLinkCommitter` 是接口，测试可注入假实现；redis 键前缀建议做成结构体字段。
  详见 `agent-memory/lessons/success-爬虫联网集成测试.md`。
- 配置：在 `config/config.go` 的 `Services` 结构体加一个字段即可。
  `gopkg.in/yaml.v2` 支持 `720h`/`30m`/`300ms` → `time.Duration`，且显式 `yaml:"camelCase"` tag 精确匹配。
  **线上非 gateway 服务的 `config.yaml` 不由 `deploy.sh` 分发**，所以新配置节要给全套内置缺省值，
  开关字段用 `*bool`（nil 视为开启），避免线上配置未同步时服务静默空跑。
- 存活上报：`keepalive.New("<site>", time.Hour)`，**只在 `CommitResLink` 返回 nil 时调用**，
  轮次成功/抓到条目都不算（站点常年返回同一批老链接时会全部 dup，那不是在正常工作）。
  详见 `agent-memory/lessons/success-爬虫保活语义.md`。异常告警用 `logger.Notify`。
- 本地调试：SPIDER 仓库有 `.vscode/launch.json`（2026-09-02 新建），
  每个子命令一个 configuration（`type: go`、`program: ${workspaceFolder}`、`args: ["<cmd>"]`、
  `env.enfi_spider_conf` 指到 `config_dev.yaml`）。加新子命令时复制一份改 name 与 args 即可。

## 配置怎么读（2026-09-09 起）

- **没有 `config.Config` 全局变量**。每个进程角色读自己的包：`config/gateway.Get()`、`config/crawler.Get()`、
  `proxyprov` / `lifecyclechecker` / `doccrawler` / `devops` / `downloader`；根结构体只组合该进程用得到的节，
  网关拿不到 `spider_gateway`，爬虫拿不到 `services.gateway`。进程内只允许一种角色。
- 多角色共用的库包（`db`、`resource`、`services/gateway/valid`…）只能用 `config/common.Get()` 读公共段，
  角色相关的值由调用方传入（`proxy_provider.OnProxyWith(sub, cb)`、`config.NewSpiderGwConn(addr, svc)`）。
- 构建 tag：`scripts/check_config_isolation.sh` 分别 `-tags gateway_only` / `-tags crawler_only` 编 main，
  网关代码 import 了爬虫配置会直接编译失败。默认构建仍是全功能单二进制。
- `./spider config_show <角色>` 看该角色实际读到的配置（打码）。
- 决策与原因：`decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`。
