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

### 主控 —— 函数已部署；域名路由变更被 auto 分类器拦截（需用户执行）
- `s deploy` 成功：函数 `nc-app-prod-cdp3`（custom-container，镜像 `1second/fc-chrome:app` digest `6507930f…`，base digest `8513a26d…`，Chrome 153.0.8010.36 + Tampermonkey 5.5.0）。
  系统域名 `https://nc-app-prod-cdp-wmmmpvnmqb.cn-hangzhou.fcapp.run`（VPC：`…cn-hangzhou-vpc.fcapp.run`）；auto 域名 `nc-app-prod-cdp3.fcv3.1074692547105102.cn-hangzhou.fc.devsapp.net`（HTTP）。
  `/health` → `{"cacheEntries":0,"chromeVersion":"Google Chrome 153.0.8010.36","ok":true,"tampermonkey":"5.5.0"}`（冷启动首个请求 >60 s 超时，第二次 7.7 s）。
- 镜像走的是「本机构建 → docker save → rsync 到 osec-jenkins → docker load → push」：本机 ACR 登录已失效、docker hub 镜像源不可用；jenkins docker 19.03 构建 noble 镜像会 NO_PUBKEY（gpg 需新内核 syscall），只能 load 现成镜像再 push；app 层（仅 COPY bootstrap）可在 jenkins 直接 build。
- **共用域名加路由被分类器拦（DNS/Domain/Cert Changes）**。已备好 `agent-tasks/2026-09-13-fc-chrome-online/domain-krzb-s.yaml`（现有 5 条路由原样 + 新增 `/cdp3/*`→`nc-app-prod-cdp3` + `wildcardRules /cdp3/*→/$1`；**故意不写 certConfig**——fc3-domain 组件只把 props 里有的字段放进 UpdateCustomDomain，证书保持不变；plan 里显示的 `- certConfig` 只是本地/远端 diff 视图）。用户执行：
  `cd agent-tasks/2026-09-13-fc-chrome-online && s -t domain-krzb-s.yaml krzb deploy -y`，然后 `curl https://fc-resource-node-api.krzb.net/cdp3/health`。
  改前基线（HTTPS 全部 ssl_verify=0）：`/`=404、`/check`=500、`/nc-app-image-render-api-test/`=500、`/cdp3/health`=404。
