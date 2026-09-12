---
title: 失败经验：握手回包附加字段被 RTC 传输层丢弃 / 失败原因被重试覆盖
type: lesson
status: active
created_at: 2026-09-08T16:00:00+08:00
updated_at: 2026-09-12T12:10:00+08:00
priority: high
keywords:
  - RtcTransport
  - cancelAllPendingCalls
  - UnaryCallResponse
  - 握手协议
  - needLogin
  - githubClientId
  - 自研RPC传输
  - 重试覆盖错误信息
summary: 网关握手403回包里的needLogin/githubClientId等业务字段无法到达前端业务层, 因为统一取消路径把失败原因重建成了只剩code/message的protobuf类型; 另附一个同源问题——登录失败原因被下一次无code重试的通用403覆盖
questions:
  - 握手回包字段传不到前端是什么原因
  - 登录失败原因被重试覆盖是怎么回事
load: on-demand
related:
  - agent-memory/decisions/decision-2026-09-08-后台登录改为github-oauth.md
  - agent-memory/lessons/success-桩网关加cdp浏览器做登录链路联调.md
  - agent-memory/knowledge/architecture-nc-js.md
---

# 失败经验：握手回包附加字段被传输层丢弃

## 问题背景

后台登录改为 GitHub OAuth 后，网关握手 403 回包需要带上 `needLogin/githubClientId/
githubAuthorizeUrl/githubScope/githubOrg/allowRtcToken` 等结构化信息，供前端弹出登录门。
网关侧代码审查通过、单测通过，两轮静态审查（含专门的验收 Agent）都判定"没问题"，
但真实浏览器联调时：**登录门 `GwLoginGate` 根本没出现，弹出来的还是旧的
"请输入管理秘钥"输入框**，页面报错是 `rpc: spider.SpiderRpc/Pong / canceled by client: 未登录`。

## 失败方法（为什么静态审查抓不出来）

网关侧代码是对的，403 回包 JSON 里字段齐全；前端 `spidergw.ts` 的判断逻辑
`e.needLogin || e.githubClientId` 单看也是对的。问题出在两者之间的传输链路，
静态审查只会分别看两端代码，不会去追一次真实握手失败时数据经过的每一跳。

## 失败表现（根因，已定位非猜测）

链路：

1. `rtc-rpc.ts` 的 `authByTokenHandshake` 收到非 0 回包 → `reject(json)`（json 完整）；
2. `initRtcChannel` 的 `handshake(...).catch(e => channelClosed(e))`；
3. `RtcTransportAutoReconnect` 的 `dataChannelPromise.catch(e => transport.cancelAllPendingCalls(e))`；
4. **`RtcTransport.ts` 的 `cancelAllPendingCalls` 把 reason 重建成
   `UnaryCallResponse.create({seq, code: reason.code || 400, message: 'canceled by client: ' + err2str(reason)})`**
   —— 它是 protobuf 生成的类型，只留得下 `code` 和 `message`，
   **所有附加字段在这一步被物理丢光**。

所以 `e.code === 403` 成立（这也是为什么旧的秘钥弹窗会出现），但
`e.needLogin || e.githubClientId` 恒为 false，直接落进"兼容极老网关"的分支。
**网关侧改得再对也没用，这条路走不通。**

## 根本原因

这条 RTC-gRPC 传输是自研的，`cancelAllPendingCalls` 是所有 RPC 共用的统一取消路径，
`UnaryCallResponse` 是 proto 类型天然带不了自定义字段——任何"想让 RPC 错误通道携带
额外业务字段"的设计，都会在这一步被截断，且这个丢失点离两端代码审查的视线都很远。

## 规避方法

**不要**去改 `cancelAllPendingCalls`（公共路径，proto 类型改不了）。改成"握手回包不经过
RPC 错误通道，直接回调给上层"：

1. `authByTokenHandshake(token, onReply?, onHandshakeError?)` 新增一个失败回调，
   在 `reject(json)` **之前**用完整 json 调它；`RtcTransportAutoReconnect` 增加对应
   可选透传参数。两个新参数都可选，不改既有调用方语义，不动二进制帧格式。
2. `spidergw.ts` 用这个新回调驱动登录态；`mustInitOk` 的 `catch` 分支改成**优先看
   `needLogin.value`**（回调必定早于 pong 的 reject 触发），只有它为 false 且
   `e.code===403` 时才回落旧的 `uiInputToken()` 弹窗。
3. 顺带修了一个小问题：GitHub 回调会带 `iss` 参数，原 `takePendingGithubCode`
   只删 `code`/`state`，`iss` 会留在地址栏，一并清掉。

## 关联问题：登录失败原因被下一次重试覆盖（同一轮联调发现）

**现象**：GitHub 授权回来 → 网关换票失败并返回"403 需要 xxx 组织成员" → **3 秒后前端
的下一次重连（这次没有 code）拿到通用的 403"未登录"，把登录页上的具体错误信息覆盖掉**。
用户最终只看到"未登录"，永远不知道自己是因为不在组织里被拒。

**根因**：登录失败信息和"未登录"状态共用同一个响应式变量，后一次握手（哪怕是无意义的
心跳重连）会无条件覆盖前一次的具体错误。

**规避方法**：
- 网关回包加 `loginFailed`（`json:"loginFailed,omitempty"`）字段，只在"这次 403 是带着
  code 来换票但失败了"时置 true，区别于"压根没登录"的普通 403。
- 前端新增一个**粘性**的 `loginError` ref：`loginFailed` 为真时记下 message，**之后的
  普通未登录 403 不得覆盖它**，只在用户再次点击登录时清空。UI 上与普通提示区分展示。

## 下次行动建议

握手阶段（或任何"首帧定生死"的协议）如果需要把结构化信息带给上层业务代码，
**第一时间去追一遍真实失败路径穿过了哪些统一错误处理/重试/取消逻辑**，不要只看
两端代码是否"看起来正确"；同时区分"状态"与"该状态下最近一次的详细原因"，
后者不应被无关的后续事件静默覆盖。

## 适用边界

适用于本仓库自研的 RTC-gRPC 传输（`packages/catalyst/contract/rpc/grpc_rtc/`）。
其他走标准 gRPC/HTTP 的场景，错误对象本身可以带任意字段，不存在这个坑；
但"UI 状态被无关重试覆盖"这条更通用，任何带自动重连/心跳的长连接都可能踩到。
