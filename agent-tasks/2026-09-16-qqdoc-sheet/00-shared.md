# 共享上下文：文档爬虫新增「腾讯文档(docs.qq.com) 表格」解析

> 所有参与本任务的子 Agent 都必须先读完本文件，再读自己那份角色简报。

## 1. 任务目标（用户原话）

> 现有金山文档解析获取网盘链接, 需增加腾讯文档, 示例
> https://docs.qq.com/sheet/DR1paWVp2cWxmc3NW?tab=BB08J2
> https://docs.qq.com/sheet/DTFd3V3pzWmJFRWpY?tab=7f9s70
> 开发好后, 去网上多找几个文档链接, 进行验证.
> 现有其他功能在开发, 需使用 worktree, 合并 master 前和我确认

## 2. 现有链路（事实，直接用）

```
后台 NC-JS(spiderAdmin 文档页) 提交文档 URL ──gRPC──▶ 网关 doc_scheduler(不校验 URL, type 初始 "unknown")
   ──PopTask──▶ SPIDER doc-crawler(services/doc_crawler) ──WS──▶ FC Chrome(nc-app-prod-cdp3, COMMON fc-chrome)
   打开 <docUrl>#taskNonce=<uuid>, inject=1 把云端脚本注入每个页面(document-start, 主世界)
   云端脚本(userscripts 仓库 src/cloud/kdocCloud.ts) 解析 → console.log('[[DOC_SPIDER]]'+json) 回传
   doc-crawler 收 result → CommitResource2 提交链接 → TaskDone(type=docType, docMtime, version, linkCount)
```

- 云端脚本对**所有**文档 URL 都是同一份（doc-crawler 配置 `UserscriptUrl` 单值，线上
  `https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/userscripts/kdoc.user.js`）。
  因此腾讯文档支持 = **同一份脚本按 `location.hostname` 分派** + 前端识别 docs.qq.com 链接。
  网关、doc-crawler、契约都**不需要改**。
- console 协议正本：`/home/peterq/dev/projects/peterq/agent-memory-osec-spider/agent-tasks/2026-09-08-monitoring-and-doc-fc/05-doc-fc-contract.md` §3
  （nonce/start/progress/result 分批 seq+final/error permanent；单条 ≤200KB；60s 内首条 start；异常必须发 error）。
- 金山文档现有实现与踩坑全部写在 `src/cloud/kdocCloud.ts` 的注释里（原生 console.log 引用、nonce 存取、watchdog、心跳、分批 result），**腾讯文档实现必须复用同一套回传/守护基础设施，不要另起一套**。

## 3. 仓库、分支与工作树（已建好，不要自己再建）

| 角色 | 工作树路径 | 分支 | 基于 |
|---|---|---|---|
| 云端脚本（10） | `/home/peterq/dev/projects/peterq/userscripts-wt-qqdoc` | `feat/qqdoc-cloud` | userscripts `master@0e86ba1`；依赖已 `pnpm install --offline` |
| 前端（20） | `/home/peterq/dev/projects/1s/ncjs-wt-qqdoc` | `feat/qqdoc` | nc-js `main@dbbbbcc`；依赖已 `pnpm install --offline` |

- 主工作树（`/home/peterq/dev/projects/peterq/userscripts`、`/home/peterq/dev/projects/1s/nc-js`）里有**别人正在开发的未提交改动，禁止碰、禁止 checkout/stash**。
- 每个角色只在自己的工作树里提交；`git commit -- <自己改的路径>` 带 pathspec，不要裸 `git commit -a`；**不要 push，不要合并 master/main**（用户要求合并前先确认）。
- 提交信息中文，**禁止** `Co-Authored-By`/邮箱（远端会拒绝）。代码注释中文。

## 4. 腾讯文档数据接口（主控已用 curl 实测，2026-09-16；夹具见 `fixtures/`）

### 4.1 页面与鉴权
- `GET https://docs.qq.com/sheet/<docId>?tab=<sheetId>`：公开分享文档匿名直接 200，**无 SSO 重定向链**（与金山不同），
  `#taskNonce=` 不会被冲掉。响应 Set-Cookie：`hashkey`/`TOK`/`traceid`/`tgw_l7_route`。
- 页面 HTML 里 SSR 内嵌一个 `<script src="//docs.qq.com/dop-api/opendoc?...&callback=clientVarsCallback&t=...">`（首块数据）。
- `dop-api/opendoc` **没有 Cookie 时返回 401**；带上页面下发的 Cookie 即 200。脚本在页面内用同源 `fetch(..., {credentials:'include'})` 天然满足。
  `t=`/`xsrf=` 参数**不是必需**（去掉 t 实测 200）。

### 4.2 取数接口（JSONP）
```
GET https://docs.qq.com/dop-api/opendoc?id=<docId>&tab=<sheetId>&normal=1&outformat=1&wb=1&nowb=0
    &noEscape=1&enableSmartsheetSplit=1&needSheetState=1&sliceStates=1&startrow=0&endrow=60
    &block_start_col=0&block_end_col=16383&block_start_row=<s>&block_end_row=<e>&callback=clientVarsCallback&xsrf=
```
响应体 `clientVarsCallback({...})`，去掉包裹后是 JSON。关键路径：

| 路径 | 含义 |
|---|---|
| `padType` | `"sheet"` 才是表格；bogus id 返回 `"blankpage"`（且 `clientVars.retcode`=200061、`errcode`、`errmsg` 出现） |
| `clientVars.title` | 文档标题 |
| `clientVars.lastModifyTime` | 最后修改时间，**毫秒**时间戳 → `docMtime` |
| `clientVars.collab_client_vars.header[0].d[]` | sheet 列表 `{id,name,hidden,type:"grid"}`（不带 tab 参数也返回全部） |
| `clientVars.collab_client_vars.padSubId` | 当前响应对应的 sheet id |
| `...initialAttributedText.text[0].max_row / max_col` | 该 sheet 行列上限（doc1 BB08J2: 1024×25） |
| `...initialAttributedText.text[0].workbook` | base64(zlib) protobuf，工作簿元信息（不需要） |
| `...initialAttributedText.text[0].block_datas[i]` | `{start_row_index?(0 时省略), end_row_index, start_col_index?, end_col_index, related_sheet}` |
| `block_datas[i].related_sheet` | **base64 → zlib inflate（头 `78 01`）→ protobuf**，含该区块单元格 |

区块范围实测：
- `block_start_row=0&block_end_row=4999` → 一次返回 0~1023 全部（按 max_row 截断）；`0~255` 与 `256~511` 分块请求也各自正确。
- **越界**（`5000~9999`，超过 max_row）时服务端**不报错而是退回第一块（0~255）**：分块循环必须用 `max_row` 作终止条件，并校验返回块的 `end_row_index >= start`，否则会死循环/重复计数。
- `block_end_col=16383` 可接受，返回按 `max_col` 截断。

### 4.3 区块 protobuf 结构（用通用 wire-format 遍历得出；`ref/pbwalk.py` 打印字段树，`ref/qqextract.py` 是已验证的提取原型）
```
root
└ f1 (msg)
   ├ f4 {f1: "3.0.0"}                       版本
   └ f5 (repeated, "区段") {f1: <type varint>, f<type+1>: payload}
       type 18 = 单元格数据, payload 在 f19:
         ├ f3 {f1: sheetId, ...}
         ├ f4 样式(忽略)
         ├ f5 共享字符串/数字表(顺序即索引, 三张表分开计数, 各自独立从 0 计数):
         │    repeated f1 {f1: 纯文本}                         → plain[]
         │    repeated f2 {repeated f3 run{ f3{f1: 文本}, f7{f11{f1: 超链接 url}} }} → rich[]
         │    repeated f3 {f1: fixed64 double}                 → numbers[]（2026-09-16 追加, 见下）
         └ repeated f6 单元格 {f1: row(0 省略), f2: col(0 省略), f3 值{f1: 类型, f2{f1: 索引(0 省略)}, f4 样式}}
               类型 4 → plain[索引];  类型 6 → rich[索引](各 run 文本拼接, 超链接 url 若不含于文本则追加 "(url)")
               类型 2 → numbers[索引], 输出 String(n)（整数不带 .0; 2026-09-16 追加, 提取码/年份/
                 序号等纯数字单元格走这里, 之前误判成"其他类型"计入 unknownCellTypes, 见下方实测说明）
               类型 0 → 空(只有样式);  其他类型: 若含 fixed64 双精度按数字输出, 否则忽略
```
- varint/长度前缀均为标准 protobuf；wire type 0/1/2/5 都会出现，遍历器必须处理 fixed64/fixed32。
- 判断某个 length-delimited 字段是"子消息"还是"字符串"：先尝试按 protobuf 解析且字段号全在 1~100 内视为子消息，否则按 UTF-8 字符串——**只用于兜底扫描**；主路径按上表固定路径取值，不靠猜。
- 【2026-09-16 追加】数字单元格实测: `https://docs.qq.com/sheet/DYU5Idmdid2JjVmxj`(12 sheet) 曾把
  全部数字单元格算进 unknownCellTypes(20356), 根因是漏了类型 2(数字)分支——单元格值消息是
  `f3{f1=2, f2{f1=索引}}`, 索引指向的不是直接内嵌的 fixed64, 而是 f5 里第三种条目
  `repeated f3 {f1: fixed64 double}`(与 plain/rich 用法一致, 都是"索引进共享表")。夹具
  `fixtures/doc4-DYU5Idmdid2JjVmxj-tab-BB08J2-rows0-1481-numeric-cells.js`(1482 行, f5 子字段
  分布 f1(plain)=2920 / f2(rich)=3 / f3(numbers)=2718, 类型 2 单元格 2846 个)对账通过, 但发现
  其中 129 个类型 2 单元格引用的索引超出 numbers[] 实际收集到的条目数(已核实: 该区块只有一个
  type=18 区段, 没有别的区段携带补充数字表, 也不是解析遗漏)——判断是文档编辑历史里的悬空引用
  (id 已分配但对应数值后来被覆盖/清空)。处理方式: 索引越界时按空单元格处理、不计入
  unknownCellTypes(该计数器只用来发现"没见过的单元格类型", 不是"类型认识但取不到值")；
  真正的数字条目本身缺 f1(fixed64) 才计入。
- 对账结论（`ref/qqextract.py` 跑夹具）：doc1 BB08J2 1024 行 / **968** 个唯一分享 id；doc1 fuv7gd 65 行 / **64**；doc2 7f9s70 22 行 / **21**。
  原始字节正则扫描多出来的全是 `…h` 结尾的伪 id（URL 后紧跟的 protobuf 长度字节 0x68），结构化提取无遗漏。

### 4.4 【2026-09-16 08:40 追加】第二种数据格式：`dver 2.x`（`text[0]` 是 JSON op 列表，不是 protobuf）
主控用网上找到的文档 `https://docs.qq.com/sheet/DS25FQkJjbkZpUnZh`（8 个 sheet，单 sheet 3414 行）实测发现**老文档返回的是另一种格式**，实现必须同时支持两种，按 `text[0]` 的类型分派：
- `typeof text[0] === 'object' && !Array.isArray(text[0])`（含 `block_datas`）→ §4.3 protobuf 格式（`dver 3.0.0`）。
- `Array.isArray(text[0])` → 本节 JSON 格式（`dver 2.11.0`）。夹具：`fixtures/doc3-DS25FQkJjbkZpUnZh-tab-g73g1s-rows0-60-dver2.js`（只请求了 0~60 行）。

结构：`text[0]` 是 **op 组的数组**，每组是 op 数组，op 形如 `{t: <类型>, v: 5, c: [...]}`。只需要 **`t === 3`** 的 op：
```
c[0] = [sheetId, rowFrom, rowTo, colFrom, colTo]          本 op 覆盖的范围(闭区间)
c[1] = { "<flatIndex>": cell, ... }                        flatIndex = (row-rowFrom)*(colTo-colFrom+1) + (col-colFrom)  → 行优先
cell["2"] = [valueType, value]   valueType 1 → 字符串; 0 → 数字(int/float, 用 String() 输出, 提取码可能是数字)
cell["6"] = "https://..."        超链接(可能出现在没有 "2" 的单元格上, 也可能是 "#tab=xxx" 内部锚点); 与文本不同/文本不含时追加 "(url)"
cell["0"]/["3"]/["8"]/["12"]…   样式等, 忽略
```
- 一个 op 里 `c[1]` 只包含非空单元格；没有 `"2"` 也没有 `"6"` 的 cell 视为空。
- 行范围由 **`startrow`/`endrow`** 控制（不是 block_*）：`startrow=0&endrow=5000` 一次返回 0~3413 全部（1.5 MB）；`startrow=2000&endrow=3999` 返回 2000~3413。总行数用 `collab_client_vars.maxRow`（两种格式都有这个字段，3.0.0 里等于 `text[0].max_row`）。
- **分块循环必须两种格式统一**：每次请求同时带 `startrow/endrow` 与 `block_start_row/block_end_row` 同一区间 `[s, s+CHUNK-1]`；终止条件 `s >= maxRow`；再加"返回的数据范围低于 s 则 break"保护（protobuf 格式看 `end_row_index`，JSON 格式看 `c[0][2]`）。
- 对账数（`ref/` 里的 Python 口径）：doc3 tab g73g1s 全量 3414 行 / **3553** 个唯一分享 id；小夹具（0~60 行）61 行 / **63** 个 id，第 1 行文本为 `夸克资源👉\t👉点我查看夸克更新文档👈(https://docs.qq.com/doc/DS2ZveFhIR3NZQXZi)`。
- 空白页/已删除文档的另一种表现：`padType: "blankpage"`、`clientVars.retcode: 0`、`errmsg: "blankpage type:2 null"`（夹具 `fixtures/deleted-doc-DR0JQZVFvWm9qTm1z-blankpage.js`）→ 同样 permanent error。判定统一为：`padType !== 'sheet'` 或 缺 `initialAttributedText` → permanent；`retcode` 非 0/非空时把 code 带进 message。
- 其余 4 个网上文档（DZUZyd3ZobE5jVFJq / DTmpEb25Obnh3cW9i / DV05PZWx6QUFBeHdt / DYU5Idmdid2JjVmxj）都是 3.0.0 格式，主控验证阶段会用。
- `ref/qqfetch.py <docid> <tab> <startrow> <endrow> <out.js> [bs be]` 可拉任意区间做夹具（自动带 Cookie）。

## 5. 硬性约束（会返工或出生产事故）

1. **绝不执行 `pnpm upload:cloud` / `pnpm upload`**（会覆盖线上 OSS 上正在服役的脚本）。构建只到 `pnpm build:cloud` 产出 `dist-cloud/kdoc-cloud.user.js` 为止。
2. **NC-JS 绝不执行 `pnpm build`**（构建脚本会真实上传生产 OSS，见 `lessons/failure-ncjs构建脚本会自动上传OSS.md`）。只跑 type-check / vitest / dev。
3. 金山文档路径的行为**不能有任何回归**：`www.kdocs.cn`/`365.kdocs.cn`/`account.kdocs.cn` 上的 nonce 存取、SSO 处理、回传协议、watchdog、心跳、分批逻辑保持等价；允许把公共部分抽成函数复用，但验收会逐行 diff。
4. 云端脚本必须**单文件、无外链、无 npm 运行时依赖**（不要引入 pako/protobufjs 等）；zlib 解压用浏览器内建 `DecompressionStream('deflate')`（线上 Chrome 153、本机 Chrome 149、Node 22 都有）。
5. **禁止使用 Monitor / 禁止"起后台任务再等通知"**：命令都前台跑完；测试用夹具，不要为了"证明跑通"去反复请求线上文档（对账用夹具 + 最多 2~3 次真实请求即可）。
6. 不要采信本简报以外的口头转述；有疑问先看 `fixtures/` 里的真实数据。

## 6. 邮件与汇报
子 Agent 不发邮件（主控统一发）。完成后在最终汇报里给出：改动文件清单、提交哈希、测试命令与输出摘要、未完成/存疑项。
