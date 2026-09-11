# 共享上下文：后台登录改造为 GitHub OAuth（限 1second 组织成员）

## 1. 目标（用户原话）

> 现在登录使用固定 token, 改为 github 授权登录, 检测需要为 1second 组织成员, 才能登录。

## 2. 现状（已核实的事实）

- 后台（NC-JS 的 qiankun 微前端子应用）不走 REST，全部数据走 **WebRTC DataChannel 上自实现的 gRPC**，
  直连 SPIDER 网关 `115.29.215.228:7542/udp`。
- 鉴权只有一层：握手首帧发 `{token, clientName}`，网关
  `osec-spider-go/services/gateway/gateway.go:rtcHandshake` 只判断 `m.Token == gw_config.Get().RtcToken`
  （全局共享的固定管理秘钥，无账号/角色体系），失败返回 `{code:403}`。
- 前端把秘钥存在 localStorage `spiderGwConfig`（`{clientName, gwToken}`），403 时 `prompt('请输入管理秘钥')`。
- 只有两个前端入口用 `useGwClient()`：`admin/spiderAdmin/src/layout/AppLayout.tsx`、
  `admin/panShareDownload/src/ui/panShareDownloadUi.tsx`。`login3rd` 子应用不连网关。
- 生产后台地址 `https://1s.peterq.cn`（Cloudflare Pages 项目 `1s-nc-admin-qiankun`）。
- **网关机能直连 GitHub**（osec-res1 实测 `https://api.github.com/` 200、0.5s），所以 OAuth code 交换、
  组织成员校验全部放在网关 Go 侧做，不需要任何中转服务。
- 组织 slug：`1second`（`git@github.com:1second/nc-js.git`）。

## 3. 用户已拍板的决策

1. **保留固定 RtcToken 作为兜底，但生产默认关闭**：由配置项 `allow_rtc_token` 控制，
   线上置 false（只认 GitHub 会话票据），本地开发/GitHub 故障时可打开。
2. **建两个 OAuth App**：prod 回调 `https://1s.peterq.cn/`，dev 回调 `http://localhost:5173/`。
   `client_id` **不写进前端代码**，由网关在握手 403 时下发，前端照着跳转 —— 因此本地开发连
   127.0.0.1 网关就自动用 dev App，连生产网关就用 prod App，前端一份代码两套环境。
3. 语言：所有代码注释、提交信息、给用户的说明一律中文。

## 4. 新握手协议（v2）—— 两端必须逐字对齐

客户端首帧（JSON，字段全部可选）：

```json
{ "token": "<会话票据 或 旧 RtcToken>", "clientName": "xxx", "githubCode": "", "redirectUri": "" }
```

网关按以下顺序分支：

1. **`githubCode` 非空 → 登录换票**
   - 校验 `redirectUri` 以配置白名单 `redirect_uri_prefixes` 中某一项开头，否则 403。
   - `POST https://github.com/login/oauth/access_token`（Header `Accept: application/json`，
     body `client_id/client_secret/code/redirect_uri`，超时 10s）→ 拿 `access_token`。
   - `GET https://api.github.com/user`（Header `Authorization: Bearer <token>`）→ `login/id/name/avatar_url`。
   - `GET https://api.github.com/user/memberships/orgs/1second` → 必须 200 且 `state == "active"`；
     404/403 一律判为"不是组织成员"，返回 403 且 message 写明"需要 1second 组织成员"。
   - 通过则签发会话票据，回包：
     ```json
     {"code":0,"message":"ok","session":"v1.xxx.yyy","expiresAt":1790000000,
      "user":{"login":"peterq","name":"...","avatarUrl":"https://..."}}
     ```
     并且**本次连接直接视为已认证**（不需要客户端再连一次）。
2. **`token` 能验签且未过期的会话票据 → 通过**，caller info 带上 GitHub login。
3. **`allow_rtc_token == true` 且 `token == RtcToken` → 通过**（兜底，caller 标记为 `rtc-token`）。
4. **否则 403**，回包必须带上前端发起登录所需的全部信息：
   ```json
   {"code":403,"message":"未登录","needLogin":true,
    "githubClientId":"Ov23xxxx","githubAuthorizeUrl":"https://github.com/login/oauth/authorize",
    "githubScope":"read:org","githubOrg":"1second","allowRtcToken":false}
   ```
   （`allowRtcToken` 告诉前端要不要显示"用管理秘钥登录"的兜底入口。）

会话票据格式（自定义紧凑格式，不引第三方 JWT 库）：

```text
v1.<base64url(payload JSON)>.<base64url(HMAC-SHA256(session_secret, "v1."+payloadB64))>
payload: {"login":"peterq","uid":123,"name":"...","avatar":"...","iat":1788,"exp":1789}
```

- 签名比较必须用 `hmac.Equal`（常量时间）。
- 票据、access_token、client_secret **一律不得写进日志**。

## 5. 网关新增配置（`services.gateway` 节下）

```yaml
    github_auth:
      client_id: "Ov23xxxxxxxx"
      client_secret: "xxxxxxxx"
      org: "1second"                 # 缺省 1second
      session_secret: "<32+ 位随机串>"
      session_ttl: 168h              # 缺省 168h
      allow_rtc_token: false         # 缺省 false
      redirect_uri_prefixes:         # 缺省 ["https://1s.peterq.cn/", "http://localhost:"]
        - "https://1s.peterq.cn/"
        - "http://localhost:"
```

启动校验：`client_id/client_secret/session_secret` 任一为空**且** `allow_rtc_token=false` 时 panic
（否则网关谁都连不进去）；只要 GitHub 配置齐全，`rtc_token` 允许为空。

## 6. 仓库与路径

| 代号 | 路径 |
|---|---|
| COMMON | `/home/peterq/dev/projects/1s/enfi-resource-common`（本简报所在仓库） |
| SPIDER | `/home/peterq/dev/projects/1s/osec-spider-go`（网关 Go 服务） |
| NC-JS | `/home/peterq/dev/projects/1s/nc-js`（前端 mono repo，pnpm workspace） |

## 7. 硬性约束（违反会返工或造成生产事故）

- **绝对不要跑 `pnpm build` / `deployProd` / `vite build`**：NC-JS 的 mfe 插件与部署脚本会
  真实写生产 OSS 的 `apps.json`。类型检查用 `npx vue-tsc --noEmit`，测试用 `npx vitest run`。
- **不要碰 `_note/` 目录**（仓库外 secret 目录，含 AK/SK），也不要尝试读写生产配置 yaml；
  配置项只改 Go 结构体与示例文件 `PRD/config-v2/config.local.example.yaml`。
- **不要执行部署、不要 ssh 到生产机、不要重启任何线上服务。**
- 不要把 client_id / client_secret / session_secret 的真值写进代码、注释、测试或提交。
- 不要动 proto、不要重跑 `gen.sh` / `protc_gen.sh`（本次改造不涉及 proto）。
- Go 侧错误包装沿用 `github.com/pkg/errors`；前端组件写法沿用现有 `defineComponent + setup 返回 JSX`。
- 注释、提交信息一律中文。**不要 commit，不要 push**，改完保留工作区，由主控统一提交。

## 8. 交付要求

汇报时给出：改了哪些文件（各自做了什么）、跑了哪些验证命令及结果、有意留下的 TODO 或风险点。
不要复述简报内容，不要贴大段 diff，只贴关键片段。
