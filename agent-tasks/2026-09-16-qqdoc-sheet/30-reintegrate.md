# 角色 10 追加任务：把腾讯文档解析重新集成到 master 新结构（runtime + 站点模块）

背景：你开发期间 userscripts `master` 合入了飞书文档接入 `bf4c36d`，`src/cloud/kdocCloud.ts` **已删除**，云端脚本重构为：
`docCloud.ts`（入口，按 hostname 分发）→ `runtime.ts`（`bootstrap(site, nativeConsoleLog)`：nonce/回传协议/watchdog/心跳/去重/分批/版本号）→ 站点模块 `kdoc.ts` / `feishu.ts`（各自导出 `xxxSite: SiteDef` 与 `matchXxxHost(host)`）。产物改名 `dist-cloud/doc-cloud.user.js`，`upload:cloud` 同时写 OSS 的 `doc-cloud.user.js` 与旧名 `kdoc.user.js`。直接 `git merge` 会在 `vite.cloud.config.ts` 冲突、`kdocCloud.ts` 是"删除 vs 修改"。

工作树仍是 `/home/peterq/dev/projects/peterq/userscripts-wt-qqdoc`（分支 `feat/qqdoc-cloud`）。禁忌不变：不 push、不 `upload:cloud`、不碰主工作树。

## 必读
- `src/cloud/runtime.ts` 第 14~70 行（`DocResult` / `Runtime` / `SiteDef` 接口）与 `bootstrap()`（第 188 行起）：站点只需实现 `run(rt) → DocResult`，去重/分批/version/终态全部由 bootstrap 做。
- `src/cloud/feishu.ts` 末尾 `feishuSite` 的写法（`watchdogMs: 150*1000`、`isDocPage`、`cookieDomain`、`onIntermediatePage`）作为模板。
- `src/cloud/docCloud.ts`：分发入口。

## 要做的事
1. `git merge master`（在工作树里）。冲突处理：`kdocCloud.ts` 接受删除；`vite.cloud.config.ts` 以 master 为基底再加 `https://docs.qq.com/sheet/*` 的 `@match`，`version` 升 `0.3.0`；`package.json` 同时保留 `verify:cloud` 与 `verify:qqdoc`；`README.md` 两节都保留。
2. 新建 `src/cloud/qqdoc.ts`：导出 `matchQqdocHost(host)`（`host === 'docs.qq.com'`）与 `qqdocSite: SiteDef`：
   - `name: 'qqdoc'`；`isDocPage(loc)`：`loc.hostname === 'docs.qq.com'`（无 SSO 链，落地即文档页）；`cookieDomain()` 返回 `null`（只用 localStorage）；`watchdogMs: 150 * 1000`。
   - `run(rt)`：`parseQqDocLocation(location.pathname, location.search)` 为 null → `throw rt.permanentError('暂仅支持腾讯文档表格(docs.qq.com/sheet/*)')`；否则调用 qqdoc 目录里重构后的纯流程函数，返回 `{ docType: 'qqSheet', docMtime, links, warning? }`（某个 sheet 失败放进 `warning`，不终止；`stats` 不再需要单独字段，可拼进 warning 或省略）。
   - 进度：每解析出一行非空文本调 `rt.onRow()`；每个 sheet 开始时 `rt.stage('sheet', { name, index, total })`；首个响应后 `rt.stage('meta', { sheetCount, title })`。
3. 重构 `qqdoc/qqdocMain.ts`：去掉对 `emit/emitTerminal/calVersion/resultChunkSize/setScanned` 的依赖注入，改成纯函数 `collectQqdoc({ docId, tab, fetchJsonp, onRow, onStage, parseResLinkFromText }) → Promise<{ links, docMtime, sheetCount, rows, unknownCellTypes, fallbackAdded, warning? }>`；`OpendocError.permanent === true` 的错误在 `qqdoc.ts` 里转成 `rt.permanentError(message)` 抛出（bootstrap 按 `PERMANENT:` 前缀识别），非 permanent 直接抛（可重试）。
4. 删除 `src/cloud/shared/resLink.ts`、`shared/version.ts`：`parseResLinkFromText`/`calVersion`/`ResLink` 一律从 `../runtime` 导入（runtime 已导出同名同实现）；`linkAccumulator.ts`、`scripts/qqdoc-verify.ts`、单测同步改 import。验证脚本口径仍与 `collectQqdoc` 一致（直接复用它）。
5. `docCloud.ts` 加分支：`else if (matchQqdocHost(host)) bootstrap(qqdocSite, nativeConsoleLog);` 并更新头注释（金山 / 飞书 / 腾讯）。
6. 单测：原有 49 条语义保留（改 import/签名），补 `qqdoc.ts` 层 1 条：用桩 `Runtime`（onRow 计数、permanentError 返回带前缀的 Error）+ 桩 fetchJsonp 跑 doc2 夹具，断言返回 `docType: 'qqSheet'`、链接数 21、`onRow` 调用次数 = 非空行数。飞书/金山既有测试必须仍全过。
7. `pnpm test -- --run` 全绿；`pnpm build:cloud` 产出 `dist-cloud/doc-cloud.user.js`，头部含 4 类 `@match`（kdocs×3、feishu 若干、`https://docs.qq.com/sheet/*`），grep 不到 `require(`。
8. 真实验证一次即可：master 已有 `scripts/verify_cloud.py`（本机调试 Chrome 模拟 inject=1），按其 README 用法对 `https://docs.qq.com/sheet/DR1paWVp2cWxmc3NW?tab=BB08J2` 跑一次，期望 final result `docType=qqSheet linkCount=1032`；再对金山 `https://www.kdocs.cn/l/cdXYaQ5EOakI` 跑一次做回归（期望 193 条左右）。如该脚本在本机跑不起来，说明原因即可，主控用另一套端到端脚本兜底。
9. 提交（merge 提交 + 一次代码提交均可），中文提交信息，不 push。汇报：commit 哈希、测试/构建输出、验证输出、冲突处理方式、存疑项。
