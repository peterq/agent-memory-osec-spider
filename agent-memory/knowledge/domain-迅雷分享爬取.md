---
title: 迅雷分享爬取（xlLoadShare）：客户端行为、接口、失败分类与探针
type: knowledge
status: active
created_at: 2026-09-15T06:46:00+08:00
updated_at: 2026-09-15T06:46:00+08:00
priority: high
keywords: [xlLoadShare, 迅雷, xunleipan, 失败率, 顶层文件, 空文件夹, share status, captcha token, xl_share_probe, v2xlLoadShare]
questions:
  - xlLoadShare 队列为什么失败率高，失败都是什么原因
  - 怎么不经爬虫直接查一个迅雷分享的顶层结构和文件夹内容
  - 迅雷分享状态码该重试还是判失效
summary: xlLoadShare 失败率排查结论：丢顶层文件 75%、空文件夹 25%、状态码全重试放大；接口/头部/探针用法与修复建议
load: on-demand
related:
  - agent-memory/knowledge/domain-网盘有效性检测.md   # 网关侧迅雷状态码表 invalidXunleiShareLinkCodes
  - agent-memory/knowledge/architecture-spider-队列约定.md
  - agent-memory/sessions/2026/2026-09-15-xlLoadShare失败率排查.md
---

# 迅雷分享爬取（xlLoadShare）

## 1. 链路与进程

- 网关 `resourcePreCheck` → 队列 `xlLoadShare` → `./spider v2xlLoadShare`（**osec-resngix + osec-jenkins 各 1 进程，20 协程**，2026-09-14 重启）。
- 代码：消费者 `services/v2/res_crawler/xl/xl_load_share.go`；客户端 `services/xunlei-pan/xl-client.go`（`LoadShareById` → `getShareInfoAndFillResource` + `listFolderLoop`/`listDir`）；落盘 `resource/big-res.go`（`TempFileHandlerForBatchFiles` 懒建目录、`SaveBigResource` 读 `./temp/<日期>/xl-share-<id>`）。
- 业务日志**不在** `v2xlLoadShare.log`（那里只有配置加载），在 `sudo docker logs spider-v2xlLoadShare`；成功 `onSuccess.submitResult`，失败 `task fail`（`reason`、`Retry`）。

## 2. 接口与头部 [事实]

- 验证码 token：`POST https://xluser-ssl.xunlei.com/v1/shield/captcha/init`，client_id/device_id/captcha_sign 都是代码里的常量（`newCommon`、`refreshCaptchaToken`）。token 按 device 绑定，**多个并发请求共用一个 token 会很快 `captcha_invalid`**，探针要每次单独取。
- 分享信息：`GET https://api-pan.xunlei.com/drive/v1/share?share_id=&pass_code=&limit=100`，头 `X-Device-Id/X-Client-Id/X-Client-Version/X-Captcha-Token`；返回 `share_status`、`files[]`（顶层条目，`kind=drive#file|drive#folder`）、`pass_code_token`。
- 目录详情：`GET .../drive/v1/share/detail?share_id=&parent_id=<folder id>&pass_code_token=&limit=100&page_token=`。pass_code_token 含 `+ / =`，经 `:9527` 调试代理转发时要**双重 URL 编码**（代理先解一层）。

## 3. 2026-09-15 失败分类 [事实]（osec-jenkins 近 48h，任务级去重）

| 类别 | 不同分享数 | 说明 |
|---|---|---|
| 成功 | 415 | 成功样本 38/38 顶层是文件夹 |
| "no such file or directory"（无临时文件） | 186 | 其中 **133 顶层只有文件**、**43 文件夹内容为空**（详情 status OK、0 文件）、余 10 为代理抖动未分类 |
| 分享状态码错误 | 82 | PASS_CODE_ERROR 50、SENSITIVE_RESOURCE 29、DELETED 17、PASS_CODE_EMPTY 7、400/403 13（事件数） |

事件级失败 ≈ 50%（411 失败 vs 416 成功）：因为上述全部被当临时错误由网关重试 3 次（Retry 1/2/3 各占 1/3），一个坏分享贡献 3~4 次失败。

## 4. 根因 [事实]

1. **客户端丢顶层文件**：`LoadShareById` 只把 `r.FileList` 里 `Isdir==1` 的顶层条目放进 `folderQueue`，顶层文件既不进 `task.files` 也不计入 `FileCount`；分享顶层是单个 mp4 时 handleBatchFiles 从未被调用 → 临时目录不存在 → `SaveBigResource` 报 list dir error。混合分享（顶层文件+文件夹）会**静默漏掉顶层文件**。对照夸克 `services/quark/quark-client.go` 会先把全部顶层条目 append 进 `fileItemSlice`。该缺陷在队列 v2 之前的旧 `load-xl-share-service.go` 即存在（4b15c9c 只改了导出名）。
2. **空文件夹分享**：分享状态 OK、文件夹详情 0 文件（内容已被清理，来源多为 feikuai.tv），同样落到"无临时文件"分支并被重试。
3. **状态码全当临时错误**：消费者只把 `ShareLink.Cancelled/Forbidden` 当永久失效上报 SubmitValid；`DELETED/SENSITIVE_RESOURCE`（网关 `invalidXunleiShareLinkCodes` 已判失效）、`PASS_CODE_ERROR/PASS_CODE_EMPTY`（提取码错/缺）都返回普通 error → 重试 3 次且不上报。

## 5. 修复建议 [推断，待用户拍板]

- 客户端：顶层 `drive#file` 先 append 进 `task.files`、累加 `Size/FileCount`（照夸克实现）；无文件夹时直接走 handleBatch 的 last batch。
- 消费者：遍历完 `FileCount==0` → 永久失败并按空分享处理（是否 `SubmitValid Valid=0` 待确认，见 open-questions）；`DELETED/SENSITIVE_RESOURCE/PASS_CODE_*` 走 `MarkPermanentError`，前两者同时 SubmitValid 失效，与网关状态码表对齐（改判定两套要一起看 → `domain-网盘有效性检测.md`）。
- 修复后历史失败的顶层文件分享需重投（去重键 `resDealAt` 6h 后自然可重投；批量重投走网关 `CommitResource`）。

## 6. 探针 [事实]

`scripts/xl_share_probe.sh <host> <shareId> [pwd]`（本仓库）：经该机 `:9527` 调试代理取 token、查分享信息与首个文件夹详情，打印中文摘要；`RAW=1` 输出原始 JSON。无需远端 python。批量分类时按 §2 注意每分享单独取 token、并行 ≤3。
