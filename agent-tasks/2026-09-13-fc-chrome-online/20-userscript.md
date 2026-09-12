# 角色 20：云端油猴脚本上传 + 本地全链路预演 + 回填点准备

## 1. 云端脚本构建与上传
- `cd /home/peterq/dev/projects/peterq/userscripts && pnpm build:cloud`（`vue-tsc --noEmit && vite build --config vite.cloud.config.ts`）。
  若 `vue-tsc` 因仓库里**别人的未提交改动**报错，改成只跑 `vite build --config vite.cloud.config.ts`（不要改任何非 cloud 文件），并在汇报注明。
- 核对产物 `dist-cloud/kdoc-cloud.user.js`：头部 `@match` 只有 `https://365.kdocs.cn/l/*` 与 `https://www.kdocs.cn/l/*`、`@run-at document-start`、无 `@require`、无 Vue/gRPC 字样；
  读 `location.hash` 的 `#taskNonce=`，无 nonce 不做事。
- `pnpm upload:cloud`（= `ossutil cp -f dist-cloud/kdoc-cloud.user.js oss://osec-deploy-pub/fc-chrome/userscripts/kdoc.user.js`），
  然后 `curl -s https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/userscripts/kdoc.user.js | head -20` 确认公网可读且是新内容。
  ⚠️ 角色 10 可能也会往同一路径传一份（同一文件），谁后传都一样，不冲突。
- 顺手确认 `.user.js` 的 Content-Type（`curl -sI`）不影响 Tampermonkey 通过 URL 安装（若返回 `application/octet-stream` 之外的奇怪类型，用 `ossutil set-meta` 设成 `text/javascript`）。

## 2. 本地全链路预演（真实执行）
用本机 Chrome 跑一遍 `fc-chrome/README.md`「本地验证做了什么」的链路，但页面换成**真实金山文档** `https://www.kdocs.cn/l/cdXYaQ5EOakI`：
- 起 `make local CHROME_PATH=/usr/bin/google-chrome-stable`（`nohup … &`，用完 kill）。
- `go run ./cmd/localverify -fc ws://127.0.0.1:9000/chrome -script https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/userscripts/kdoc.user.js -page https://www.kdocs.cn/l/cdXYaQ5EOakI -nonce local1`
- 期望：拿到 `[[DOC_SPIDER]]{...}`，`nonce=local1`，含解析出的链接数/版本号。拿不到就排查脚本对真实页面的就绪判定（`window.__WPSENV__`、`window.APP`）与超时，
  **修 `src/cloud/kdocCloud.ts`**（不动 PC 版 `src/plugins/kdoc/`），重新 build+upload，直到本地跑通。把最终 console 输出（截断到 500 字）贴进汇报。
- 若文档需要登录才能读：如实记录，换用 `05-doc-fc-contract.md` 里描述的本地 `sample.html` 桩页面证明协议链路，并在汇报里把"真实文档需登录"列为阻塞项交主控。

## 3. 给线上集成测试准备工具
- 给 `fc-chrome/cmd/localverify` 加两个 flag（保持默认行为不变）：
  `-mode inject|tm`（`tm` = 连 `/chrome?script=<url>`，不带 `inject=1`，考验 Tampermonkey 自动安装路径）、`-timeout <秒>`（等 `[[DOC_SPIDER]]` 的最长时间，缺省 120）。
  退出码：拿到协议输出 0，超时 3，握手失败 2，便于脚本化。
- 只改 `cmd/localverify/main.go`；`go build ./... && go vet ./...`；COMMON `git commit -- fc-chrome/cmd/localverify` 并 push。
  **角色 10 同时在改 `fc-chrome/` 其他文件，不要碰 `tampermonkey.go` `handler.go` `README.md` `s.yaml`。**

## 4. 回填点（先备好，域名由角色 10 产出后由主控/角色 30 填）
- 列出三处回填的精确位置（文件:行）与将要写的值的形态：NC-JS `admin/login3rd/src/task/task.ts` `eps['prod-v3']`；NC-JS `apps/cdp-driver/s.yaml` `CDP_ENDPOINT`（只加注释/占位，不部署）；
  SPIDER `config/config.go` `DocCrawlerConfig` 的 `fc_endpoint`/`fc_endpoint_public` 缺省值（找 `applyDefault`/`Get()` 里给缺省值的地方）。写进 99-notes.md，不要现在改。

## 交付
按 00-shared.md 写入 `99-notes.md`「角色 20」小节：OSS 脚本 URL 与 md5、本地预演的 console 输出、`localverify` 新用法、三处回填位置。
