---
title: 迅雷分享爬取（xlLoadShare）：客户端行为、接口、失败分类与探针
type: knowledge
status: active
created_at: 2026-09-15T06:46:00+08:00
updated_at: 2026-09-15T15:50:00+08:00
priority: high
keywords: [xlLoadShare, 迅雷, xunleipan, 失败率, 顶层文件, 空文件夹, share_status, ShareStatusError, submitInvalidDryRun, xl-fail-export, xl_share_probe, v2xlLoadShare]
questions:
  - xlLoadShare 失败率高是什么原因
  - 怎么直接查一个迅雷分享的结构
  - 迅雷失效上报 dry run 开关在哪
summary: xlLoadShare 失败率修复(09-15 已上线)：顶层文件入批次、状态码按共用码表判定、空分享永久失败；失效上报仍 dry run；接口/探针/导出重投工具用法
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

## 4. 根因 [事实]（修复前）

1. **客户端丢顶层文件**：`LoadShareById` 只把顶层 `Isdir==1` 条目入 `folderQueue`，顶层文件既不进 `task.files` 也不计 `FileCount`；顶层单文件分享从不触发 handleBatchFiles → 临时目录不存在 → `SaveBigResource` 报 list dir error；混合分享静默漏顶层文件。旧 `load-xl-share-service.go` 即如此。
2. **空文件夹分享**：状态 OK、文件夹详情 0 文件（多为 feikuai.tv 来源），同样落到"无临时文件"并重试。
3. **状态码全当临时错误**：消费者只认 `ShareLink.Cancelled/Forbidden` 文案（迅雷根本不返回），`DELETED/SENSITIVE_RESOURCE/PASS_CODE_*` 都重试 3 次且不上报。

## 5. 修复 [事实]（SPIDER `3270e10`，09-15 jenkins 08:51 / resngix 08:58 / restest 09:51 三机全部上线（restest ssh 反复超时，scp 重试 20 次才成功））

- 客户端：顶层条目全部进批次并累加 `Size/FileCount`（照夸克），`r.FileList=nil`；非 OK 状态返回类型化 `*xunlei_pan.ShareStatusError{Status,Text}`。
- 码表唯一正本 `services/xunlei-pan/share_status.go`：`InvalidShareStatusCodes`(SENSITIVE_RESOURCE/NOT_FOUND/EXPIRED/DELETED)、`ValidShareStatusCodes`(OK/PASS_CODE_EMPTY)、`PassCodeShareStatusCodes`；网关 `xunlei_checker.go` 改引用同一张表（两套判定从此同源）。
- 消费者 `xl_load_share.go`：`errors.As` 取码 → 失效码 `submitInvalid`+`MarkPermanentError`；提取码错/缺永久失败不上报；未知码仍重试。遍历完 `FileCount==0` → `empty-share` 永久失败、**不上报失效**（链接可打开，空内容≠失效，失效会不可逆删 ES）。
- **失效上报处于 dry run**：`const submitInvalidDryRun = true`，只打 `submit-invalid-dry-run` 日志（含 status/pwd）。按 `procedures/checklist-不可逆操作上线.md`：收集清单 → `scripts/xl_share_probe.sh` 独立复核 → 用户拍板后改 false 重新部署。首例 `VP0Q3NoLKSSXkLlaVbg6nEk9A1` SENSITIVE_RESOURCE 探针复核一致。
- 验证：联网测试 `XL_IT=1 LOCAL_CONFIG_PATH=<本地yaml> go test ./services/xunlei-pan/ -run TestLiveLoadShareById`（顶层文件/文件夹回归/空文件夹/DELETED/PASS_CODE_ERROR 5 例全过，走本地代理池）。重投 288 条后 5 分钟：入库 173、empty-share 78、expire 1、503 重试 1，**原先 100% 失败的顶层文件分享已全部入库**。

## 6. 历史失败重投 [事实]

消费者容器重建后 docker logs 清空，只能从 SLS 找：`go run ./tools/xl-fail-export -addr 127.0.0.1:18082 -days 7 -out _note/xl-refix/no-temp-file.tsv`（经 res2 网关隧道调 `queue_admin.SearchLogs`：`finishQueuedTask` 拿 taskKey，`preCheck.handle` 全文匹配 `"xunleipan:<id>"` 拿 pwd；`queueName`/`link_key` 不是 SLS 索引键，只能全文匹配）→ `lc-recrawl -file … -rate 10 -client xl-refix-2609` 投递。09-15 09:09 投 288/288（7 天窗口，pwd 全齐）。预检去重 `resDealAt` TTL 6h：6h 内刚失败的会被判 repeat，需要时 6h 后再导一次。

## 7. 探针 [事实]

`scripts/xl_share_probe.sh <host> <shareId> [pwd]`（本仓库）：经该机 `:9527` 调试代理取 token、查分享信息与首个文件夹详情，打印中文摘要；`RAW=1` 输出原始 JSON。无需远端 python。批量分类时按 §2 注意每分享单独取 token、并行 ≤3。远端偶发 `Traceback ... 'NoneType'` 是该分享响应非 JSON（代理抖动），重跑即可。
