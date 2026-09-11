---
title: 系统架构与数据链路总览
type: knowledge
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-02T10:50:00+08:00
priority: critical
keywords: [架构, 数据链路, 网关, 队列, Elasticsearch, gRPC, 端口]
summary: 从爬取到入库到检索的完整链路、各服务端口与中间件分工
load: on-demand
related:
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/knowledge/architecture-storage.md
  - agent-memory/knowledge/architecture-api.md
  - agent-memory/knowledge/api-rpc契约.md
---

# 系统架构与数据链路总览

## 主链路

```text
[关键词爬虫 keyword_*]           [分享页爬虫 *_share / v2bnd*]
        │ 产出关键词/分享链接              │ 产出资源详情(文件清单)
        ↓                                  ↓
   SPIDER gateway (:8082)  ← Redis 队列 + MySQL + ES(调度侧)
   ├─ res_scheduler      资源/关键词任务队列、账号黑名单、爬前钩子
   ├─ doc_scheduler      文档站点抓取调度
   ├─ download_scheduler 网盘转存/解析/下载到 OSS 的调度
   ├─ gateway_v2         通用命名空间队列（PushTask/PopTask/Keepalive/Finish）
   └─ spider_gateway     旧版入口(CommitResource/CommitKeyword/CommitBitTorrent)
        │
        │ resource.SaveBaiduResource() → gRPC storage.UpsertResource
        ↓
   STORAGE gateway (:8081)
        │ 入 Redis 队列(queue-task)，立即返回
        ↓
   STORAGE worker（独立进程 `storage worker`）
        ├─ resource  → ES index `resource`
        ├─ magnet    → ES index `enfi_magnet_v3`
        ├─ valid     → ES 有效性索引
        └─ useraction→ ES `resource_search` / `resource_download`
        ↓
   Elasticsearch
        ↑
   API (gin, HTTP) ── /api/v2/search、/api/v2/detail、/api/enfi/* …
```

## 关键设计点

- **两级网关**：SPIDER gateway 管"爬什么/谁来爬"，STORAGE gateway 管"怎么落库"。爬虫节点只持有 gRPC 客户端，不直连 Redis/ES/DB。
- **队列即调度**：任务队列在 Redis，通过 gRPC 暴露为 `PopTask/Keepalive/TaskDone` 三段式，支持超时重投、seq 校验（`ErrSeqIdNotMatch` → 任务已被取消）。
- **写入幂等**：资源 `id = md5(url)`；`version = md5(排序后的文件列表 originMd5+filename+fid)`。STORAGE 用 `version` 判重，`version` 未变则跳过写入，仅继承 likes/views/downloads/ctime。
- **大资源流式写入**：`UpsertBigResource` 是 client-streaming，先发 `Resource` 再分批发 `FileListItemBatch`，服务端用 ES painless 脚本 `filelist.addAll` 追加。
- **爬前钩子**：`CheckResourceBeforeCrawl` —— 爬虫在真正抓取前把 `Resource` 发给 gateway，gateway 按 `网盘类型:账号Id` 查分享账号黑名单，命中则返回 `stopCrawl`，爬虫侧包装为**永久失败**（`app_error.MarkPermanentError`）不再重试。实现见 `services/spider-common/spider_contract/spider_contract.go` 与 `services/gateway/res_scheduler/res_scheduler_service.go`。

## 服务端口（本地 dev 配置）

| 服务 | 端口 | 配置项 |
|---|---|---|
| STORAGE gateway | `:8081` | STORAGE `config*.yaml` → `services.gateway.listen_addr` |
| SPIDER gateway | `:8082` | SPIDER `config*.yaml` → `services.gateway.listen_addr` |
| API HTTP | 配置项 `server.host/port` | API `config*.yaml` |
| API Prometheus | `:8089` `/api/metrics` | 硬编码在 `api-starter.go` |

## 中间件

- **Redis**：任务队列、去重（`keywordDealAt:<kw>` 8h SETNX）、分布式锁（`dlock`，前缀 `resScheduler`）、黑名单哈希同步（30s 拉取）
- **Elasticsearch**：资源主库与检索
- **MySQL**：SPIDER gateway 侧调度元数据（gorm）、STORAGE 可选落库（`savemysql`）
- **MongoDB**：STORAGE 侧 `baidu_user` / `share_files` 集合
- **阿里云 OSS / AWS S3**：种子文件、下载文件产物
- **阿里云 SLS 日志**：`logger.InitAliLog`，project `resource-backend`
