# 角色 13：构建期预热「已装好 Tampermonkey 的 Chrome profile」+ 用真实 UI 核对路径 2 选择器（本地 docker 内）

## 背景
角色 12（见 `99-notes.md`）已证明：镜像里 `/etc/opt/chrome/policies/managed/tampermonkey.json`（`force_installed` + OSS 上的 update.xml/crx）能让 headless Chrome 153 装上 Tampermonkey 5.5.0；
但**全新 profile 到扩展就绪耗时 15 s~180 s 不定**，而 `fc-chrome` 每次 `/chrome` 都建全新临时 profile 并立刻跑 `installUserScript`，导致路径 2 100% 报"未找到 Tampermonkey"。
COMMON 当前 HEAD 含角色 11（`57652d7`）、角色 12（`cdb4e62`）改动；本机已有重建好的 `fc-chrome:base`/`:app` 镜像（含策略文件）。

## 要做
1. **构建期预热 profile**：`image/Dockerfile` 末尾新增一步——在构建容器里起 `google-chrome --headless=new --user-data-dir=/opt/chrome-profile-seed --remote-debugging-port=9222 about:blank`，
   轮询 `curl 127.0.0.1:9222/json/list` 直到出现 `chrome-extension://dhdgffkkebhmkfjojejmpbldmpobfkfo/` target（上限 300 s，超时构建失败而不是静默通过），再优雅退出 Chrome（`Browser.close` 或 SIGTERM 等待），
   删除 `SingletonLock`/`SingletonSocket`/`SingletonCookie`、`*/Cache*`、`*/Code Cache` 等无用大目录，保留 `Default/Extensions`、`Default/Preferences`、`Default/Secure Preferences`、`Local State`、`Default/Local Extension Settings` 等。
   构建需要访问 OSS 公网（本机 docker 可以）。注意 Docker 构建时无 `--network=host` 也能出网。
2. **运行时复制 seed**：`chrome.go` 里建临时 profile 时，若 `CHROME_PROFILE_SEED`（缺省 `/opt/chrome-profile-seed`）目录存在，`cp -a` 到临时目录再启动；不存在则维持现状。首次 Tampermonkey 就绪等待：`installUserScript` 前用 `Target.getTargets` 轮询最多 `TM_READY_TIMEOUT_SEC`（缺省 20）等 TM target 出现。
3. **核对路径 2 选择器**：镜像里跑 `fc-chrome`，`go run ./cmd/localverify -mode tm -script <本地或 OSS 脚本> -page <sample.html>`，现场 `Runtime.evaluate` dump `options.html#nav=utils` 的 DOM，把 `tryInstallViaTampermonkeyOptionsPage` 的输入框/按钮选择器改对；
   Tampermonkey 会弹独立的"安装脚本"确认页（新 target，URL 含 `ask.html` 或类似）——找到它并点"安装"；再确认脚本真的进了已安装列表。
   成功判据：**不带 inject=1**，打开 `sample.html#taskNonce=x` 收到 `[[DOC_SPIDER]]`。若 Tampermonkey 5.5 的 UI 无法用 CDP 稳定驱动，试备选：Tampermonkey 支持 `@match` 脚本通过 **策略 `ExtensionSettings` 的 managed storage / Tampermonkey 的 "config" 导入** 或 **直接打开 `.user.js` URL 触发安装页**（Chrome 打开 `*.user.js` 时 TM 会拦截并弹安装页，只需点"安装"），选最稳的一条。
4. 测 `inject=1` 路径不回归；`/health` 增加 `profileSeed: true/false` 字段（可选）。
5. `go build ./... && go vet ./... && go test ./...`；README 更新三条路径实测结论与新环境变量；`git commit -- fc-chrome/<文件>`（不动 `cmd/localverify`），push。
   **不 docker push、不 s deploy**（主控负责：镜像要经 jenkins 中转）。本机 `make image-base BASE_FROM=registry.cn-hangzhou.aliyuncs.com/1second/app-cdp:chrome && make image-app` 构建通过即可。

## 路径
- 云端脚本 OSS：`https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/userscripts/kdoc.user.js`（角色 20 可能还在更新，内容以此为准）
- 线上函数（只读参考，不要改）：`https://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou.fcapp.run/health`

## 交付
≤500 字写入 `99-notes.md`「角色 13」小节：seed 预热耗时与镜像增量、运行时就绪耗时（3 次实测）、路径 2 最终做法与证据、commit hash、未解决项。
