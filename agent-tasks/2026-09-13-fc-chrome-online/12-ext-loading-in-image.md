# 角色 12：在生产镜像的 Chrome 里把 Tampermonkey 真正装进去（本地 docker 内验证，不碰云端）

## 背景
角色 11 实测（见 `99-notes.md`「角色 11」）：品牌版 Google Chrome 149 直接忽略 `--load-extension` / `--disable-extensions-except`
（Chrome 137+ 已移除该能力），所以 `fc-chrome` 的"内置 Tampermonkey + 自动装脚本"路径 1/2 在品牌版 Chrome 上**根本进不了浏览器**。
生产镜像 `registry.cn-hangzhou.aliyuncs.com/1second/fc-chrome:base` **本机已构建好**（ubuntu24.04 + google-chrome-stable 153.0.8010.36 +
`/opt/extensions/tampermonkey/` = Tampermonkey 5.5.0 解包），可直接 `docker run` 做实验。

## 目标
找出一种**在该镜像内可用**的方式让 Tampermonkey 5.5.0 出现在 `Target.getTargets` 里（有 `chrome-extension://dhdgffkkebhmkfjojejmpbldmpobfkfo/…` target），
并且 `fc-chrome` 的 `script=<url>` 自动装脚本（路径 2）能真的把脚本装进去；给出可合入的 Dockerfile/代码改动。

## 候选方案（按序验证，能用就停，全部不行如实报告）
A. **企业策略强制安装（推荐先试）**：镜像里写 `/etc/opt/chrome/policies/managed/tampermonkey.json`：
   `{"ExtensionSettings":{"dhdgffkkebhmkfjojejmpbldmpobfkfo":{"installation_mode":"force_installed","update_url":"<OSS 上的 update.xml>"}}}`。
   `update.xml` 是 Chrome 扩展更新清单（`<gupdate><app appid=…><updatecheck codebase="<crx URL>" version="5.5.0"/></app></gupdate>`），
   crx 用原始 `.crx`（主控本机 scratchpad 有 `tampermonkey.crx`，路径见下），先传到 `oss://osec-deploy-pub/fc-chrome/extensions/tampermonkey.crx` 与 `…/tampermonkey-update.xml`（ossutil 可用）。
   验证：容器内 `google-chrome --headless=new --remote-debugging-port=9222 --user-data-dir=/tmp/p about:blank`，等 10~20 s 后 `curl 127.0.0.1:9222/json/list` 看有没有 TM 的 target；`chrome://policy` 用 CDP 截图/dump 看策略是否生效。
   注意 headless 下策略是否加载、首次安装需要网络（容器内需能访问 OSS 公网域名）。
B. **换 Chrome for Testing**（同内核、保留 `--load-extension`）：`https://googlechromelabs.github.io/chrome-for-testing/` 取与 153 同大版本的 linux64 zip，
   装到 `/opt/chrome-for-testing/`，`CHROME_PATH` 指过去；补齐依赖库（`ldd chrome | grep not found`）。验证同上（用 `--load-extension=/opt/extensions/tampermonkey`）。
C. **Chromium**（ubuntu 24.04 只有 snap，容器内不可用；如有 deb 源如 `xtradeb` PPA 或 `chromium` 静态包可试，否则跳过）。

## 然后
- 用能加载扩展的那套配置，在容器里跑完整 `fc-chrome`（`docker run … -p 19000:9000 -e CHROME_PATH=… -e INSTANCE_RECYCLE_EVERY=0 fc-chrome:app`，
  app 镜像若没有就先 `make image-app`——本机 docker 构建可用，只是 push 不行）；`/health` 的 `tampermonkey` 非 null；
  用 `go run ./cmd/localverify -mode tm`（角色 20 已加 `-mode`，若尚未合入就临时改一行不带 `inject=1`）+ 本地 http.server 提供 `userscripts/dist-cloud/kdoc-cloud.user.js`，
  验证 `tryInstallViaTampermonkeyOptionsPage`：现场 `Runtime.evaluate` dump Tampermonkey options 页 DOM，把选择器改对，处理"确认安装"页（单独 target）。
  成功判据：安装后打开 `sample.html#taskNonce=x`（不带 inject）能收到 `[[DOC_SPIDER]]`。
- 改动落到 COMMON `fc-chrome/`：`image/Dockerfile`（策略文件或 Chrome for Testing）、`tampermonkey.go`（选择器/确认页）、`README.md`（如实写清哪条路径可用、依据）。
  `go build ./... && go vet ./...`；`git commit -- fc-chrome/<文件>`；push。**不要动 `cmd/localverify`**（角色 20）；不要 `docker push`、不要 `s deploy`。

## 路径
- crx 原件：`/tmp/claude-1000/-home-peterq-dev-projects-peterq-agent-memory-osec-spider/026b04c5-d598-4589-85fd-c28a13b7d650/scratchpad/tampermonkey.crx`
- 解包目录：同目录 `tm/`；zip：同目录 `tampermonkey.zip`
- 扩展 ID：`dhdgffkkebhmkfjojejmpbldmpobfkfo`（Chrome 应用店 Tampermonkey）

## 交付
≤500 字写入 `99-notes.md`「角色 12」小节：A/B/C 各自实测结论与证据（target 列表/截图路径）、最终方案、Dockerfile/代码改动、OSS 新增对象、commit hash、仍未解决的点。
