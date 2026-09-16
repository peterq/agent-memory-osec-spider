---
title: 飞书文档解析（docx / 多维表格）
type: knowledge
status: active
created_at: 2026-09-16T09:00:00+08:00
updated_at: 2026-09-16T11:20:00+08:00
priority: high
keywords: [飞书文档, feishu, 多维表格, bitable, docx, client_vars, clientvars, doc-cloud, 云端脚本]
questions:
  - 飞书文档的网盘链接用哪些接口解析、怎么分页
  - 飞书 wiki 怎么区分 docx 与多维表格
  - 飞书文档需登录/已删除时怎么处理
summary: 飞书 docx/多维表格解析依据：匿名可读、client_vars/clientvars 接口与分页、objType 映射、3000 行上限、登录墙与已删除判定、验证与未覆盖项
load: on-demand
valid_until: 2027-03-16
related:
  - agent-memory/knowledge/architecture-fc-chrome文档爬虫上云.md
  - agent-memory/lessons/success-在线文档解析优先用页面自带接口.md
  - agent-tasks/2026-09-16-feishu-doc/99-notes.md
---

# 飞书文档解析（2026-09-16 接入）

## 代码位置 [事实]
- 云端脚本 NC-JS `apps/doc-cloud-spider/src/`（2026-09-16 从个人仓库 userscripts `src/cloud/` 迁入）：`main.ts`（入口按域名分发）→ `runtime.ts`（nonce/回传/watchdog）→ `sites/kdoc.ts` / `sites/feishu.ts`（站点实现）；`sites/feishuParse.ts` 纯函数带夹具单测（`sites/__fixtures__/`）。产物 `dist/doc-cloud.user.js`，OSS `fc-chrome/userscripts/doc-cloud.user.js`，`pnpm upload` 同时写旧对象名 `kdoc.user.js`。
- SPIDER `services/doc_crawler` 默认 `userscript_url` 已指向 doc-cloud；docType 回传 `feishuDocx` / `feishuBitable`（金山仍 `kdocSheet`）。
- NC-JS spiderAdmin `src/scheduler/spiderUtil.ts`：`DocType` 增加 `feishu`，正则只截到 token（丢 `?table=`）。
- 验证工具：该包 `pnpm verify:cloud <url>…`（`scripts/verify_cloud.py`，本机调试 Chrome 9222 模拟 inject=1）。

## 页面与接口 [事实，2026-09-16 抓包]
- 公开分享文档**匿名可读**；页面自身接口带 cookie 直接 `fetch` 即可（同源）。非浏览器 UA 会被 302 到 `accounts.feishu.cn/accounts/page/login?…with_guest=1`，真实 Chrome 直接落地。
- 链接形态：`<tenant>.feishu.cn/{wiki|docx|base}/<token>`、`<tenant>.larkoffice.com/…`、`docs.feishu.cn/article/wiki/<token>`、`docs.feishu.cn/v/wiki/<token>/xx`（后两者 302 到租户域）。
- wiki 节点类型：`window.wiki_info_map[wikiToken] = {objToken, objType}`，objType **22=docx、8=多维表格、12=文件(pdf)**；其余按永久失败。
- docx 块数据：`GET /space/api/docx/pages/client_vars?id=<objToken>&mode=7&limit=N`，首片 `next_cursors[]`，逐个 `&cursor=` 拉到没有新 cursor（38 块 limit=5 → 8 次拉齐）。`mode=4` 是同步块专用（报 4000091 invalid paging cursor）；不带 mode 一次返回全部但大文档是否封顶未验证。块文本在 `data.text.initialAttributedTexts.text`，超链接是 `apool.numToAttrib` 里 `["link", encodeURIComponent(url)]`。SSR 首片在 `window.DATA.clientVars.data`（接口失败时兜底）。
- 多维表格：`GET /space/api/v1/bitable/<token>/clientvars?tableID=<tbl>&recordLimit=3000&needBase=true&openType=0&noMissCS=true`；`data.table` / `data.base` 是 **gzip+base64（"H4sI" 开头，encoding=0 也如此）**，用 `DecompressionStream('gzip')` 解。`base.blocks` 顺序 + `blockInfos`（带 `blockType` 的是仪表盘 36 等，`tbl` 前缀才是表）；`table.meta.recordsNum`、`recordMap[rec][fld].value`（string | number | [{type:'text'|'url', text, link}] | {users:[…]}）。**recordLimit 上限 3000**（800004006）。超出的"按需表"走 `POST …/ondemand/records?tableID&viewID&tableRev&jointRev` body `{ranges:[{start,end}], viewId, localViewConfig:{filter:null,sort:"[]",group:"[]"}, withExtra:{groupInfos:true}, removeFmlExtra:true}`（小表会原样返回全表；`ondemandVer:2` 只对按需表有效）[推断：请求格式抓自前端 bundle，未在真实按需表验证]。
- 修改时间：`GET /space/api/meta/?type=<objType>&token=<objToken>` → `edit_time`（秒）。
- 失败判定：client_vars `4000007 resource deleted` → 永久；`920004004 PermFail` → 永久；需登录的文档停在 `accounts.feishu.cn/…/login?…login_redirect_times=1`，`onIntermediatePage` 10 s 后仍在该页 → 永久失败。`tablesv3/` 匿名 "Failed to fetch"，不用。

## 验证结论（2026-09-16，本机 Chrome）[事实]
14 个 URL：docx 8 条（含 1364 链接长文、docs.feishu.cn 两种跳转形式、直连 docx）、多维表格 2 条（模板库，行全拉到但无网盘链接）、PDF/已删除/需登录各 1 条永久失败、金山回归 193 链接。明细 `agent-tasks/2026-09-16-feishu-doc/99-notes.md`。
未覆盖：带网盘链接的公开多维表格、>3000 行按需表、Tampermonkey 路径。

## 风险 [事实]
PC 端油猴调度器不按域名过滤 `popTask`，会拿到飞书任务但无脚本回传 → 保活超时后网关重试；上线前应让 PC 调度器跳过非 kdocs 任务或停用。
