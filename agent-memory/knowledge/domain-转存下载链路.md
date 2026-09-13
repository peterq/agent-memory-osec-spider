---
title: 网盘分享文件转存下载链路（resolve → download → OSS）
type: knowledge
status: active
created_at: 2026-09-13T19:05:00+08:00
updated_at: 2026-09-13T19:05:00+08:00
priority: high
keywords: [转存下载, share_download, resolve_link, download_scheduler, 账号池, refresh token, InvalidParameter.RefreshToken, download2oss, 下载组, 链路体检]
questions:
  - 分享链接里的文件是怎么被转存、解析成下载地址并落到 OSS 的
  - 转存下载链路的进程跑在哪台机器，队列和账号池在 redis 哪些键
  - 怎么检查转存下载链路是否通畅，脚本在哪
  - 为什么 share_download_resolve_link 一直报 InvalidParameter.RefreshToken
  - 下载组进度（解析了多少、下载了多少）在哪张表
summary: SPIDER 下载调度链路的代码结构、redis 键/MySQL 表、阿里/百度解析方式、三条下载路径，以及 2026-09-13 体检结论：链路空转，阿里 3 个账号 refresh token 全失效、百度 0 可用账号；体检脚本 scripts/dl_chain_health.sh
load: on-demand
related:
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/knowledge/api-rpc契约.md  # DownloadSchedulerRpc 三条线
  - agent-memory/sessions/2026/2026-09-13-转存下载链路体检.md
---

# 网盘分享文件转存下载链路

按批次（下载组）把分享链接里的文件转存到自有网盘账号、解析出直链、再下载并上传到 OSS，作为取证产物。
与主链路（爬取→ES）无关，任务来源是离线导出的清单文件，**不是常驻的自动流水线**。

## 1. 三段进程与线上位置（2026-09-13 `deploy.sh ps` [事实]）

| 段 | 命令 | 主机 | 作用 |
|---|---|---|---|
| 投递 | `share_download_push_resolve_ali_250918`（`push_resolve.StartPrefixByFileType`） | osec-resdb | 读清单 → `CreateDownloadGroup` → `PushResolveLinkTaskV2`；队列满则等空闲。2025-09-22 投完 595,448 任务后一直空转（容器 Up 11 个月）|
| 解析 | `share_download_resolve_link`（`resolve_worker.Start`，同时起 ali-share 与 bnd 两个 mgr）| osec-res2 | `PopPanAccount` 占账号 → 每账号 4 并发（bnd 20）`PopResolveLinkTaskV2` → `ResolveShareFileLink` → `ReportResolveLinkTask` |
| 下载 | `share_download_download`（`download_worker.Start`）| osec-res1 | `PopDownloadFileTask` → 下载并上传 OSS → `KeepaliveDownloadFileTask(Finished)` |

代码全在 SPIDER `services/gateway/download_scheduler/`：`push_resolve/`、`resolve_worker/`、`download_worker/`、`pan_download/{alipan_download,bnd_download}`，网关侧实现 `download_scheduler_service.go`（gRPC `DownloadSchedulerRpc`）。

## 2. 状态存储

- **redis db6（`redises.db1`，res1 上容器 `enfi-spider-redis`，无本机 redis-cli，用 `docker exec` 调）**
  - 账号池：`downloadScheduler:account_conf:<ali-share|bnd>`（hash，值含 RefreshToken，**禁止回显**）、`account_error:<type>`（错误标记）、`account_meta:<type>:<id>`
  - 队列（`illuminate/queue-task` Queue2）：`queue:{downloadScheduler:<ali|bnd><Acc|Resolve2|Download>}:<waiting|pending|map>`；zset 空即被 redis 删除，`type`=none 表示 0；score 高 16 位是优先级、低 48 位是入队毫秒（`DecodeScore`）
  - 账号必须在 `<prefix>Acc` 队列里才会被 worker 领用；`SetEnablePanAccount` 负责进出队列，`MarkPanAccountError(Disable=true)` 出队并写 error hash
- **MySQL `prod-osec-spider`**（res1 有 `mysql` 客户端，RDS 内网域名只在生产网可解析）：每个下载组两张表 `download_share_file_<ali|bnd>_<group>`（分享文件清单，唯一键 share_id+fid）与 `download_file_<type>_<group>`（按文件 hash 去重，`saved` 表示已传 OSS）。`GetDownloadGroupInfo` 就是对这两张表 count。表没有时间列，PolarDB `information_schema.tables.update_time` 为 NULL，**看不到最后写入时间**，只能按建表时间找最新组。

## 3. 解析（resolve）做了什么

- **阿里**（`alipan_dl.go GetSharedFileUrl`）：`get_share_token`（走代理）→ `/adrive/v4/batch` 批量 `/file/copy` 把分享文件转存到自有盘临时目录 → 取 `download_url`/`url` 直链，`ExpireTime = now+4h`，附 Referer 头，`Hash = content_hash`。临时目录定期 trash 并清空回收站。账号初始化用 refresh token 换 access token，token 轮换后经 `AddAliPanAccount` 写回 redis。
- **百度**（`bnd_dl_v2.go`）：转存到自有账号 → 取 dlink → 经代理跟随 302 拿快速主机直链。
- **失败处理**：`ErrorAccBlocked/ErrorAccLoggedOut` 或连续 20 次失败（`ErrorAccFailTooMany`）→ `MarkPanAccountError(Disable)` 停用账号；同一 share 连续 20 次失败进 `badShareMap` 跳过。
- **⚠ 坑 [事实 2026-09-13]**：账号 init 阶段的 `InvalidParameter.RefreshToken`（阿里 refresh token 失效）**不在停用分类里**，worker 只记错误、`cancel()`，账号回队列后约 1 分钟又被领用，形成每账号每分钟一条错误的死循环，且不产生任何告警。

## 4. 上报与下载

- `ReportResolveLinkTask`：按 `file hash` 查 `download_file` 去重 → 新文件写两张表并推 `<prefix>Download` 队列；返回 new/duplicate 计数。
- 下载 worker 三条路径（`download_worker.go handleTask`）：OSS 客户端为内网时 `internalNetworkPipe`（把 `cn-beijing-data.aliyundrive.net` 换成 OSS 北京内网域名流式转存，限流时 1 分钟内退到 `downloadByOssMirror`）；否则调函数计算 `resource_download_fc/download2oss`。单文件上限 10 GB，`.txt` 200 MB。

## 5. 体检方法

`scripts/dl_chain_health.sh`（记忆仓库；`SINCE=6h` 可改窗口，`--no-mysql` 跳过库查询；口令从 SPIDER `_note/config/spider.prod.yaml` 读，不回显）依次输出：三个容器状态与日志统计 → 账号池/错误标记/六条队列长度与最早入队时间 → 最新下载组两张表的计数。
判读：解析容器 `refreshToken失效` 行数 ≈ 错误行数 → 账号池全废；`Resolve2 waiting` 有积压但 `Acc` 队列为 0 → 无账号可用；下载容器全是 `no available download task` → 上游没产出。

## 6. 2026-09-13 体检结论 [事实]

- 链路**空转、不可用**：阿里 7 个账号中只有 3 个在队列里，且 3 个的 refresh token 全部失效（自 09-10 18:42 容器重启起 72 h 内 11,050 次错误、0 成功）；其余 4 个 2025-03/2025-09 已标记 403/NotFound 错误。百度 11 个账号 0 个在队列（7 个 2024-12~2025-02 被标错误）。
- 队列：阿里解析/下载队列为空；百度解析队列积压 3,836（2025-02-09 入队的 literature 批次遗留，无账号消费，map 里 7,672 条）。
- 最新下载组 `ali_250918_list`（2025-09-19 建）：share_file 16,230,283，download_file 全部 saved（1,677,799 个，≈35.5 TB），无未下载记录 → 该批次 2025-09 已完成，之后再无新批次。
- 09-13 18:31 网关重启造成下载 worker 100 条 `connection refused`，已自愈，非故障。
- 恢复需要：给阿里账号重新获取 refresh token（`AddAliPanAccount` 或 `resolve_worker/push_acc_test.go` 的投递方式）并 `SetEnablePanAccount`；百度同理补账号。是否恢复待用户决定（`current/open-questions.md`）。
