---
title: 领域知识：四类在线文档的免登录取正文方式
type: knowledge
status: active
created_at: 2026-09-16T09:30:00+08:00
updated_at: 2026-09-16T09:30:00+08:00
priority: high
keywords: [腾讯文档, dop-api/opendoc, 金山文档, kdocs, 飞书, feishu, 石墨, shimo, lizard-api, 免登录, SSR, WPS JSAPI, workbook, related_sheet, tab]
questions:
  - 腾讯文档表格/文档怎么不登录拿到全部内容和修改时间
  - 金山文档、飞书、石墨能不能免登录抓正文，各用什么接口
  - 腾讯 sheet 多个子表(tab)怎么全拿到
summary: 腾讯 opendoc(sheet 逐 tab、zlib 分块)/飞书 SSR/石墨 lizard-api/金山 WPS JSAPI 四平台匿名取正文与修改时间的接口、格式与坑；实现在 COMMON docfind/docfetch.py
load: on-demand
valid_until: 2026-12-31
related:
  - agent-memory/procedures/workflow-文档发现.md
  - agent-memory/knowledge/architecture-fc-chrome文档爬虫上云.md
  - agent-memory/knowledge/domain-腾讯文档表格解析.md  # 线上云端脚本(页面内同源 fetch)的解析实现, 与本文 HTTP 取法同源
  - agent-memory/knowledge/domain-飞书文档解析.md
---

# 四类在线文档的免登录取正文方式（[实测 2026-09-16]，实现见 COMMON `site-discovery/tools/docfind/docfetch.py`）

## 腾讯文档 docs.qq.com（HTTP 即可）

- 先 `GET` 文档页拿 cookie（`traceid`/`TOK`/`hashkey`），再 `GET /dop-api/opendoc?id=<短id>&outformat=1&normal=1`（带 `Referer`）。不带 cookie 直接 401。
- 响应 `clientVars`：`title`、`lastModifyTime`（毫秒）、`padType`（doc/sheet）、`collab_client_vars.initialAttributedText.text`。
- **doc**：`text` 是 op 列表（`DocKeyframe` mutations 里的字符串），整段 JSON 正则抽 url 即可（超链接以 `HYPERLINK https://... \tdfu https://...` 形式出现）。
- **sheet**：`text[0]` 有 `workbook` 与 `related_sheet` 两个 base64+zlib(`eAG...`) 的 protobuf 块；**单元格内容和链接在 `related_sheet`**，`workbook` 只有结构（含**全部子表 6 位 id**，如 `eguplw`、`BB08J2`）。不带 `tab` 只返回当前子表，**要逐 tab 再请求** `&tab=<id>`（实测 43 个 tab 全拿）。1482 行的表一次返回全部（`end_row_index=1481`），`startrow/endrow` 参数无影响。
- 少数老 doc 的 opendoc 不是合法 JSON（`"text":[裸文本...]`），要整段正则兜底；正文可能含未转义控制字符，`json.loads(strict=False)`。
- 页面本身还内嵌 `basicClientVars`（base64 JSON）含 `padId`/`lastModifyTime`/权限位，可作 HEAD 级快速判断。

## 飞书 feishu.cn / larkoffice.com（HTTP 即可，前提是匿名可读）

- 匿名可读的 `docx` / `wiki` 页面**服务端直出正文块**（`_block_ssr_metrics`），直接正则 HTML 抽 url；`"edit_time":<秒>` 与 `"create_time"` 在 HTML 里；`window.DATA.meta` 有 `title/isPermitted/isDeleted`。
- 未开匿名访问的文档会 302 到 `accounts.feishu.cn/accounts/page/login`，判 `need_login`。老版 `/docs/doccnXXX` 基本都要登录。
- 超长文档 SSR 可能只出前若干块，`--browser` 用页面 innerText 补（滚动触底触发懒加载）。
- 注意本机 TUN 代理把 `*.feishu.cn` 解析成 198.18.x.x fake-ip，偶发 ConnectTimeout，会话要挂重试。

## 石墨 shimo.im（元信息 HTTP，正文要浏览器）

- `GET /lizard-api/files/<guid>?collaboratorCount=true` 匿名可得 `name / updatedAt / contentUpdatedAt / passwordProtected / shareMode`。
- 正文接口 `/lizard-api/files/<guid>/content` 匿名 403；`export`、`plain`、`history` 也不通。只能本机 Chrome 打开后读 `innerText` + `a[href]`。
- 搜索引擎几乎不索引石墨正文，`site:shimo.im 网盘` 搜不到；候选主要来自 GitHub 代码搜索与 link3。

## 金山文档 kdocs.cn（必须浏览器）

- curl 直接 302 到 `account.kdocs.cn/passport/singlesign?cb=...&f=c`，无匿名 HTTP 路径。
- 本机 Chrome 打开 `/l/<id>`：页面经 singlesign 中转再回到 `/l/`，**要等地址稳定再注入 JS**，否则 `Inspected target navigated or closed`。
- 就绪后 `window.__WPSENV__`（`office_type`: s/k=表格、w=文字；`file_info.file.modify_time` 秒级修改时间、`fname`），`window.APP.getWorksheets().getSheetsId()` 枚举子表，`sheet.getUsedRANGE / sheetData.prepareBlock / getRowValidBound / getCellString / getHyperlink` 逐行读（移植自 userscripts `src/cloud/kdocCloud.ts` 的 `copySheet`，含"连续 1000 行空则停"与每 500 行让出事件循环）。
- 匿名可读的表格会渲染但顶栏显示"立即登录"，不影响 JSAPI 读数；真正需登录的正文只有"邀请你协作查看文档 / 立即登录"几行文字。
