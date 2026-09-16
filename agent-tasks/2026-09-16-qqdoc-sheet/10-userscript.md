# 角色 10：云端脚本——在 `kdocCloud.ts` 同一份脚本里增加腾讯文档表格解析

工作树：`/home/peterq/dev/projects/peterq/userscripts-wt-qqdoc`（分支 `feat/qqdoc-cloud`）。先读 `00-shared.md`。

## 必读文件（为什么读）
- `src/cloud/kdocCloud.ts`：现有金山实现。你要复用它的 `nativeConsoleLog`/`emit`/`emitTerminal`/watchdog/心跳/`parseResLinkFromText`/`calVersion`/分批 result，并把主流程按 host 分派。
- `vite.cloud.config.ts`：云端构建 target；`@match` 要加 `https://docs.qq.com/sheet/*`（`inject=1` 路径不看 match，但 Tampermonkey 路径看）。
- `agent-tasks/2026-09-16-qqdoc-sheet/ref/qqextract.py`（Python 原型，已验证）：`extract_block()` 就是你要用 TS 重写的算法；`pbwalk.py` 是通用 wire 遍历，可照抄成 TS。
- `agent-tasks/2026-09-16-qqdoc-sheet/fixtures/*.js`：真实 JSONP 响应，作单测夹具。

## 落点与结构（建议，可微调但要说明）
```
src/cloud/
├── kdocCloud.ts                 入口: 抓原生 console.log → nonce → 按 host 分派: kdocs → 现有 main(); docs.qq.com → qqdoc/main
├── qqdoc/protobufWire.ts        通用 protobuf wire 解析: parseFields(Uint8Array) → {field, wireType, value}[]; varint/fixed32/fixed64/bytes
├── qqdoc/qqSheetBlock.ts        related_sheet(base64) → inflate → 按 §4.3 固定路径取 plain/rich/cells → rows: Map<row, Map<col,string>> → 行文本[]
├── qqdoc/qqOpendoc.ts           opendoc URL 拼接、JSONP 去壳、header/sheet 列表、错误判定(padType!=='sheet'、retcode/errcode)、分块循环
└── qqdoc/*.test.ts              vitest 单测(Node 环境, 用夹具)
scripts/qqdoc-verify.ts          Node 侧验证脚本(见下), README.md 里补一节用法
```
纯逻辑模块（protobufWire/qqSheetBlock/JSONP 去壳）**不得引用 window/document/console**，这样才能在 Node 里单测和跑验证脚本；DOM/fetch 只在 `qqOpendoc.ts` 的取数函数和入口里出现，且取数函数接受可注入的 `fetchJsonp(url) => Promise<string>` 以便验证脚本复用同一套解析。

## 腾讯文档主流程要求
1. 仅在 `location.hostname === 'docs.qq.com'` 时走本分支。`location.pathname` 形如 `/sheet/<docId>`；不是 `/sheet/` 的（`/doc/`、`/slide/`、`/form/`、`/smartsheet/`…）→ `emitTerminal({event:'error', permanent:true, message:'暂仅支持腾讯文档表格(docs.qq.com/sheet/*)'})`。
2. nonce：docs.qq.com 无重定向链，直接用现有 `hashNonce || readStoredNonce()`（localStorage）即可；`kdocsCookieDomain()` 在此 host 返回 null 属预期。DOC_HOSTS 判定要扩到 docs.qq.com（否则会走到"中间跳，直接 return"）。
3. `emit({event:'start'})` 后**不要等页面 App 就绪**（腾讯页面的内部对象我们不用），直接 fetch 数据：
   - 第一步：`opendoc(id, tab=<url 上的 tab 或空>)` 拿 `padType`、`title`、`lastModifyTime`、`header[0].d[]`。
     `padType !== 'sheet'` 或存在 `clientVars.retcode/errcode` 或缺 `collab_client_vars.initialAttributedText` → **permanent error**，message 带上 retcode/errmsg 便于排查；HTTP 非 200 / 网络异常 / JSON 解析失败 → 非 permanent error（可重试）。
   - 第二步：遍历 header 里**全部** sheet（含 hidden；`type` 不是 grid 的也尝试，失败只记进度不终止），每个 sheet 按 `CHUNK_ROWS = 2000` 分块：`start=0; while(start < maxRow){ 请求 [start, start+CHUNK-1]; 取 max_row; 校验返回 block 的 end_row_index >= start, 否则 break; 解析; start += CHUNK }`。首个 block 可能同时返回多个 `block_datas`，全部解析。
   - 每解析出一行非空文本 → `parseResLinkFromText(rowText)` 去重累加，`scanned++`，每 200 行 `emit progress`（沿用现有节奏与 `scannedSoFar`）。
   - 单元格拼行：按 col 升序 `\t` 连接；rich run 的超链接 url 不含于文本时追加 `(url)`（与金山 `getHyperlink` 行为一致，`pwd` 识别依赖 ±50 字符上下文，所以行内顺序必须是 row-major）。
   - 兜底：对每个区块再做一次"全部字符串叶子扫描"，把结构化行里没出现的链接补进去（覆盖未知单元格类型）；正常夹具下兜底应补 0 条，测试要断言这一点。
4. 结束：`docType: 'qqSheet'`，`docMtime = new Date(lastModifyTime).toISOString()`（毫秒），`version = calVersion(urls)`，分批 result 与金山完全一致（复用同一段代码）。
5. watchdog：金山是 90s 总闸；腾讯按 fetch 计，大文档多 sheet 可能更久，把总闸做成按 host 可配（腾讯 150s），每次 fetch 单独 `AbortController` 20s 超时；`TaskTimeoutSec` 缺省 240s，别超过。
6. zlib：`new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'))).arrayBuffer()`；base64 用 `atob` + 手工转 Uint8Array（Node 22 也有 atob）。注意 Node 22 的 `DecompressionStream` 是全局对象，测试无需 polyfill。
7. 单元格类型 0（空样式）、4（plain）、6（rich）之外的类型：含 fixed64 → 按 `String(Number)` 输出（提取码可能是纯数字单元格）；其余忽略但计数到一个 `unknownCellTypes` 统计并在最终 result 附 `stats:{sheets, rows, unknownCellTypes}`（多余字段 doc-crawler 会忽略，方便线上排查）。

## 单测（vitest，`pnpm test -- --run`）
- `protobufWire.test.ts`：手工构造字节验证 varint 多字节、fixed64、嵌套 bytes、截断输入抛错。
- `qqSheetBlock.test.ts`（用夹具，断言用 §4.3 对账数）：
  - `doc1-...-tab-BB08J2-rows0-1023.js`：1024 行；唯一分享 id 968；第 1 行文本包含 `https://pan.quark.cn/s/c8a6cf153e50` 与 `https://pan.baidu.com/s/11ar5NpgF5v6xqvJ20VVDOw?pwd=v98k`；经 `parseResLinkFromText` 后该百度链接 pwd 为 `v98k`。
  - `doc1-...-tab-fuv7gd.js`：64 个唯一 id。
  - `doc2-...-tab-7f9s70.js`：21 个唯一 id；第 2 行文本等于 `《中国少年儿童百科全书》有声版\thttps://pan.quark.cn/s/95cfe0d2f5ca(https://pan.quark.cn/s/95cfe0d2f5ca#/list/share)`。
  - 三个夹具兜底扫描新增均为 0。
- `qqOpendoc.test.ts`：JSONP 去壳；`bogus-id-...js` → 判定为 permanent 错误且 message 含 `200061`；header 解析出 doc2 的 sheet 列表（首页/最近更新/教育考试/…）；分块循环用桩 `fetchJsonp` 验证"越界退回第一块"时能正确终止。
- 夹具放 `src/cloud/qqdoc/__fixtures__/`（从任务目录复制，`doc1-page.html` 不用复制）。

## Node 侧验证脚本 `scripts/qqdoc-verify.ts`
用途：不起 Chrome，直接对任意 `docs.qq.com/sheet/*` 链接跑同一套解析，打印 sheet 数、行数、链接数、按类型计数、前 5 条链接、docMtime。
- 先 `fetch(页面 URL)` 拿 `set-cookie`，再带 Cookie 请求 opendoc（Node 22 全局 fetch；自行拼 `Cookie` 头，UA 写 Chrome 桌面）。
- 运行：`pnpm exec vite-node scripts/qqdoc-verify.ts https://docs.qq.com/sheet/DR1paWVp2cWxmc3NW`（vite-node 随 vitest 1.x 已装；若不可用改用 `tsx`/`node --experimental-strip-types` 并在 README 写明）。
- 在 `README.md` 增加「腾讯文档验证脚本」一节。主控会用它批量验证网上找到的链接。

## 构建与自检
- `pnpm build:cloud` 必须成功；产物 `dist-cloud/kdoc-cloud.user.js` 单文件、含 `@match https://docs.qq.com/sheet/*`、grep 不到 `require(`/`import(`。
- `vite.cloud.config.ts` 的 `version` 升到 `0.2.0`，头注释补腾讯说明。
- **不要执行 `pnpm upload:cloud`**。

## 交付
`git add` 自己的文件并 `git commit -- <paths>`（不 push）。汇报：文件清单、commit 哈希、`pnpm test -- --run` 与 `pnpm build:cloud` 输出摘要、验证脚本对两个示例链接的输出、存疑项。
