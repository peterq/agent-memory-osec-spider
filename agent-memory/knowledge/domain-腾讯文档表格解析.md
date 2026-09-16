---
title: 领域知识：腾讯文档(docs.qq.com)表格的取数接口与两种数据格式
type: knowledge
status: active
created_at: 2026-09-16T08:55:00+08:00
updated_at: 2026-09-16T11:20:00+08:00
priority: high
keywords: [腾讯文档, docs.qq.com, opendoc, dop-api, protobuf, dver, 文档爬虫, qqSheet, kdocCloud]
questions:
  - 腾讯文档表格的单元格数据从哪个接口拿、要不要登录
  - 腾讯文档 opendoc 返回的 protobuf 区块怎么解
  - 为什么腾讯文档有的返回 block_datas 有的返回 JSON op 数组
  - 腾讯文档分块拉取越界时会怎样
summary: 2026-09-16 实测：公开表格匿名可访问；同源 GET dop-api/opendoc（需页面 Cookie，t/xsrf 非必需）返回 JSONP；数据有两种格式——dver 3.0.0 的 base64+zlib+protobuf 区块（字段路径已摸清）与 dver 2.x 的 JSON op 数组（t=3 op 行优先平铺）；分块循环要用 maxRow 终止，越界会退回第一块
valid_until: 2026-12-31
load: on-demand
related:
  - agent-memory/agent-tasks/2026-09-16-qqdoc-sheet/00-shared.md  # 任务简报, 含夹具与 Python 原型
  - agent-memory/knowledge/architecture-fc-chrome文档爬虫上云.md
---

# 腾讯文档表格解析（供云端脚本 NC-JS `apps/doc-cloud-spider/src/sites/qqdoc.ts` 使用；2026-09-16 前在个人仓库 userscripts）

> 详细字段表、夹具与已验证的 Python 原型在 `agent-tasks/2026-09-16-qqdoc-sheet/`（`00-shared.md` §4、`ref/`、`fixtures/`），本文只记结论。接口为第三方未公开接口，结论有保质期。

## 1. 访问与鉴权 [事实 2026-09-16]
- `https://docs.qq.com/sheet/<docId>[?tab=<sheetId>]` 公开分享匿名 200，**无 SSO 重定向**，`#taskNonce=` 不丢（与金山不同）。
- 取数接口 `GET /dop-api/opendoc?id=<docId>&tab=<sheetId>&outformat=1&normal=1&wb=1&nowb=0&noEscape=1&…&callback=clientVarsCallback`（JSONP）：**无 Cookie 401**；页面下发的 `hashkey/TOK/traceid` Cookie 带上即 200。页面内同源 fetch 天然满足；Node/curl 侧先 GET 页面拿 Cookie **并把 `Referer` 设成文档页 URL**（无 Referer 也 401：`trpc-error-msg: this url does not allow access from`；浏览器同源 fetch 自动带）。`t=`/`xsrf=` 可省。本机到 docs.qq.com 偶发连接超时，批量验证脚本要带重试。
- 无效/已删文档：`padType: "blankpage"`（`retcode` 200061 或 0，`errmsg` 形如 `blankpage type:2`）→ 永久失败。非表格文档 `padType !== 'sheet'` → 永久失败。

## 2. 公共字段 [事实]
`clientVars.title`、`clientVars.lastModifyTime`（毫秒）、`collab_client_vars.header[0].d[]`（全部 sheet：`id/name/hidden/type`，不带 tab 也返回）、`collab_client_vars.maxRow`（当前 sheet 行上限，两种格式都有）、`padSubId`（本响应的 sheet id）。

## 3. 格式 A：`dver 3.0.0`（`text[0]` 是对象，含 `block_datas`）[事实]
- `initialAttributedText.text[0].block_datas[i].related_sheet` = base64 → zlib（头 `78 01`）→ protobuf。
- 结构：`root.f1` → 重复 `f5` 区段 `{f1: type}`；**type 18** 的 `f19` 是单元格数据：`f5` 共享字符串表（重复 `f1{f1:纯文本}` → plain[]；重复 `f2{重复 f3 run{f3{f1:文本}, f7{f11{f1:超链接}}}}` → rich[]，两张表各自按顺序编号），重复 `f6` 单元格 `{f1:row, f2:col, f3{f1:类型, f2{f1:索引}}}`：类型 4 → plain[索引]，6 → rich[索引]，**2 → numbers[索引]**（`f5` 的第三种条目 `f3{f1: fixed64 double}` 按顺序编号；序号/年份/纯数字提取码都走这里，文档 `DYU5Idmdid2JjVmxj` 一个 sheet 就有 2,846 个），0 → 空样式；0 值字段在 wire 上省略。[待确认] `DYU5Idmdid2JjVmxj` 首 sheet 2,846 个类型 2 索引各不相同但 numbers 表只有 2,718 条，尾部 129 个（行 ≥1360）越界；实现按空单元格处理、不计 unknownCellTypes。想复核可单独请求 1300~1481 行区块看表是否补全（本次两次请求都网络超时未做）。
- 区块范围由 `block_start_row/block_end_row` 控制，可一次请求 0~4999 拿整表（按 `max_row` 截断）；**越界不报错而是退回第一块**，循环必须以 `maxRow` 为终止并校验返回块 `end_row_index >= start`。
- 对账：doc `DR1paWVp2cWxmc3NW` tab BB08J2 1024 行 968 个唯一分享 id，与原始字节正则一致（正则多出的全是 URL 后跟长度字节 `h` 的伪 id）。

## 4. 格式 B：`dver 2.x`（`text[0]` 是数组）[事实]
- `text[0]` = op 组数组，op `{t, v, c}`；只需 **`t === 3`**：`c[0]=[sheetId,rowFrom,rowTo,colFrom,colTo]`，`c[1]={flatIndex: cell}`，`flatIndex=(row-rowFrom)*(cols)+(col-colFrom)`（行优先）。
- `cell["2"]=[类型,值]`（1 字符串 / 0 数字），`cell["6"]` 超链接（可能是 `#tab=xxx` 内部锚点），其余键为样式。
- 行范围由 **`startrow/endrow`** 控制（`0~5000` 一次拿 3414 行 1.5 MB；`2000~3999` 返回 2000~3413）。实现时两组参数同时带同一区间即可兼容两种格式。
- 出现于较老的文档（`DS25FQkJjbkZpUnZh`，8 sheet），网上随机 6 个文档中 1 个是格式 B。

## 5. 实测规模与耗时 [事实 2026-09-16, 本机 fc-chrome + Chrome 149]
- `DTFd3V3pzWmJFRWpY` 13 sheet / 9,131 链接、`DS25FQkJjbkZpUnZh`（格式 B）8 sheet / 8,345 链接，都在 150 s watchdog 内完成并分 17~19 批 result 回传；已删除文档 `DR0JQZVFvWm9qTm1z` 正确回传 `permanent:true`。
- 验证工具：不起 Chrome 用 NC-JS `apps/doc-cloud-spider` 的 `pnpm verify:qqdoc <url>`；本机端到端用记忆仓库 `scripts/docspider/e2e-local-fcchrome.sh`；"注入后无回传"先用 `scripts/docspider/cdp-inject-debug.py` 区分脚本问题与 fc-chrome 链路问题。

## 6. 与现有链路的关系 [事实 2026-09-16 合入 master]
云端脚本对所有文档 URL 都是同一份（`doc-cloud.user.js`，OSS 同时写旧名 `kdoc.user.js`），入口 `src/cloud/docCloud.ts` 按 hostname 分发到站点模块：`kdoc.ts` / `feishu.ts` / **`qqdoc.ts`**（`qqdocSite: SiteDef`，`watchdogMs` 150 s，纯解析逻辑在 `src/cloud/qqdoc/`：`protobufWire` / `qqSheetBlock` / `qqSheetJsonOps` / `qqOpendoc` / `linkAccumulator` / `qqdocMain.collectQqdoc`）。网关 `SubmitDoc` 不校验 URL、doc-crawler 只透传 `docType`（取 `qqSheet`），前端只改 `spiderAdmin/src/scheduler/spiderUtil.ts`（识别 `docs.qq.com/sheet/*`，URL 去掉 `?tab=`）。Node 侧批量验证：`node scripts/dev-vite-node.mjs scripts/qqdoc-verify.ts <url>`。
