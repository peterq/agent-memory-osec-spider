---
title: 参考：GitHub OAuth App 配置（后台登录）
type: knowledge
status: active
created_at: 2026-09-08T16:00:00+08:00
updated_at: 2026-09-08T16:00:00+08:00
priority: medium
keywords:
  - GitHub OAuth App
  - client_id
  - redirect_uri
  - 1second 组织
  - 回调地址
  - Access restricted
summary: 两个GitHub OAuth App(prod/dev)的名称、client_id、管理页、已注册回调列表与组织第三方应用策略, 不含任何secret
load: on-demand
related:
  - agent-memory/decisions/decision-2026-09-08-后台登录改为github-oauth.md
  - agent-memory/sessions/2026/2026-09-08-后台登录改为github授权.md
---

# GitHub OAuth App 配置参考

## 组织与策略

组织 slug：`1second`。组织第三方应用策略是"Access restricted"，但 GitHub 明确写着
*Applications owned by 1second always have access*，所以本组织自己名下的这两个 App
**不需要额外审批**，成员首次登录只会看到常规的授权确认页。

## 两个 App（均归 1second 组织所有，非个人账号）

| 用途 | 名称 | client_id | 管理页 |
|---|---|---|---|
| 生产 | `1s-nc-admin (prod)` | `Ov23liVdy3cJkVMV03L1` | https://github.com/organizations/1second/settings/applications/3843686 |
| 本地 | `1s-nc-admin (dev)` | `Ov23lih8tSerxYwqexP5` | https://github.com/organizations/1second/settings/applications/3843687 |

**client_secret 不在本文件、不在任何 git 跟踪文件里**，存放于仓库内未纳入 git 的
`.agent-browser/oauth-credentials.txt`。**任何情况下都不要把 secret 写进 git 跟踪的
文件、记忆文件或提交信息。**

## 已注册的回调地址（决定前端 redirect_uri 只能取这些值）

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

**含义**：前端 `redirect_uri` 必须与上表某一项**逐字相等**（GitHub 新版表单支持一个
App 最多 10 个回调，但本次未勾选"Allow wildcard matching"，不能靠路径前缀匹配）。
qiankun 生产环境下子应用的 `location.pathname` 就是 `/spiderAdmin` 或
`/pan-share-download`（带不带尾斜杠都已注册）；本地 dev 服务器下 pathname 是 `/`，
端口需为 5173~5175 之一。算出来的 redirect_uri 若不在上表内，GitHub 会直接报
`redirect_uri_mismatch`，此时应去 App 管理页补一条回调，而不是在前端瞎凑。

网关侧白名单实现为**前缀**匹配（`redirect_uri_prefixes`），缺省三项：
`https://1s.peterq.cn/`、`http://localhost:`、`http://127.0.0.1:`
（比最初设计多了 `http://127.0.0.1:` 一项，因为 dev App 注册了 `127.0.0.1:5173` 回调）。

## 连通性

网关机 osec-res1 实测直连 `https://api.github.com/` 200、耗时 0.5s，无需代理，
因此 OAuth code 交换与组织成员校验直接放在网关 Go 侧做（见
`decisions/decision-2026-09-08-后台登录改为github-oauth.md` 决策 1）。

## 真实联调实测过的分支（工具 `osec-spider-go/tools/ghauthcheck`）

| 场景 | 结果 |
|---|---|
| `-org=1second`，账号是 active 成员 | 通过，返回 login/uid/avatar |
| `-org=anthropics`，非成员 | 命中 `ErrNotOrgMember`，文案"不是 xxx 的 active 成员" |
| 过期/错误 code | 报"GitHub access_token 交换失败"，**HTTP 状态码仍是 200**，
  错误在 body 的 `error` 字段里，Go 侧按 body 判定，不能只看状态码 |
