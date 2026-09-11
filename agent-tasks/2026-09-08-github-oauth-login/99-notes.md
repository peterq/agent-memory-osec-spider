# 过程补充（主控追加）

## 1. OAuth App 已创建（2026-09-08）

两个 App 都归 **1second 组织所有**（不是个人账号），组织的第三方应用策略是"Access restricted"，
但 GitHub 明确写着 *Applications owned by 1second always have access*，所以**不需要额外审批**，
组织成员首次登录只会看到常规的授权确认页。

| 用途 | 名称 | client_id | 管理页 |
|---|---|---|---|
| 生产 | `1s-nc-admin (prod)` | `Ov23liVdy3cJkVMV03L1` | https://github.com/organizations/1second/settings/applications/3843686 |
| 本地 | `1s-nc-admin (dev)` | `Ov23lih8tSerxYwqexP5` | https://github.com/organizations/1second/settings/applications/3843687 |

**client_secret 不在本文件里**，见仓库内未纳入 git 的 `.agent-browser/oauth-credentials.txt`。
任何情况下都不要把 secret 写进 git 跟踪的文件、记忆文件或提交信息。

## 2. 已注册的回调地址（决定前端 redirect_uri 只能取这些值）

prod App：
```
https://1s.peterq.cn/
https://1s.peterq.cn/spiderAdmin
https://1s.peterq.cn/spiderAdmin/
https://1s.peterq.cn/pan-share-download
https://1s.peterq.cn/pan-share-download/
```
dev App：
```
http://localhost:5173/   http://localhost:5174/   http://localhost:5175/   http://127.0.0.1:5173/
```

含义：**前端 `redirect_uri` 必须与上面某一项逐字相等**（GitHub 新版表单支持多回调，但未勾选
"Allow wildcard matching"，所以不能靠"路径前缀"匹配）。因此前端取 `location.origin + location.pathname`
时要注意：qiankun 生产环境下子应用的 pathname 就是 `/spiderAdmin` 或 `/pan-share-download`
（带不带尾斜杠都已注册）；本地 dev 服务器下 pathname 是 `/`，端口需为 5173~5175 之一。
如果算出来的 redirect_uri 不在上表内，GitHub 会直接报 `redirect_uri_mismatch`，此时应联系主控
去 App 管理页补一条回调，而不是在前端瞎凑。

## 3. 与 GitHub 的连通性

网关机 osec-res1 实测直连 `https://api.github.com/` 200、耗时 0.5s，无需代理。

## 4. 真实 GitHub 联调结果（主控执行，2026-09-08）

新增工具 `osec-spider-go/tools/ghauthcheck`（不启动网关就能验证 `github_auth` 配置是否可用，
用法见文件头注释）。用 **dev App + 真实 code** 实测三条分支：

| 场景 | 结果 |
|---|---|
| `-org=1second`（账号 peterq 是 active 成员） | 通过：`login=peterq uid=46517975 avatar=https://avatars.githubusercontent.com/u/46517975?v=4` |
| `-org=anthropics`（非成员） | 命中 `ErrNotOrgMember`，文案"不是 … 的 active 成员" |
| 过期/错误 code | 报 `GitHub access_token 交换失败, http status=200, error=The code passed is incorrect or expired.`，未泄露任何凭据 |

**由此暴露一个前端必须处理的事实：`GET /user` 返回的 `name` 可能是空字符串**（该账号就是空），
顶栏与登录态展示不能只显示 `name`，必须回落到 `login`。

另注意：GitHub 的 `access_token` 交换失败时 **HTTP 状态码仍是 200**，错误在 body 里，
Go 侧已按 body 里的 `error` 字段判定（不要改成只看状态码）。

## 5. 验收发现的阻断级问题与返工要求（2026-09-08，网关侧）

**问题**：`services/gateway/gateway.go` 分支 1（githubCode 换票）的三条失败路径
——redirectUri 不在白名单、`ErrNotOrgMember`、其余 GitHub 交换错误——只回了 `code/message`，
没填 `needLogin/githubClientId/githubAuthorizeUrl/githubScope/githubOrg/allowRtcToken`
（这些字段是 `omitempty`，于是回包里整个 key 都不出现）。

**后果**（已确认是真实故障，不是理论问题）：前端 `spidergw.ts` 用
`if (e.needLogin || e.githubClientId)` 判断是否展示登录页，缺字段时会退到"兼容极老网关"的旧分支，
**弹出"请输入管理秘钥"输入框**；网关返回的"需要 1second 组织成员"这类文案也永远到不了界面上。
也就是说：非组织成员完成 GitHub 授权后，看到的不是"你不在 1second 组织"，而是一个要秘钥的弹窗。

**要求的改法**：把这五个登录信息字段的填充从"只在分支 4 手写"改成"只要最终以 403 返回就统一带上"
——在 `defer` 闭包里判断 `app_error.GetCode(err) == 403` 时统一填充；
`needLogin` 可按具体错误细分（例如换票失败也应为 true，用户确实需要重新登录），
但 `githubClientId/githubAuthorizeUrl/githubScope/githubOrg/allowRtcToken` 四项在所有 403 分支上必须一致。
改完补一个针对该行为的单测（构造一次 403 换票失败，断言回包里这些字段都在）。

**同时补一个单测**（验收建议级）：`auth/github_test.go` 缺"access_token 交换阶段 HTTP 200 但 body 里带
`{"error":"bad_verification_code"}`"的用例。现有实现靠 `out.AccessToken == ""` 已覆盖，
但没有断言，将来有人误改成"只看状态码"不会被测试挡住。这是真实会发生的场景（见本文件第 4 节）。

## 6. 对 00-shared 第 5 节的修正

`redirect_uri_prefixes` 的缺省值实现为三项：`https://1s.peterq.cn/`、`http://localhost:`、
`http://127.0.0.1:`，比 00-shared 第 5 节写的多了 `http://127.0.0.1:`。这是**有意的**：
dev OAuth App 注册了 `http://127.0.0.1:5173/` 回调（见本文件第 2 节），以正文为准，不用改回去。

## 7. 真实浏览器联调发现的阻断级问题（2026-09-08，前端）

主控用桩网关(`tools/stubgw`)+ dev OAuth App，在真实 Chrome 里打开 `http://localhost:5173/`
实测：**登录门 `GwLoginGate` 根本没出现，弹出来的还是旧的"请输入管理秘钥"输入框**。
页面上的报错是 `rpc: spider.SpiderRpc/Pong` / `canceled by client: 未登录`。

### 根因（已定位，不是猜测）

网关 403 回包里的 `needLogin/githubClientId/...` 到不了 `useGwClient`。链路是：

1. `rtc-rpc.ts` 的 `authByTokenHandshake` 收到非 0 回包 → `reject(json)`（json 完整）；
2. `initRtcChannel` 的 `handshake(...).catch(e => channelClosed(e))`；
3. `RtcTransportAutoReconnect` 里 `dataChannelPromise.catch(e => transport.cancelAllPendingCalls(e))`；
4. **`RtcTransport.ts:53` `cancelAllPendingCalls` 把 reason 重建成
   `UnaryCallResponse.create({seq, code: reason.code || 400, message: 'canceled by client: ' + err2str(reason)})`**
   —— 它是 protobuf 生成的类型，只留得下 `code` 和 `message`，
   **所有附加字段（needLogin/githubClientId/githubAuthorizeUrl/githubScope/githubOrg/allowRtcToken）在这一步被丢光**。

所以 `mustInitOk` 的 `catch (e)` 里 `e.code === 403` 成立（这也是为什么旧的秘钥弹窗会出现），
但 `e.needLogin || e.githubClientId` 恒为 false，直接落进"兼容极老网关"的分支。
网关侧改得再对也没用，这条路走不通。

### 要求的改法

**不要**去改 `cancelAllPendingCalls`（它是所有 RPC 共用的取消路径，且 `UnaryCallResponse` 是 proto
类型带不了自定义字段）。改成"握手回包不经过 RPC 错误通道，直接回调给上层"：

1. `rtc-rpc.ts`：`authByTokenHandshake(token, onReply?)` 已有成功回调，再加一个失败回调
   （例如 `authByTokenHandshake(token, onReply?, onHandshakeError?)`），在 `reject(json)` **之前**
   用完整的 json 调它；`RtcTransportAutoReconnect` 增加对应的可选透传参数。两个新参数都可选，
   不改既有调用方语义，不动二进制帧格式，不动 `cancelAllPendingCalls`。
2. `spidergw.ts`：用这个新回调驱动登录态——回包 `code===403` 且带 `needLogin||githubClientId` 时，
   在回调里直接设置 `needLogin.value=true` 与 `loginInfo.value={...}`。
   `mustInitOk` 的 `catch` 分支改成**优先看 `needLogin.value`**（回调一定早于 pong 的 reject 触发，
   因为 reject 是 `cancelAllPendingCalls` 引起的、而它发生在 `channelClosed(e)` 之后），
   只有在 `needLogin.value` 为 false 且 `e.code===403` 时才回落到旧的 `uiInputToken()` 弹窗。
3. 顺带修一个小问题：GitHub 回调会带一个 `iss` 参数（实测 `?iss=https%3A%2F%2Fgithub.com%2Flogin%2Foauth`），
   `takePendingGithubCode` 目前只删 `code`/`state`，`iss` 会留在地址栏。一并删掉。

### 怎么自测（不要只靠类型检查）

桩网关已在跑（主控启动，监听 UDP 7542），`admin/spiderAdmin` 的 vite dev server 在 5173。
改完告诉主控，由主控在带 GitHub 登录态的调试浏览器里复测整条链路。
你自己可以先跑 `npx vue-tsc --noEmit -p admin/spiderAdmin/tsconfig.app.json` 与 vitest。

## 8. 联调发现的第二个问题：登录失败原因被重试覆盖（两端各改一处）

**现象**（把桩网关的 `org` 改成一个用户不属于的组织后实测）：GitHub 授权回来 → 网关换票失败并返回
`403 需要 anthropics 组织成员` → **3 秒后前端的下一次重连（这次没有 code）拿到通用的 `403 未登录`，
把登录页上的 message 覆盖掉**。最终用户只看到"未登录"，永远不知道自己是因为不在组织里被拒。
（网关日志能看到两条：`handshake failed: 需要 anthropics 组织成员` 紧跟着 `handshake failed: 未登录`。）

### 网关侧改法（`services/gateway/gateway.go`）

回包结构体加一个字段 `LoginFailed bool \`json:"loginFailed,omitempty"\``。在 `rtcHandshake` 开头
（`json.Unmarshal` 之后）记一个局部变量 `loginAttempt := m.GithubCode != ""`，在 `defer` 里
统一填充那段中补一行：`ret.LoginFailed = loginAttempt && ret.Code == 403`。
含义：这次 403 是"带着 code 来换票但失败了"，而不是"压根没登录"。补一个单测断言：
带 githubCode 的失败回包 `loginFailed=true`，不带 code 的未登录回包 `loginFailed` 不出现。

### 前端改法（`spidergw.ts` / `GwLoginGate.tsx`）

- 新增一个**粘性**的 `loginError` ref：握手回包 `loginFailed` 为真时记下它的 `message`，
  **之后的普通"未登录"403 不得覆盖它**；只在用户再次点击"使用 GitHub 登录"（`startGithubLogin`）
  时清空。
- 登录页把 `loginError` 显著展示出来（例如红色告警条，"登录失败：需要 xxx 组织成员"），
  与 `loginInfo.message` 那种普通提示区分开。
- `useGwClient` 把 `loginError` 一起导出，两个入口都传给 `GwLoginGate`。

### 顺带（建议级，可一并做）

未登录状态下每次重试都会弹一条 `rpc: spider.SpiderRpc/Pong / canceled by client: 未登录`
的红色通知，5 秒一条，很吵。`needLogin` 为真期间应当抑制这条通知（在两个入口的 `onCallError`
里判断，或在 `useGwClient` 内部统一过滤 needLogin 期间的 Pong 错误）。
