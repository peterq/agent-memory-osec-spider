# 角色 10：FC 基础设施 —— Tampermonkey 包 → 镜像 → 部署 → 共用域名加路由

## 顺序与要求

### 1. Tampermonkey 扩展包上传 OSS
- 拿到 Chrome 版 Tampermonkey（稳定版）的 crx：优先 Chrome Web Store 的 crx 下载端点
  （`https://clients2.google.com/service/update2/crx?response=redirect&prodversion=<本机 chrome 版本>&acceptformat=crx2,crx3&x=id%3Ddhdgffkkebhmkfjojejmpbldmpobfkfo%26uc`），
  不通就用 tampermonkey.net 官方发布页；再不通搜阿里云/其他镜像。**记录来源 URL 与版本号**。
- crx3 → zip：crx 文件 = 头部（magic `Cr24` + version + 头长度 + 头）+ 标准 zip，剥掉头部即得 zip；用 `python3` 处理并用 `unzip -t` 校验，确认根目录有 `manifest.json`。
- `ossutil cp -f tampermonkey.zip oss://osec-deploy-pub/fc-chrome/extensions/tampermonkey.zip`，然后 `curl -sI https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/extensions/tampermonkey.zip` 确认公网可读（200）。

### 2. 用真实扩展包核对/修正 `tampermonkey.go` 的选择器（本地，必须做）
- 解包到本机某目录，`make local CHROME_PATH=/usr/bin/google-chrome-stable` 起 fc-chrome，
  让 `tampermonkeyDir()` 指到解包目录（看 `tampermonkey.go:19` 的探测逻辑，必要时加环境变量 `TAMPERMONKEY_DIR` 覆盖，缺省值不变）。
- 用 `go run ./cmd/localverify` 或自写 CDP 客户端，以 `display=1`（本机有界面就用，没有就 headless + `Page.captureScreenshot` 存图看）验证
  `tryInstallViaTampermonkeyOptionsPage` 是否真的把脚本装进去了：打开 `chrome-extension://<id>/options.html`，看"已安装脚本"列表里有没有。
  选择器不对就改到对；Tampermonkey 若弹"确认安装"页，要在代码里把它也点掉（找 install 页面的 target，`Runtime.evaluate` 点确认按钮）。
  **如果 Tampermonkey 在 `--headless=new` 下根本不加载**（`chrome://extensions` 空），如实记录并说明生产只能走 `inject=1`，不要硬凑。
- 顺手确认 `/health` 的 `tampermonkey` 字段返回真实版本号。
- 改动写单测能覆盖的就补；`go build ./... && go vet ./... && go test ./...` 通过。

### 3. 镜像构建与推送
- `make image-base`（会从 OSS 拉第 1 步的包，构建日志里**不能**出现 `WARNING: 未拿到 TAMPERMONKEY_URL`），`make image-app`，`docker push` 两个 tag。
- `docker run --rm -e CHROME_PATH=/opt/google/chrome/google-chrome -e INSTANCE_RECYCLE_EVERY=0 -p 19000:9000 <app 镜像>` 本地起一次，`curl 127.0.0.1:19000/health` 看 `tampermonkey` 非 null、Chrome 版本正常，然后停掉。

### 4. 部署函数
- `cd fc-chrome && s -t s.yaml fc-chrome deploy -y`（access `shaka_osec`）。s.yaml 里 `fc-chrome-domain` 是 `domainName: auto`——允许它生成系统测试域名，但**主用域名是第 5 步的共用域名**。
- 部署后 `curl https://<auto 域名>/health` 与 `wscat`/CDP 客户端连 `/chrome?inject=1&script=<任意 OSS 上的 user.js>` 各一次，证明函数活着、WebSocket 握手成功。
- 若角色权限不足（NAS/日志/镜像拉取），按 s 的报错去搜阿里云文档补授权，记录改了什么。

### 5. 共用域名 `fc-resource-node-api.krzb.net` 加路由
- 先查现状：`s cli fc3 ...`/`aliyun fc GET /2023-03-30/custom-domains/fc-resource-node-api.krzb.net`（FC 3.0 OpenAPI `GetCustomDomain`），
  记下现有 `routeConfig.routes`（path、functionName、qualifier）、`certConfig`、`protocol`、`tlsConfig`——**打码后写进 99-notes.md**，这是回滚依据。
- 新增路由 `path: /cdp3/*` → `functionName: nc-app-prod-cdp3`，并配 `rewriteConfig`（FC 3.0 文档：自定义域名 → 路由 → 重写规则，`wildcardRules: [{match: "/cdp3/*", replacement: "/$1"}]`），
  让函数收到 `/chrome`、`/health`。用 `UpdateCustomDomain` 提交**完整**的 routes（老的 `/*` 原样保留，且顺序上新路由在前或确认 FC 按最长前缀匹配——查文档写明）。
  如果 FC 3.0 该域名不支持重写：改 `handler.go`，新增环境变量 `PATH_PREFIX`（如 `/cdp3`），命中即剥掉前缀再路由，`s.yaml` 加该环境变量并重新 deploy。
- 验证：`curl https://fc-resource-node-api.krzb.net/cdp3/health` 200 且 `tampermonkey` 非 null；**同时** `curl https://fc-resource-node-api.krzb.net/health`（老路由）行为与改之前一致（改之前先记一次响应作对照）。
  再用 CDP 客户端连 `wss://fc-resource-node-api.krzb.net/cdp3/chrome?inject=1&script=<OSS 脚本 URL>` 握手成功（脚本 URL 若角色 20 还没传，先用任意可访问的 `.user.js`，例如把本地 `userscripts/dist-cloud/kdoc-cloud.user.js` 临时传到 `oss://osec-deploy-pub/fc-chrome/userscripts/kdoc.user.js`——这正是最终路径，直接传即可）。

### 6. 文档与提交
- 更新 `fc-chrome/README.md`：「需要人工做的事情」改为「上线记录（2026-09-13）」——域名、路径、镜像 tag、Tampermonkey 版本、选择器验证结论、回滚方法（删路由/回滚镜像 tag）；
  `s.yaml` 若改过一并提交。`Makefile` 里如有硬编码 auto 域名也更新。
- COMMON 仓库 `git commit -- fc-chrome` 并 push。

## 交付
按 00-shared.md 写入 `99-notes.md`「角色 10」小节：每步的证据（命令 + 关键输出打码）、最终可用的两个地址（`https://fc-resource-node-api.krzb.net/cdp3/…` 与 auto 域名）、
Tampermonkey 版本与自动装脚本三条路径各自的**实测结论**、遇到的权限/文档问题与解法。
