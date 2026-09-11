---
title: STORAGE 存储服务结构
type: knowledge
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-02T10:50:00+08:00
priority: high
keywords: [STORAGE, enfi-resource-storage, 入库, Elasticsearch, 索引, save-worker, version]
summary: enfi-resource-storage 的三个子命令、写入流程、ES 索引名与幂等策略
load: on-demand
related:
  - agent-memory/knowledge/architecture-系统总览.md
  - agent-memory/knowledge/api-rpc契约.md
---

# STORAGE（`1s/enfi-resource-storage`，module `enfi-resource-storage`）

## 入口与进程模型

`storage.go`，三个子命令：

| 命令 | 作用 |
|---|---|
| `gateway` | gRPC 服务（`:8081`），实现 `storage.StorageRpc`；收到请求只做校验和入 Redis 队列，立即返回 |
| `worker` | 并发跑 4 个 `queue-task` 服务：resource / valid / useraction / magnet 的 ES 写入 |
| `reporter` | 邮件报告（`email-reporter`，cron 配置 `services.save_worker.cron_config`） |

日志写到 `<cmd>.log`（工作目录下可见 `gateway.log`、`worker.log`、`elastic.log`）。

## 目录

```text
config/    config.go（yaml 配置结构）、log.go
db/        db.go（Redis/ES）、mysqldb.go
services/
  gateway/       gRPC 实现 + 大资源流式写入 + getResById
  save-worker/   es.go / mysql.go / mongo.go / resource.go / valid.go / magnet.go
                 useraction.go / save-torrent.go
  email-reporter/
```

## ES 索引（来自 `config_dev.yaml` → `services.storage`）

| 配置项 | 索引名 |
|---|---|
| `es_resource_index` | `resource` |
| `es_magnet_index` | `enfi_magnet_v3` |
| `es_baidu_user_index` | `baidu_users` |
| `es_resource_useraction_indexes` | `resource_search`、`resource_download` |
| `es_resource_valid_index` | dev 为空，线上配置里设置 |

MongoDB：库 `enfiresource`，集合 `baidu_user`、`share_files`。
MySQL：库 `enfi_resource_storagelayer`（`savemysql: false` 时不写）。

## 写入幂等与去重（`services/save-worker/es.go`）

1. 取本批资源的 `version` 列表，用 `terms` 查询 ES 已存在的文档。
2. 已存在（version 相同）→ 从旧文档继承 `Likes / Views / Downloads / Ctime`，并从待写 map 中**剔除**，不重复写。
3. 剩余的走 `Bulk` + `NewBulkIndexRequest().Id(res.GetId())`，type `_doc`。

`id` 与 `version` 由**爬虫侧**计算（SPIDER `resource/baidu.go` `SaveBaiduResource`）：
- `id = md5(url)`
- `version = md5(按 path 排序后 拼接每个文件的 originMd5+filename+fid)`
- 同时把 `filename` 复制到 `filename_ik_completion` / `filename_py_completion` 供 ES 补全用

## 大资源流式写入

`UpsertBigResource(stream UpsertBigResourceMsg) returns (UpsertBigResourceResponse)`：
- 第一条消息发 `Resource`（不含 filelist），后续发 `FileListItemBatch{offset, last, files}`
- 服务端用 painless 脚本 `ctx._source.filelist.addAll(params.files)` 追加，并更新 `version`
- 响应 `canceled` + `cancelReason`，服务端可中途要求客户端停止（如 version 未变）
