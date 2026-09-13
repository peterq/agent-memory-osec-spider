# 角色 14：线上 Tampermonkey 路径（不带 inject）装了脚本却不执行 —— 诊断并修复（本地容器复现优先）

## 现状（主控 2026-09-13 10:45 实测，勿重查）
- 线上函数 `nc-app-prod-cdp3` 镜像 `fc-chrome:app-20260913d` = ACR `:base`（**无策略文件**）+ 叠层 `image/Dockerfile.seed`（COPY 策略 `image/policies/tampermonkey.json` + 带外预热的 seed profile）+ `bootstrap`（COMMON HEAD `4e255c3` 代码）。
  `https://fc-resource-node-api.krzb.net/cdp3/health` → `profileSeed:true, tampermonkey:5.5.0`。函数环境变量临时开了 `CHROME_EXTRA_ARGS="--enable-logging=stderr --v=1"`、`TM_READY_TIMEOUT_SEC=40`；timeout 600 s、2048 MB。
- **inject=1 路径线上全通**（20 s 出 result）。
- **TM 路径**：`go run ./cmd/localverify -mode tm -timeout 180 -fc wss://fc-resource-node-api.krzb.net/cdp3/chrome -script <OSS kdoc.user.js> -page https://www.kdocs.cn/l/cdXYaQ5EOakI -nonce x`
  → 5~9 s 握手；函数日志显示 Tampermonkey 就绪、`options.html#nav=utils` → `ask.html?aid=…` → `options.html#nav=dashboard` 都走到了，`tampermonkey.go:85 报告已点击导入, 未做安装结果二次校验`；随后页面 180 s 内**没有任何 `[[DOC_SPIDER]]`**，`-reload-after 20` 强制 reload 也没有 → 不是首次导航竞态。
  页面 console 里只见 Tampermonkey background.js 自己的 "alarm/Storage" 日志，无脚本输出。
- 日志获取：`cd fc-chrome && s fc-chrome logs --start-time "$(date -d '-10 min' '+%F %T')" --end-time "$(date '+%F %T')"`（网络抖动时重试；去 ANSI 色码 `sed -E 's/\x1b\[[0-9;]*m//g'`）。主控最近一次日志已存 `/tmp/claude-1000/-home-peterq-dev-projects-peterq-agent-memory-osec-spider/026b04c5-d598-4589-85fd-c28a13b7d650/scratchpad/fclogs3.clean`（6645 行，可直接 grep）。
- 本地：`docker images` 里有 `fc-chrome:base-seed`（策略 + seed，与线上叠层等价——注意本地这个是主控用本地 base 叠的，线上是 ACR base 叠的，Chrome 版本同为 153）与 `fc-chrome:app-seed`（旧 bootstrap）。本地容器访问 kdocs 走宿主机代理可能有 SSL 抖动，先用本地 `sample.html` 桩页（角色 13/20 之前用 `python3 -m http.server` 提供 `userscripts/dist-cloud/kdoc-cloud.user.js` 与一个带 `#taskNonce=` 的页面）复现，再上真实文档。
- 约束：不 `s deploy`、不 `docker push`（主控做：改完代码告诉主控即可，主控走 jenkins 叠层链）；可以本地 `make build` + `docker build` + `docker run` 任意验证；禁止 Monitor/后台等待；凭据不进输出。

## 排查清单（按序，拿到证据就写进 99-notes.md）
1. **脚本到底装进去没**：在 fc-chrome 里把 `installUserScript` 的"二次校验"补上——点完 ask.html 的 Install 后，打开 `options.html#nav=dashboard`，`Runtime.evaluate` 读已安装脚本列表（名称、是否 enabled、`@match`），写进日志并作为 `installResult.verified`。这样线上日志能直接回答"有没有装上"。
2. **Allow User Scripts 开关**：读 `chrome://extensions/?id=dhdgffkkebhmkfjojejmpbldmpobfkfo` 的开关状态（角色 13 的 seedprep 里有现成 DOM 路径），在 fc-chrome 启动后打一条日志；如果 seed 复制后开关丢了，看它到底持久化在 profile 哪个文件（`Default/Preferences` 的 `extensions.settings.<id>` 里某个 key？`Local State`？）——对比 seed 目录与运行时临时 profile。
3. **TM 是否真的注入**：TM 5.5(MV3) 用 `chrome.userScripts.register`；在 background.js 的 console 里找 "userScripts"/"register"/"inject" 相关日志；页面 `document-start` 时 TM 会在页面 console 打注入信息（可在 fc-chrome 里 `Runtime.enable` 页面 target 并转发 console）。也可以用 CDP 在页面里 `Runtime.evaluate("!!window.__kdocCloudLoaded")`（若脚本没有这种标记，给 `src/cloud/kdocCloud.ts` 加一个 `window.__DOC_SPIDER_LOADED__ = Date.now()` 的最早一行——改 userscripts 仓库要重新 `pnpm build:cloud && pnpm upload:cloud`，可以做）。
4. **@match/@run-at/元数据**：核对 OSS 上脚本头部（`curl -s <OSS url> | head -20`）与最终落地 URL（`https://www.kdocs.cn/l/cdXYaQ5EOakI` 可能被 SSO 302 到别的 host 再回来）；TM 安装页对 `@match` 里非法写法会静默改成"不匹配"。
5. **策略层面**：Chrome 138+ 对 force_installed 扩展的 `userScripts` 权限，除了 UI 开关是否还需要策略 `ExtensionSettings.<id>.toolbar_pin` 之类；查官方文档/Chromium 源码注释（`user_scripts`、`kUserScriptsAllowed` / `extensions.userScripts` pref 名），确认 pref 键名，直接在 seed 的 Preferences 里核对该键是否存在且为 true。

## 修复方向（任选证据支持的那条）
- 二次校验失败 → 修选择器/等待；成功但不执行 → 修开关持久化（必要时 fc-chrome 启动后用 CDP 再点一次开关，把它做成运行时兜底而不只靠 seed）；`@match` 问题 → 改脚本头。
- 所有改动：COMMON `fc-chrome/`（`git commit -- <文件>`，不动 `cmd/localverify`）；userscripts 若改 → `build:cloud` + `upload:cloud` + commit。完成后本地容器里 `localverify -mode tm` 对桩页跑通作为交付证据；线上复测由主控做。

## 交付
≤500 字写入 `99-notes.md`「角色 14」小节：根因（带日志/DOM 证据）、改动文件、本地验证输出、是否需要重新出 seed、commit hash。
