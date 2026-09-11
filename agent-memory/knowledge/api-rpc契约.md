---
title: gRPC 协议契约（COMMON/rpc）
type: knowledge
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-02T10:50:00+08:00
priority: high
keywords: [proto, gRPC, StorageRpc, SpiderRpc, res_scheduler, doc_scheduler, download_scheduler, gateway_v2, Makefile]
summary: COMMON 仓库中各 proto 服务的方法清单、核心消息结构与代码生成流程
load: on-demand
related:
  - agent-memory/knowledge/architecture-系统总览.md
  - agent-memory/procedures/workflow-本地构建与验证.md
---

# gRPC 协议契约（`enfi-resource-common/rpc/`）

> **改协议的唯一入口是本仓库**。改完 `.proto` 后必须重新生成，再同步下游。

## 代码生成

仓库根 `Makefile`：
```bash
make spider    # protoc rpc/spider/rpc.proto ... + go run cmd/proto/replace-json.go
make storage   # 同上，针对 rpc/storage/rpc.proto
```
生成后会跑 `cmd/proto/replace-json.go` 做后处理（去掉 `omitempty`、按 `json_name` 修正 tag），
因为 ES 文档字段名依赖精确的 json tag（如 `createtime`、`originmd5`、`filelist`、`server_ctime`）。

> 注意：Makefile 里的路径 `rpc/spider/rpc.proto` 与实际文件名 `rpc/spider/spider-gw.proto` 不一致，
> 新增 proto（`gateway_v2` / `res_scheduler` / `doc_scheduler` / `download_scheduler` / `spider_task`）也没进 Makefile，
> 这些目前需要手工执行 protoc。**执行前先确认命令，别盲跑 make。**

## `rpc/storage` —— `service StorageRpc`（STORAGE 实现，SPIDER 调用）

| 方法 | 说明 |
|---|---|
| `UpsertResource(BatchResource)` | 主入库接口 |
| `UpsertMagnet(BatchResource)` | 磁力资源入库 |
| `UpsertResourceValid(BatchResourceValid)` | 有效性状态入库 |
| `UpsertBigResource(stream)` | 大资源流式写入（Resource + 分批 FileListItemBatch） |
| `GetResourceById(id)` | 按 id 读（排除 filelist） |
| `LinkExpired(StringMessage)` | 标记链接失效 |
| `CommitUserAction(UserAction)` | 用户行为（搜索/下载）埋点 |
| `Pong(Ping)` | 健康探测 |

核心消息：
- `Resource`：ES 主文档模型，39 个字段。关键：`id`(md5(url))、`version`(文件清单指纹)、`md5`/`originmd5`、`filelist`、`valid`、`type`(网盘类型)、`user`(分享账号)、`client`(爬虫节点)、`meta map<string,string>`、`refer`、`tag_str`、`likes/dislikes/views/downloads`、`filename_ik_completion`/`filename_py_completion`(补全)、`torrent_info_bytes`
- `FileListItem`：`category/isdir/size/path/filename/ext/server_ctime/md5/originmd5/fid/parent`
- `ResourceDto` / `FileListItemDto`：对外 DTO，比 `Resource` 少内部字段，多了 `admin_keyword`、`desc`、`file_count`、`dir_count`、`crc`、`join{parent,name}`
  > 近期演进（git log）：`crc` 字段 → `join` 字段，逐步加在 DTO 上。

## `rpc/spider` —— `service SpiderRpc`（旧版网关入口）

`CommitBaiduShare`、`CommitKeyword`、`CommitBitTorrent`、`CommitResource`、`CommitResource2`、
`XunleiPanCaptchaTokenHeader`、`SetClientName`、`GetDefaultClientName`、`Pong`。

`ResourceToCommit{type,url,pwd,client,error,meta,referer}` 是爬虫上报的最小单元。

## `rpc/spider/res_scheduler_rpc` —— `ResSchedulerRpc`（资源/关键词调度）

- 任务三段式：`PopQueuedTask` / `TaskKeepalive` / `TaskDone`；投递 `PushQueuedTasks`
- **`CheckResourceBeforeCrawl(Resource) → {stopCrawl, reason}`**：爬前钩子，按 `<网盘类型>:<账号Id>` 查黑名单
- 黑名单运维接口：`AdminHashKeys` / `AdminHashAdd` / `AdminHashRemove` / `AdminHashGetAll`
  （目前唯一的 key：`resScheduler:shareScrawlAccBlacklist`，value 为拉黑原因）
- `GetCallerInfo`、`XunleiPanCaptchaTokenHeader`
- 队列名常量在 `res_rpc.go`：`resourcePreCheck` / `bndInputPwd` / `bndLoadShare`，
  关键词队列 `KeywordSubscribedQueueName(site)` → `keywordSubscribed:<site>`

## `rpc/spider/doc_scheduler_rpc` —— `DocSchedulerRpc`（文档站点抓取）

`QueryDocPagination`、`SubmitDoc`、`SetDocNextCrawlAt`、`SetDocMemo`、`SetDocValid`、
`GetTaskBatch`、`GetQueuedUrls`、`PopTask`、`TaskKeepalive`、`TaskDone`、`GetQueueLength`、
`DeleteWaiting`、`SetTaskPriority`

## `rpc/spider/download_scheduler_rpc` —— `DownloadSchedulerRpc`（最大的一个，30+ 方法）

三条线：
1. **网盘账号池**：`PopPanAccount`/`KeepalivePanAccount`/`AddAliPanAccount`/`AddBndAccount`/`SetEnablePanAccount`/`DeletePanAccount`/`SetPanAccountMetadata`/`MarkPanAccountError`/`ListPanAccount`/`GetPanAccount`
2. **链接解析与下载**：`PushResolveLinkTaskV2`/`PopResolveLinkTaskV2`/`KeepaliveResolveLinkTask`/`ReportResolveLinkTask`/`PopDownloadFileTask`/`KeepaliveDownloadFileTask`/`CreateDownloadGroup`/`ListDownloadGroup`/`GetDownloadGroupInfo`/`QueryIsEtagDownloaded`
3. **分享文件与网页资源**：`SaveShareFile`/`QueryShareFileExist`/`QueryShareFilePagination`/`CreateWebResDownloadGroup`/`QueryWebResUrlExist`/`SaveWebResUrl`/`SaveWebResOss`/`UpdateWebResUrl`

## `rpc/spider/gateway_v2` —— `SpiderGwV2Rpc`（通用队列抽象，新代码首选）

`CreateQueue`/`ListQueue`/`QueueLength`/`ListTask`/`PushTask`/`PushTaskBatch`/`PopTask`/
`KeepaliveTask`/`UpdateTaskMetadata`/`FinishTask`

配套 SPIDER 侧封装：`services/gateway/gw_contract/gw_contract.go` 的 `QueueDefine[T]` + `GwQueue[T]`。

## `rpc/spider/spider_task` —— 任务 payload 类型

`TaskGroup`、`BndCheckShareFidTask`、`BndTransfer2TmpTask`、`BndCollectTask`、`BndBatchResolveTask`、
`WebResSearchTask`、`WebResUrlDownloadTask`

## `rpc/common_message` —— 通用类型

`Empty`(单例 `common_message.E`)、`StringMessage`、`BoolMessage`、`BytesMessage`、`Int64Message`、
`MapStringString`、`UnixTimeStamp`、`CodedError`、`JsonValue`/`JsonObject`/`JsonArray`（+ `JsonObjectMessageToGo` 转换）

## `rpc/illuminate/multi-server`

自定义 gRPC name resolver，scheme 用于 `grpc.Dial("<scheme>:///host1,host2")`，
配合 `loadBalancingPolicy: round_robin` 与 `grpc_retry`（最多 3 次，`codes.Unavailable`）。
客户端封装：`rpc/storage/client/storage-client.go`、`rpc/spider/client/spider-client.go`
（发送消息上限 100MB）。
