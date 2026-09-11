---
title: 决策：后台登录改为 GitHub OAuth（限 1second 组织成员）
type: decision
status: active
created_at: 2026-09-08T16:00:00+08:00
updated_at: 2026-09-08T16:00:00+08:00
priority: high
keywords:
  - GitHub OAuth
  - 后台登录
  - RtcToken
  - OAuth App
  - client_id
  - allow_rtc_token
  - 会话票据
summary: 固定管理秘钥改为 GitHub OAuth 登录并校验 1second 组织成员身份的四个关键设计取舍与原因
load: on-demand
related:
  - agent-memory/knowledge/architecture-nc-js.md
  - agent-memory/sessions/2026/2026-09-08-后台登录改为github授权.md
  - agent-memory/lessons/failure-握手回包附加字段被传输层丢弃.md
---

# 决策：后台登录改为 GitHub OAuth

## 背景

后台（NC-JS 的 qiankun 微前端子应用）不走 REST，全部数据走 WebRTC DataChannel 上自实现的
gRPC，直连 SPIDER 网关。原鉴权只有一层：握手首帧发 `{token, clientName}`，网关只判断
`token == RtcToken`（全局共享的固定管理秘钥，无账号/角色体系），403 时前端弹
`prompt('请输入管理秘钥')`。用户要求改为 GitHub 授权登录，且限 1second 组织成员才能登录。

## 要解决的问题

在"不新增中转服务、前端一份代码同时适配本地与生产、保留应急兜底"的约束下，设计新的鉴权协议。

## 决策要点

### 1. OAuth code 交换放在网关 Go 侧，不做 Cloudflare Pages Function 中转

**方案 A（网关直连 GitHub）**：优点——少一个中转服务，client_secret 只存网关一处配置；
缺点——依赖网关机能直连 `api.github.com`（顾虑 GFW）。
**方案 B（Pages Function 中转）**：优点——不依赖网关出海；缺点——多一层部署面、secret 分散两处。

**决策**：方案 A。实测网关机 osec-res1 直连 `https://api.github.com/` 200、耗时 0.5s，
不存在网络风险，方案 B 的顾虑不成立，选更省事的方案 A。

### 2. 建 prod / dev 两个 OAuth App，而非一个 App 配多回调

GitHub 新版表单其实支持一个 App 最多注册 10 个回调地址（此前"只能配一个"是过时信息，
已当场纠正）。即便如此，用户仍选择建两个 App，理由是本地开发用的 client_secret 要与
生产环境隔离，一个泄露不影响另一个。

### 3. client_id 由网关握手 403 时下发，前端不写死

前端代码不含任何 client_id 字面量；网关配置里存了自己的 client_id，403 时随其余登录信息
一起回给前端，前端照着跳转 GitHub 授权页。效果：本地连 dev 网关自动用 dev App，
连生产网关自动用 prod App，**一份前端代码同时适配两套环境**，是整个设计里最省事的一环。

### 4. 保留 RtcToken 作为可关闭兜底

新增配置项 `allow_rtc_token`，生产置 `false`（只认 GitHub 会话票据），本地开发或
GitHub/组织服务不可用时可临时打开。启动校验相应改为"GitHub 三件套（client_id/secret/
session_secret）齐全 或 allow_rtc_token=true"二选一满足即可启动，避免网关无法启动的风险。

## 影响

- 网关新增配置节 `services.gateway.github_auth`（client_id/secret、org、session_secret、
  session_ttl、allow_rtc_token、redirect_uri_prefixes），协议细节见任务简报
  `agent-tasks/2026-09-08-github-oauth-login/00-shared.md` §4~5（新握手协议 v2）。
- 前端新增登录门组件 `GwLoginGate`，`spidergw.ts` 增加 `needLogin`/`loginError` 状态。
- 两个 OAuth App 的 client_id、管理页地址、已注册回调列表见
  `knowledge/reference-github-oauth配置.md`（**client_secret 不在任何记忆文件里**）。

## 复盘条件

- 若网关机与 GitHub 的连通性变差（GFW 策略收紧），需重新评估是否加中转（方案 B）。
- 若组织成员规模扩大到需要更细粒度的角色/权限，当前"组织成员即可登录"的粗粒度模型需升级。
- 若 `allow_rtc_token` 在生产被长期打开使用，说明 GitHub 登录链路不可靠，需要复查而非将就。

## 当前状态

代码已合并并 push（SPIDER `41832ca` / NC-JS `5808d42` / COMMON `ac5cfc5`），**未部署**。
部署前置条件与顺序见 `sessions/2026/2026-09-08-后台登录改为github授权.md`「后续行动」一节。
