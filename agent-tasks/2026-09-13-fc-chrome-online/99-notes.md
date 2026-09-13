# 过程记录（各角色追加自己的小节；主控只读本文件）

## 主控（代角色 10）—— 过程记录

- Tampermonkey 5.5.0（MV3）crx 取自 Chrome 应用店（prodversion 149），剥 crx3 头得 zip（1.7 MB，unzip -t 无错），已传 `oss://osec-deploy-pub/fc-chrome/extensions/tampermonkey.zip`，公网 HEAD 200。
- docker hub（ustc 镜像源）拉 `ubuntu:24.04` 失败 → `image/Dockerfile` 加 `ARG BASE_FROM`，以本机旧基础镜像 `1second/app-cdp:chrome`（ubuntu24.04+chrome131）作底；旧镜像残留的 google-chrome apt 源因 Google 轮换签名 key 报 NO_PUBKEY，Dockerfile 先删该源再 apt。
- 现有域名 `fc-resource-node-api.krzb.net`（`s krzb info` 只读）：HTTP,HTTPS，anonymous，WAF off。路由：`/nc-app-image-render-api-test/*`→测试函数；`/*`→资源节点 API 函数（带版本 qualifier）；`/chrome`→`nc-app-prod-cdp2`；`/proxy`、`/check`→`nc-app-prod-cdp-driver`。计划新增 `/cdp3/*`→`nc-app-prod-cdp3`，其余原样保留。

## 角色 11 —— 本地验证 Tampermonkey 自动装脚本路径

用主控给的真实 Tampermonkey 5.5.0(MV3)解包目录本地实测三条路径，改了 `fc-chrome/tampermonkey.go`（新增 `TAMPERMONKEY_DIR` 环境变量、修了一个真实 bug）与 `README.md`，commit `57652d7` 已 push（未碰 `Makefile`/`cmd/localverify`/`image/Dockerfile`，那是角色 20 在改）。

| 事项 | 结果/证据 |
|---|---|
| `TAMPERMONKEY_DIR` 支持 | `tampermonkeyDir()` 改为 `firstNonEmpty(os.Getenv("TAMPERMONKEY_DIR"), tampermonkeyBaseDir)`，缺省行为不变 |
| `/health` | `TAMPERMONKEY_DIR=<解包目录> make local` → `curl 127.0.0.1:9000/health` 返回 `"tampermonkey":"5.5.0"` |
| **关键发现**：本机 Chrome 拒绝加载扩展 | 本机 `google-chrome-stable`(149.0.7827.114) 手动加 `--enable-logging=stderr --v=1` 直接打出 `WARNING: --load-extension is not allowed in Google Chrome, ignoring.`（`--disable-extensions-except` 同样被拒），`--headless=new` 与 `display=1`（真实 X `:1`）结果一致；`Target.getTargets` 全程只看到 4 个内置 component 扩展（应用商店/PDF Viewer/Hangouts/Network Speech），Tampermonkey 从未出现过。**不止 Tampermonkey，`ext=` 扩展加载在本机整体验证不了**，生产镜像 Chrome 是否有同样限制需部署后复查 |
| **修的真实 bug** | 旧 `tryInstallViaTampermonkeyOptionsPage` 取"第一个 `chrome-extension://` target"，本地复现它真的选中了内置 Google Hangouts(`nkeimhogjdpnpccoofpliimaahmaaome`)当 Tampermonkey，打开其 `options.html` 触发 Chrome `content_verify_job` 报错、`ERR_FILE_NOT_FOUND`——不是选择器问题。已加 `findTampermonkeyExtensionID`：枚举 `chrome-extension://` target，逐个 `chrome.runtime.getManifest().version` 比对 `tampermonkeyVersion()`，命中才用。修复后不再误开 Hangouts，报错变为清晰的"未找到 version=5.5.0 的 Tampermonkey" |
| 路径2 选择器 | **仍未验证**：扩展进不了浏览器，Utils 面板渲染不出来；`options.html` 确认是空壳(`<script src=editor.js>`+`extension.js`)，真实 UI 由高度混淆 JS 拼出，只能等扩展能加载后 `Runtime.evaluate` dump DOM 现场核对，本轮没条件做 |
| 路径3(`inject=1`) | 复测通过，未被改动影响：`go run ./cmd/localverify -script http://127.0.0.1:8899/kdoc-cloud.user.js -page http://127.0.0.1:8898/sample.html` 打到 `[[DOC_SPIDER]]{"event":"start"}` |
| `go build/vet/test` | 全部通过（无测试文件） |
| README | 「Tampermonkey 三条路径实现程度」章节按实测结论重写，环境变量表加 `TAMPERMONKEY_DIR` |
| 清理 | `bootstrap`/本地 server/两个 `python3 -m http.server`/所有测试用 chrome 进程与 `/tmp/cdp-*`、`/tmp/manualchrome-profile*` 已 kill/删除确认 |
| commit | `57652d7`（COMMON 仓库），已 push |

**给主控/角色40的风险提示**：路径1/2 依赖"Chrome 能通过命令行加载未打包扩展"这个前提，本机品牌版 Chrome 完全不成立（非 headless 特有）。生产镜像部署后第一件事应重新验证镜像内 Chrome 是否也拒绝 `--load-extension`；若也拒绝，路径1/2 需要整体换方案（如换 Chromium 或走真正的企业策略预置），doc-crawler 侧必须硬依赖 `inject=1`，不能只当"更可靠的默认值"。

## 角色 12 —— 生产镜像内验证企业策略强制安装 Tampermonkey

方案 A(企业策略)验证通过，方案 B/C 未试（A 已达标，按"能用就停"）。commit `cdb4e62`（COMMON，已 push），改了 `image/Dockerfile`+`README.md`（未碰 `Makefile`/`cmd/localverify`，角色20 在改）。crx/update.xml 已传 OSS。本机重建 `fc-chrome:base`/`:app`（未 push/未 deploy）。

| 事项 | 结果/证据 |
|---|---|
| crx 扩展 ID 校验 | 解析 crx3 `signed_header_data.crx_id` 算出 `dhdgffkkebhmkfjojejmpbldmpobfkfo`，与需求一致 |
| OSS 新增对象 | `oss://osec-deploy-pub/fc-chrome/extensions/{tampermonkey.crx, tampermonkey-update.xml}`，容器内 wget 200 |
| **A 验证通过** | 镜像内 `/etc/opt/chrome/policies/managed/tampermonkey.json`(`force_installed`) + headless chrome，`curl :9222/json/list` 三次独立证据：`chrome-extension://dhdg.../background.js` service_worker、扩展自开欢迎页(`tampermonkey.net?...&ext=dhdg`)、`Target.createTarget` 打开 `options.html#nav=settings` 渲染出真实 Settings 页 |
| **新风险(未解决)** | 全新 profile 到扩展就绪耗时不定：3 次实测 ~15s/~98s/180s 全程未出现；`fc-chrome` 每次 `/chrome` 建全新 profile 且连上就同步跑 `installUserScript`，`go run ./cmd/localverify -mode tm` 复现 100% 报"未找到 Tampermonkey"（不是选择器问题，是还没装完）。建议：构建期预热一份已装好 TM 的 profile 打进镜像，运行时复制而非新建——本轮未实现 |
| 路径2选择器 | 仍未验证：所有实测里扩展都没装完，从未拿到可交互 UI |
| `/health`(容器) | `docker run -d ... fc-chrome:app` → `{"tampermonkey":"5.5.0",...}` |
| `go build/vet` | 通过 |
| 清理 | 所有测试容器(`tm-policy-test`/`fc-chrome-test`)、本地 http.server(8899)、bootstrap 二进制均已删/kill 确认；未动其他角色的进程(如 06:54 起的本地 `bootstrap`) |

给主控/后续角色：方案 A 可合入，但**路径1/2 在当前架构下暂不能替代 `inject=1`**；doc-crawler 仍需硬依赖 `inject=1`。profile 预热与选择器验证留待后续角色。

### 主控 —— 函数已部署；域名路由变更被 auto 分类器拦截（需用户执行）
- `s deploy` 成功：函数 `nc-app-prod-cdp3`（custom-container，镜像 `1second/fc-chrome:app` digest `6507930f…`，base digest `8513a26d…`，Chrome 153.0.8010.36 + Tampermonkey 5.5.0）。
  系统域名 `https://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou.fcapp.run`（VPC：`…cn-hangzhou-vpc.fcapp.run`）；auto 域名 `nc-app-prod-cdp3.fcv3.1074692547105102.cn-hangzhou.fc.devsapp.net`（HTTP）。
  `/health` → `{"cacheEntries":0,"chromeVersion":"Google Chrome 153.0.8010.36","ok":true,"tampermonkey":"5.5.0"}`（冷启动首个请求 >60 s 超时，第二次 7.7 s）。
- 镜像走的是「本机构建 → docker save → rsync 到 osec-jenkins → docker load → push」：本机 ACR 登录已失效、docker hub 镜像源不可用；jenkins docker 19.03 构建 noble 镜像会 NO_PUBKEY（gpg 需新内核 syscall），只能 load 现成镜像再 push；app 层（仅 COPY bootstrap）可在 jenkins 直接 build。
- **共用域名加路由被分类器拦（DNS/Domain/Cert Changes）**。已备好 `agent-tasks/2026-09-13-fc-chrome-online/domain-krzb-s.yaml`（现有 5 条路由原样 + 新增 `/cdp3/*`→`nc-app-prod-cdp3` + `wildcardRules /cdp3/*→/$1`；**故意不写 certConfig**——fc3-domain 组件只把 props 里有的字段放进 UpdateCustomDomain，证书保持不变；plan 里显示的 `- certConfig` 只是本地/远端 diff 视图）。用户执行：
  `cd agent-tasks/2026-09-13-fc-chrome-online && s -t domain-krzb-s.yaml krzb deploy -y`，然后 `curl https://fc-resource-node-api.krzb.net/cdp3/health`。
  改前基线（HTTPS 全部 ssl_verify=0）：`/`=404、`/check`=500、`/nc-app-image-render-api-test/`=500、`/cdp3/health`=404。

## 角色 20 —— 云端油猴脚本上传 + 本地/线上全链路预演（找到并修复 3 个真实 bug，端到端跑通）

**结论：本地 fc-chrome 与主控已部署的线上 `nc-app-prod-cdp-wmmmpvnmqb` 两个环境都用真实金山文档 `https://www.kdocs.cn/l/cdXYaQ5EOakI` 完整跑通**：`start` → 心跳/progress → `result`（193 条 quark 链接 + docMtime + version），非推测。

### 1. OSS 脚本
- URL：`https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/userscripts/kdoc.user.js`
- 最终 md5（本地构建与公网内容一致，已 `curl | md5sum` 核对）：`ad3fb600bd47da5071f1f3cb64178d69`
- Content-Type 已是 `text/javascript`，无需 `ossutil set-meta`。
- commit：userscripts 仓库 `e0e9c20`（`src/cloud/kdocCloud.ts`），已 push。

### 2. 排查过程中发现并修复的 3 个真实 bug（不是推测）
1. **nonce 截断**：`taskNonce` 正则字符集是 `[a-zA-Z0-9.]+`，doc-crawler 用 uuid 做 nonce（带 `-`），"online-inject-1" 会被截断成 "online"（主控线上实测发现，与我本地独立发现的现象一致）。改成 `taskNonce=([^&]+)`。
2. **SSO 重定向丢 nonce**：`www.kdocs.cn/l/*` 匿名访问会经过 `www.kdocs.cn → account.kdocs.cn → account.wps.cn → account.kdocs.cn → www.kdocs.cn` 的重定向链，最终落地页 `location.hash` 被冲掉（不是登录墙，落地页 `window.__WPSENV__`/`window.APP`/`getActiveSheet()` 都现成可用，用 CDP 直接 eval 验证过）。用 `Domain=.kdocs.cn` 的跨子域 cookie（+ localStorage 兜底）把 nonce 从中间跳带到落地页，且**只在真正的文档域名**（与 `@match` 一致的 `www.kdocs.cn`/`365.kdocs.cn`）才消费 nonce、开始解析，避免在 SSO 中间跳提前消费掉。
3. **根因（解释了"只有 start、之后彻底沉默"）**：金山文档自己的前端代码加载后会**整体替换 `window.console.log`**（大概在页面落地后 1~2 秒内）。我们的 `emit()` 直接调 `console.log` 时，前几百毫秒（`start` 事件）还是原生实现、CDP 能看到；之后所有 `progress`/`result`/`error` 全部悄悄进了被替换后的函数，CDP 完全看不到——表现为"整个执行环境卡死/无响应"，但用独立心跳定时器 + `Runtime.evaluate` 直接读全局计数器验证过：JS 其实一直在正常跑（心跳计数器持续增长），只是回传通道被换了。**修法**：脚本最开头（比页面任何脚本都早，因为是 `document-start` 主世界注入）就 `console.log.bind(console)` 抓一份原生引用存好，全程只用这个引用回传，不再经过随时可能被替换的 `window.console.log` 属性。
   - 这个发现对**所有**用 console.log 回传协议的云端脚本都有意义，不止金山文档；建议记进 knowledge 供以后其它站点复用。

### 3. 加固（同一批 commit）
- 总 watchdog：90 秒内没有终态（result/error）就主动回传一条 `permanent:false` 的 error（可重试），并用 `terminalSent` 去重，满足契约"失败/超时也要有终态,不要静默"。
- `copySheet` 行遍历循环加了无条件的"每 500 行强制让出一次事件循环"（`await new Promise(r=>setTimeout(r,0))`），防止 `getDbSheetViews()`(数据库视图/超级表) 场景下 `usedRange` 被放大到整表物理行列上限、真实数据稀疏散布导致 `continuousEmptyRow` 长期到不了 1000 的退出条件时，主线程被完全占满、连 watchdog 的 `setTimeout` 都没机会触发。
- 独立心跳（15 秒一次，带递增 `tick` 序号），不依赖 copySheet 内部"每 200 行"的节奏，给 doc-crawler 更及时的存活证据。
- nonce 改为**在真正拿到终态时才消费**（原来是"读到就立刻清"），防止误判为"已消费"后又因为环境抖动等原因需要重新走一遍。

### 4. 本地预演 console 输出（截断）
```
[[DOC_SPIDER]]{"nonce":"final-confirm-...","event":"start"}
[[DOC_SPIDER]]{"nonce":"...","event":"progress","scanned":96,"heartbeat":true,"tick":1}
[[DOC_SPIDER]]{"nonce":"...","event":"progress","scanned":200}
[[DOC_SPIDER]]{"nonce":"...","event":"progress","scanned":400}
[[DOC_SPIDER]]{"nonce":"...","event":"progress","scanned":574}
[[DOC_SPIDER]]{"nonce":"...","event":"result","ok":true,"docType":"kdocSheet","links":[...193条...],
  "seq":0,"final":true,"docMtime":"2026-06-25T06:28:03.000Z",
  "version":"dac41be541aec20743b9e871a15a1021de95406d","linkCount":193}
```
本地 fc-chrome（`make local`）与线上 `wss://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou.fcapp.run/chrome` 两个环境各跑通 ≥1 次，全流程约 25~30 秒（含 SSO 重定向 ~2.5 秒）。

### 5. `cmd/localverify` 新用法（commit `dbacbce`，COMMON 仓库，已 push；只改了 `cmd/localverify/main.go`，未碰角色 10 在改的 `tampermonkey.go`/`handler.go`/`README.md`/`s.yaml`/`Makefile`/`image/Dockerfile`）
```
go run ./cmd/localverify \
  -fc ws://127.0.0.1:9000/chrome \        # 或线上 wss://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou.fcapp.run/chrome
  -script <脚本url> -page <文档url> -nonce <随便一个uuid> \
  -mode inject|tm \   # 新增, 默认 inject(原行为不变); tm=不带 inject=1, 考验 Tampermonkey 自动安装路径
  -timeout <秒>        # 新增, 默认 120, 等待 [[DOC_SPIDER]] 终态的最长时间
```
退出码：`0`=拿到终态协议输出，`2`=WS 握手失败，`3`=超时未拿到终态。
**顺手修了一个 bug**：原来请求 fc-chrome 时 `timeoutSec` 写死 `60`，真实文档解析经常超过这个值，Chrome 实例会在拿到最终结果前被提前 kill（我本地最初几轮测试就是被这个坑绊住，一度误判为"整个环境卡死"）。现在跟着 `-timeout` 动态算（`-timeout` + 30 秒余量）。

### 6. 三处回填位置（只列位置，未改，等主控/角色 30 拿到最终确认域名后填；线上域名已知是 `wss://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou.fcapp.run/chrome`，域名路由 `/cdp3/*` 上线后建议改用 `wss://fc-resource-node-api.krzb.net/cdp3/chrome`）
1. `nc-js/admin/login3rd/src/task/task.ts:18` —— `'prod-v3': 'wss://TODO-nc-app-prod-cdp3-真实域名未上线/chrome',` 改成真实域名，不删其它条目、不改默认选中项（第 387 行仍是 `eps['prod-v2']`）。
2. `nc-js/apps/cdp-driver/s.yaml:42` —— 注释状态的 `# CDP_ENDPOINT: "wss://<nc-app-prod-cdp3-真实域名>/chrome"`，取消注释并填真实值即可生效（`src/main.ts` 已读 `process.env['CDP_ENDPOINT']` 优先）。
3. `osec-spider-go/config/config.go:518-527` —— `DocCrawlerConfig.FcEndpoint`/`FcEndpointPublic` 两个字段目前**只有 yaml tag 和文档注释，仓库里还没有给它们赋默认值的代码**（没找到 `applyDefault`/`Get()` 里对应的赋值语句，大概率要等角色 41 的 `services/doc_crawler` 落地时才会一起写上）；回填时应在赋默认值的地方把 `fc_endpoint` 指向 VPC 内网域名 `wss://nc-app-prod-cdp-wmmmpvnmqb-vpc.cn-hangzhou.fcapp.run/chrome`（或 `/cdp3/*` 路由上线后的等价内网地址）、`fc_endpoint_public` 指向公网系统域名，而不是只改注释。

### 7. 清理确认
- 本机临时起的 `fc-chrome` local server（`make local`，多次重启，最后 pid 1221302/1221303）已 kill；一个因早前 `kill -9` 强杀导致孤儿的本机 chrome 进程（pid 1176976/1177013）已额外清理确认。
- `/tmp/manual-chrome-profile*`、`/tmp/fc-chrome-local*.log`、诊断用临时 python 脚本均在 scratchpad 目录内，未污染仓库。
- 未 `pnpm build`、未动 NC-JS/SPIDER 任何文件。
- 用过在线 FC 端点做验证（主控已部署，未新建/未重新部署任何函数）。

## 角色 30 —— 三处回填新 FC 地址（代码改动，不部署）

| 事项 | 结果/证据 |
|---|---|
| NC-JS `admin/login3rd/src/task/task.ts:18` | `eps['prod-v3']` 由占位改为 `wss://fc-resource-node-api.krzb.net/cdp3/chrome`（共用域名新路径），注释补系统域名备用地址；默认选中项仍是 `prod-v2` |
| NC-JS `apps/cdp-driver/s.yaml:34-38`、`src/main.ts:10-15` | `CDP_ENDPOINT` 注释占位改为真实系统域名/自定义域名（仍注释、不生效），`main.ts` TODO 改为"新实例已上线，切换时改 CDP_ENDPOINT"；缺省值不变（仍指旧实例 v2） |
| NC-JS 类型检查 | `login3rd`: `pnpm run type-check`（`vue-tsc --build`）通过，无输出；`cdp-driver`: `pnpm exec tsc --noEmit` 报 1 个错误（`main.ts:6` `import { aw } from 'vitest/dist/chunks/...'`），经 `git blame` 确认该行来自 2024-12-26 历史提交，与本次改动（第 10-15 行）无关，未处理 |
| SPIDER `config/config.go:521-524` | `FcEndpoint` 字段注释更新，去掉"尚未部署"措辞，指向 `doc_crawler.go` 的 `applyDefault` |
| SPIDER `services/doc_crawler/doc_crawler.go:38-48` | `applyDefault`：`FcEndpoint` 缺省改为 VPC 内网系统域名 `wss://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou-vpc.fcapp.run/chrome`；`FcEndpointPublic` 缺省改为共用自定义域名新路径 `wss://fc-resource-node-api.krzb.net/cdp3/chrome`（路由变更待用户执行） |
| SPIDER 构建/测试 | `go build ./...` 无输出（通过）；`go vet ./config/... ./services/doc_crawler/...` 无输出（通过）；`go test ./services/doc_crawler/... -count=1` → `ok` |
| commit | NC-JS `89860d8`（main，已 push）；SPIDER `e79c4f6`（master，已 push）。均无 Co-Authored-By |

未做：未碰 userscripts 仓库（不属于本角色范围）；未执行自定义域名路由变更（属主控/用户）；未切换 `cdp-driver` 生产缺省值（按要求保留，切换由用户决定）。

### 主控 —— 共用域名路由已生效 + 线上集成测试(inject 路径)通过（2026-09-13 07:59）
- `s krzb info`：`/cdp3/*` → `nc-app-prod-cdp3` + `wildcardRules /cdp3/* → /$1` 已在线，其余 5 条路由原样；HTTPS 证书未受影响（`ssl_verify=0`）。
  `https://fc-resource-node-api.krzb.net/cdp3/health` → `{"cacheEntries":0,"chromeVersion":"Google Chrome 153.0.8010.36","ok":true,"tampermonkey":"5.5.0"}`；老路径 `/`=404、`/check`=500 与改前基线一致。
- `go run ./cmd/localverify -mode inject -timeout 150 -fc wss://fc-resource-node-api.krzb.net/cdp3/chrome -script <OSS kdoc.user.js> -page https://www.kdocs.cn/l/cdXYaQ5EOakI -nonce krzb-inject-1`：
  握手 5 s → `start` → `progress` 200/244/400/574 → **`result ok:true docType=kdocSheet`（quark 链接列表）**，全程 20 s，退出码 0。nonce 完整（角色 20 修复生效）。
- 待办：Tampermonkey 路径（不带 inject）等角色 13 的 profile 预热方案；随后重建 base/app 镜像 → jenkins 中转推 ACR → `s deploy` → 线上 `-mode tm` 复测。

## 角色 13 —— Chrome profile 预热 + 路径2 选择器核对（找到根因、机制验证通过；构建期自动化本轮未稳定跑通）

commit `cff1561`（COMMON，已 push），改了 `chrome.go`/`tampermonkey.go`/`handler.go`/`Makefile`/`image/Dockerfile`/`README.md`，新增 `cmd/seedprep/`（未碰 `cmd/localverify`）。全部在本机 docker 容器验证，未 push 镜像、未 deploy。

| 事项 | 结果/证据 |
|---|---|
| **关键新发现1：CDP 无法 attach chrome-extension:// target** | 品牌版 Chrome(153.0.8010.36) 对 `Target.attachToTarget` attach 到任意 `chrome-extension://` target（页面/ask弹窗/service_worker 全部一样）一律返回 `{"code":-32000,"message":"Not allowed"}`，与 flatten 参数、是否本连接自建无关。角色12"三项证据"其实没走过 attach。**绕过**：先建 `about:blank` 普通页 attach，再 `Page.navigate` 过去。`tampermonkey.go`(`openExtensionPage`)与`cmd/seedprep`都用这招 |
| 路径2 真实选择器（现场 dump 确认） | Utils 面板输入框 `.updateurl_input`（旧代码猜的 `type=url`/`#url` 全不对），按钮真实文案 **"Install" 不是 "Import"**；点击后独立确认页 `ask.html?aid=...` 上 `input[name=Install].install`；`findTampermonkeyExtensionID` 改为纯 `Target.getTargets` 列表匹配（不再 attach，也不再限定 `service_worker` 类型——同一坑踩了两次） |
| **关键新发现2：Chrome 138+ "Allow User Scripts" 二次授权** | 脚本能自动装进已安装列表，但**默认不会被执行**，除非在 `chrome://extensions/?id=<id>` 手动打开该开关；Chrome 官方博客称目前无企业策略可替代。已用 CDP 找到真实 DOM（`<extensions-toggle-row id="allow-user-scripts">`→shadow root 内 `<cr-toggle id="crToggle">`）并点击验证：点开后**同一 Chrome 实例**内新开 tab 打开 `sample.html` 收到完整 `[[DOC_SPIDER]]` 协议（start+result）。这是手工验证，不是通过构建期种子自动带过去的 |
| profile 预热（`image/Dockerfile`+`chrome.go`） | 构建期起 headless Chrome，新增 `cmd/seedprep` 等 Tampermonkey 就绪 + 点开关，成功后清理（只删 `Default/Cache`/`Code Cache`/`GPUCache` 等**已知安全**目录，全部保留 `Service Worker/`）。**真实踩过的坑**：第一版 `find -iname "*Cache*"` 连 `Service Worker/ScriptCache` 一起删了，复制到运行时的 profile 反复 `DidStartWorkerFail`，表现和没预热一样，排查很久才定位。`chrome.go` 新增 `CHROME_PROFILE_SEED`/`copyProfileSeed`，`/health` 加 `profileSeed` 字段 |
| 路径2 全自动验证（真实 `/chrome` 请求，无人工干预） | `go run ./cmd/localverify -mode tm` 触发的 `installUserScript` 全自动跑完 Utils→ask→dashboard 三步，dashboard 确认脚本进已安装列表，用完的 tab 全部 `closeExtensionPage` 关掉不留残留 |
| 运行时就绪耗时（3 次实测，用 ScriptCache 修复后的种子） | installUserScript 从连上 CDP 到装脚本流程走完：~2s、~2s、~3s，`TM_READY_TIMEOUT_SEC`(缺省20s)基本用不上 |
| **构建期自动化本轮未稳定跑通** | `make image-base` 本轮共测 10 次：接入 `cmd/seedprep`/Allow User Scripts 步骤**之前**的 2 次成功（45s、122s）；接入之后 8 次全部在 300s 超时前失败，日志显示"0 个候选 chrome-extension:// target"（Chrome 从未触发过策略检查）。已加"立即点 chrome://extensions 的 Update 按钮强制触发检查"优化（手工验证过 ~1~5s 内生效），加入后仍有失败。已排除本机→OSS 网络不可达（同会话内 `curl`/`docker run curlimages/curl` 反复验证均能快速拿到 200，仅个别请求超时但重试即通）；怀疑是 Chromium `ExtensionUpdater` 抖动窗口在本环境下可能超过 300s，或本机到 OSS 存在更细粒度的间歇性异常，未能实锤根因 |
| `go build/vet/test` | 全部通过（`test` 无测试文件属正常） |
| 清理 | 所有测试容器（`tm-seed-test*`/`seedprep-test*`/`fc-chrome-e2e`/`updatebtn-test*`）、`python3 -m http.server 8899`、所有 `go run ./cmd/localverify` 进程均已 kill/删除确认；`docker ps -a` 复查无残留 |

**给主控/后续角色的关键结论**：路径1/2 的**机制**（选择器、CDP attach 绕过、Allow User Scripts 开关）已用真实证据证明可行，但"构建期自动预热到位"这最后一公里本轮未能取得一次成功的 `make image-base`（且怀疑与本会话网络状况有关，非必然可复现的代码 bug）。**doc-crawler 侧在有人实际验证过一次成功的 `make image-base`（并确认种子里 Allow User Scripts 真的被点开）之前，必须继续把 `inject=1` 当唯一可信默认通道**，不能因为本轮的选择器/机制验证通过就切换默认值。下一位接手者：换个网络更稳定的时段/环境重跑 `make image-base` 到成功一次，再用 `go run ./cmd/localverify -mode tm`（不夹带任何手工 CDP 操作）确认能自动收到 `[[DOC_SPIDER]]`，即可解除这个限制。详细排查数据见 COMMON `fc-chrome/README.md`「路径2 最终实现 + profile 预热」一节。

## 角色14 —— 线上"装了脚本却不执行"诊断与修复：根因是 closeTarget 后的目标发现竞态，已修复并验证

commit `f429fca`（COMMON，已 push，含重试：首次 push 因 SSH 连 github 超时失败，重跑成功），只改了 `tampermonkey.go`+`README.md`（未碰 `cmd/localverify`/`Makefile`/`image/`）。全部本机 docker 容器验证，**未 push 镜像、未 `s deploy`**。

**先排除的疑点**：本地起线上同款种子容器 `fc-chrome:app-seed`，用桩脚本(`test-tm-path2.user.js`, `@match http://*/sample.html*`)跑 `installUserScript` 路径1/2，**脚本真的装上且真的执行**（收到完整 `[[DOC_SPIDER]] start+result`），换成 `@run-at document-start` 桩脚本同样成功——证明角色13 头号疑点"Allow User Scripts 开关被 profile 复制丢失"**不成立**，种子本身是好的；`Preferences` 里 `granted_permissions.userScripts` 只是 manifest 必需权限的自动授予，不代表开关状态（未定位到开关真正持久化的 pref key，但不影响结论）。

**真正根因（本机 6 次独立探测复现 2 次，33%）**：`tryInstallViaTampermonkeyOptionsPage` 关闭 Utils/ask/dashboard 三个临时 `chrome-extension://` tab 时，旧代码只等 `Target.closeTarget` 的 ack 就认为关闭完成——但"关闭确认"与"从 `Target.getTargets` 摘除"是两件异步的事，残留页可在列表里多待数百毫秒到数秒，且**探测到过 1 次残留排在真正的 `about:blank` 之前**。doc-crawler/`localverify` 都按"握手后第一个 `type=page` 就是目标页"取页，一旦命中这个窗口就会 attach+navigate 错这个即将消失的扩展页，真实页面（kdocs 等）从未被导航——表现正是线上日志里"报告已点击导入"之后再无任何 `[[DOC_SPIDER]]`（连 `start` 都没有）。

| 事项 | 结果/证据 |
|---|---|
| 修复前竞态复现 | 6 次探测 2 次残留（1 次残留 `ask.html`+`options.html#nav=utils` 且排在 `about:blank` 前） |
| 修复方式 | `closeExtensionPage` 新增 `waitForTargetGone` 轮询 `Target.getTargets` 直到目标真正消失(超时 5s 只警告不阻断)；顺手修正 `installUserScript` 里写死的"未做二次校验"误导性日志(dashboard 校验自 `cff1561` 起已存在并生效，只是文案没更新，线上排障时曾被带偏) |
| 修复后验证 | 同一探测脚本连续 5 次，0 次残留；`go run ./cmd/localverify -mode tm`(桩页) 连续 3 次全部约 3s 内拿到 `start`+`result final:true`，退出码 0 |
| 真实 kdocs 页面 | **未做**：本机容器访问 `www.kdocs.cn` 走宿主机代理反复 `SSL handshake failed net_error -100/-101`（与角色13/20 已知本地网络限制一致），60s 内页面从未加载成功，与本次修复无关，不构成反证 |
| `go build/vet` | 通过（无测试文件） |
| 是否需要重新出 seed | **不需要**：只改运行时 Go 代码，profile 种子内容未变，重新编译 `bootstrap` 出新 app 镜像即可 |
| 清理 | 测试容器 `fc14test`/`fc14old`、临时镜像 `app-seed-v2`、`python3 -m http.server 18899` 均已 kill/删除确认；`docker ps -a`/`docker images` 复查无残留 |

**给主控的提示**：这个 33% 概率的竞态可能不是唯一因素（无法排除真实 kdocs 域名多次 SSO 跳转期间是否有额外扩展弹窗、真实网络延迟对窗口大小的影响）。线上重新部署新 `bootstrap` 后建议连续跑 5~10 次 `localverify -mode tm` 而非 1 次；若仍有小概率失败，下一步应在 `handleChrome` 里 `installUserScript` 返回后、WS 升级前整体再 `Target.getTargets` 校验一次，作为比逐个 tab 轮询更彻底的兜底。

### 主控 —— 收尾（2026-09-13 11:45）：两条路径线上全通
- TM 路径根因 = 云端脚本 `@match` 不含 SSO 首跳域名 `account.kdocs.cn`（302 把 `#taskNonce` 带到该跳，脚本从未运行、拿不到 nonce）；用桩脚本 `test-tm-kdocs.user.js`（`@match https://www.kdocs.cn/*` 等）线上证明 TM 注入本身正常并打印了完整跳转链。userscripts `0e9e9c20`→`0e86ba1` 加 `account.kdocs.cn/*`，脚本 md5 `50ce2cfd…`。
- 次要因素：角色 14 的 closeTarget 竞态修复（`f429fca`）；角色 13/主控的 seedprep `/json/list` 解析 bug（`06ab3d9`）；叠层缺策略文件（`5961da6`）。
- 线上镜像 `app-20260913e`（verbose 已关，`TM_READY_TIMEOUT_SEC=40`，timeout 600/2048MB）。终验 11:41：`-mode tm` 9 s、`-mode inject` 5 s 均 `result final:true`。
- 探针/桩：OSS `fc-chrome/test/` 三个文件；OSS 默认域名 html 强制下载，桩页不可直接作页面。临时 `cmd/tmprobe`/`cmd/wsprobe` 已删。
