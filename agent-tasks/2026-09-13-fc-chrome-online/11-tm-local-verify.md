# 角色 11：用真实 Tampermonkey 5.5.0 包在本地验证/修正 `tampermonkey.go` 的自动装脚本路径（纯本地，不碰云端）

主控已完成：Tampermonkey 5.5.0（MV3，crx 来自 Chrome 应用店）转 zip 并上传到
`https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/extensions/tampermonkey.zip`（公网 200）。
本地解包副本在 `/tmp/claude-1000/-home-peterq-dev-projects-peterq-agent-memory-osec-spider/026b04c5-d598-4589-85fd-c28a13b7d650/scratchpad/tm/`（根目录有 `manifest.json`，`options_page: options.html`）。

## 要做
1. 读 COMMON `fc-chrome/tampermonkey.go`、`chrome.go`、`handler.go`、`README.md`「Tampermonkey 自动装脚本: 三条路径」；读 `05-doc-fc-contract.md` §5。
2. 让 `tampermonkeyDir()` 能通过环境变量（建议 `TAMPERMONKEY_DIR`，缺省值不变）指向上面的解包目录。
3. `make local CHROME_PATH=/usr/bin/google-chrome-stable`（`nohup … &`，用完 kill）起 fc-chrome；`curl 127.0.0.1:9000/health` 看 `tampermonkey` 字段应为 `5.5.0`。
4. 用 `go run ./cmd/localverify`（或自写最小 CDP 客户端）连 `ws://127.0.0.1:9000/chrome?script=<脚本URL>`（**不带 inject=1**），脚本 URL 用
   `https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/userscripts/kdoc.user.js`（若 404 说明角色 20 还没传，先本地 `python3 -m http.server` 提供 `userscripts/dist-cloud/kdoc-cloud.user.js`）。
   验证 `tryInstallViaTampermonkeyOptionsPage` 是否真的把脚本装进了 Tampermonkey：连接后用 CDP 打开 `chrome-extension://<id>/options.html`，
   `Runtime.evaluate` 读已安装脚本列表（或 `Page.captureScreenshot` 存 PNG 用 Read 看图）。
   - 选择器不对就改到对（真实 5.5.0 的 options 页 DOM：`#nav=utils` 里"从 URL 安装"的输入框/按钮；安装确认页是单独 target，要找到并点"安装"）。
   - 若 `--headless=new` 下扩展根本没加载（找不到 `chrome-extension://` target），如实记录，试 `display=1`（本机若无 X 则跳过）并给出结论"生产只能走 inject=1"。
5. 再跑一次 `inject=1` 路径确认没被你的改动弄坏。
6. `go build ./... && go vet ./... && go test ./...`；更新 `README.md` 里三条路径的"实现程度"为实测结论（版本 5.5.0）。
7. COMMON 仓库 `git commit -- fc-chrome/<你改的文件>`（**不要 add `fc-chrome/cmd/localverify`**，角色 20 在改它），push。

## 约束
- 纯本地，不跑 docker、不 s deploy、不改 OSS。禁止 Monitor/后台等待。
- 汇报 ≤400 字写入 `99-notes.md`「角色 11」小节：三条路径各自实测结论、改了哪些选择器/文件、`TAMPERMONKEY_DIR` 用法、commit hash。
