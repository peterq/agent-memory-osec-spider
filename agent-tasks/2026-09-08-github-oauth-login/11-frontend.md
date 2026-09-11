# 角色：前端（NC-JS）

先读 `00-shared.md`，第 4 节握手协议是与网关的契约正本，字段名逐字对齐。

## 必读文件

- `nc-js/packages/catalyst/contract/rpc/spiderGw/spidergw.ts` —— `useGwConfig()` / `useGwClient()`，
  本次改造核心；注意 `mustInitOk()` 里 `e.code === 403` 的处理。
- `nc-js/packages/catalyst/contract/rpc/grpc_rtc/rtc-rpc.ts` —— `authByTokenHandshake()`（第 97 行）
  发首帧、收回包；`reject(json)` 把网关回包整体抛出（所以 403 的附加字段前端拿得到），
  成功时只 `console.log` 丢弃回包 —— 需要新增回调把回包交出来。
  `RtcTransportAutoReconnect()`（第 274 行）是断线自动重连入口。
- `nc-js/admin/spiderAdmin/src/layout/AppLayout.tsx` —— 子应用外壳（顶栏 + 侧栏 + `useGwClient` 接线），
  登录态 UI 主要落在这里；顶栏已有"环境切换 / clientName / Mock 开关"的写法可照抄。
- `nc-js/admin/panShareDownload/src/ui/panShareDownloadUi.tsx` —— 第二个入口，同样要改。
- `nc-js/admin/spiderAdmin/src/pages/lifecycle/__tests__/smoke.test.tsx` —— 现有测试绕开握手，
  改造不要破坏它。

## 落点与要求

### 1. 新文件 `packages/catalyst/contract/rpc/spiderGw/githubAuth.ts`

- `useGwSession()`：`useLocalStorage('spiderGwSession', { session:'', expiresAt:0, user:{login:'',name:'',avatarUrl:''} })`。
- `takePendingGithubCode()`：从 `location.search` 取 `code`/`state`；校验 state 与 sessionStorage 中
  登录前写入的值一致（不一致视为 CSRF，丢弃并报错）；**立刻用 `history.replaceState` 把 code/state
  从地址栏抹掉**（code 一次性，刷新重放会失败）；返回 `{ code, redirectUri }`，
  `redirectUri` 必须与发起授权时用的完全一致（`location.origin + location.pathname`）。
- `startGithubLogin(info)`：`info` 是网关 403 回包里的 `githubClientId/githubAuthorizeUrl/githubScope`；
  生成随机 state 存 sessionStorage，跳转
  `${authorizeUrl}?client_id=..&redirect_uri=..&scope=read:org&state=..`。
  `redirect_uri` 用 `location.origin + location.pathname`（qiankun 下是 `https://1s.peterq.cn/spiderAdmin`，
  已注册的回调 `https://1s.peterq.cn/` 是它的前缀，GitHub 允许）。
- `clearGwSession()`：退出登录，清 localStorage 会话后 `location.reload()`。

### 2. `rtc-rpc.ts`

`authByTokenHandshake(token, onReply?)`：握手成功时把回包 JSON 交给 `onReply`（用于保存网关签发的
session）。`RtcTransportAutoReconnect` 增加透传该回调的可选参数。**不要改动现有调用方的签名语义**
（新参数一律可选），也不要改二进制帧格式。

### 3. `spidergw.ts` 的 `useGwClient`

- hello 工厂改为：若有待兑换的 GitHub code → 发 `{githubCode, redirectUri, clientName}`；
  否则发 `{token: session 票据(没有则空串), clientName}`。**旧的 `gwToken` 字段保留**，
  在网关回包 `allowRtcToken:true` 且用户手动录入秘钥时仍然发它（兜底通道）。
- 握手成功回包里有 `session` 时，写入 `useGwSession()`（含 `expiresAt` 与 `user`）。
- 403 且 `needLogin` 时：**不要继续 1 秒一次地死循环重连**——把 `needLogin` 置为 true 并把网关下发的
  `githubClientId` 等信息暴露出去，停在等待用户点击登录的状态（原有 `while` 重试循环要相应改造，
  注意 `abort()` 与 `disposed` 的既有语义别破坏）。
- `options` 增加 `onNeedLogin?`（可选），`uiInputToken` 保留但只在 `allowRtcToken` 为真时才用得上。
- 新增导出：`needLogin`(ref)、`loginInfo`(ref, 网关下发的登录参数)、`currentUser`(computed, 来自会话)。

### 4. 两个入口的 UI

`spiderAdmin/src/layout/AppLayout.tsx`：

- 未登录（`needLogin` 为真）时，用整页登录卡片替代现在的 `Spin+Skeleton`：
  标题写明"需 GitHub 账号且为 1second 组织成员"，主按钮"使用 GitHub 登录"调用 `startGithubLogin`；
  网关回包 `allowRtcToken` 为真时，再给一个次要入口"使用管理秘钥登录"（沿用 `modals.prompt`）。
- 登录后顶栏显示头像 + GitHub 登录名，下拉里放"退出登录"。头像用 `user.avatarUrl`，
  加载失败回退到现有的 `UserOutlined` 图标。
- 登录失败（403 且带 message，例如"不是 1second 组织成员"）要在登录页上把网关返回的 message 展示出来，
  不能只在 console 里。

`panShareDownload/src/ui/panShareDownloadUi.tsx`：同样接入登录页与顶栏用户信息。它是老写法（多 Tab），
不必与 spiderAdmin 像素级一致，但交互语义要一致。**登录卡片组件写在 catalyst 里复用**
（建议 `packages/catalyst/ui/widget/GwLoginGate.tsx`），两个入口都用它，别复制两份。

## 验证命令（在 `/home/peterq/dev/projects/1s/nc-js` 下）

```bash
npx vue-tsc --noEmit -p admin/spiderAdmin/tsconfig.app.json
npx vitest run --root admin/spiderAdmin
cd admin/panShareDownload && npx vue-tsc --noEmit && cd -
```

若 `vue-tsc` 在改动前就有存量报错，先确认是存量（`git stash` 对比），汇报里写明，只保证不新增报错。

## 禁止

**绝对不要跑 `pnpm build` / `vite build` / `deployProd`**（会写生产 OSS 的 apps.json）。
不要 commit / push。不要动 proto 与 `protc_gen.sh`。不要把 client_id 写进前端代码
（它由网关握手回包下发，这是本设计的关键点）。
