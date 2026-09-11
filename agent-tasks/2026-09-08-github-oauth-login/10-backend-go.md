# 角色：网关 Go 侧（SPIDER）

先读 `00-shared.md`，第 4/5 节是协议正本，逐字实现，不要自行改字段名。

## 必读文件（读它们是为了照抄现有风格与接线方式）

- `osec-spider-go/services/gateway/gateway.go` —— `rtcHandshake`（第 113 行起）是本次主战场；
  `Start()` 里第 178 行起有 `rtc_token 为空则 panic` 的启动校验，新校验加在旁边。
- `osec-spider-go/config/config.go` —— `GatewayConfig`（第 82 行起）是配置结构体；
  看它的 yaml tag 风格与注释风格。
- `osec-spider-go/config/gw_config/gw_config.go` —— `gw_config.Config` 是 `GatewayConfig` 的别名，
  `gw_config.Get()` 每次都重新取，配置热更新靠它。
- `osec-spider-go/config/config_test.go` —— 配置解析测试的写法，新增字段要在这里补断言。
- `osec-spider-go/PRD/config-v2/config.local.example.yaml` —— 本地示例配置，要补 `github_auth` 节。
- 任一现有子包（如 `services/gateway/lifecycle/`）—— 看包注释、错误包装（`github.com/pkg/errors`）、
  `app_error.NewError(msg, code)` 的用法。

## 落点

新建包 `osec-spider-go/services/gateway/auth/`：

- `session.go`：`Sign(payload, secret) string` / `Verify(token, secret) (*Session, error)`，
  格式见 00-shared 第 4 节；过期、格式错、签名错要返回可区分的错误。
- `github.go`：`ExchangeCode(ctx, cfg, code, redirectURI) (*GithubUser, error)`，
  内部串起 code→access_token→/user→/user/memberships/orgs/{org}；
  用带超时的 `http.Client`（10s），HTTP 状态码非 2xx 要把 GitHub 的 error 描述带进错误信息
  （**但不得带 access_token / client_secret**）。组织不匹配返回一个可判定的哨兵错误
  （如 `ErrNotOrgMember`），让调用方翻译成 403 文案。
- `*_test.go`：至少覆盖 —— 签发→验签往返、过期票据被拒、签名被篡改被拒、
  非法格式被拒；GitHub 交互用 `httptest.Server` 打桩（把 base url 做成可注入的字段/变量，
  默认值是真实 GitHub 地址），覆盖"成员 active 通过""state=pending 拒绝""404 拒绝"。

改造 `services/gateway/gateway.go`：

- `rtcHandshake` 按 00-shared 第 4 节四个分支重写；回包结构体加上 `session/expiresAt/user/needLogin/
  githubClientId/githubAuthorizeUrl/githubScope/githubOrg/allowRtcToken` 字段，
  **零值字段要 `omitempty`**，别让成功回包里冒出一堆空字段。
- `spiderclient.SetCallerInfo` 的 `InstanceName` 保持原样，新增把 GitHub login 也带上
  （看 `spiderclient.CallerInfo` 有没有合适字段，没有就加一个 `GithubLogin string`，
  加字段要检查所有构造点是否编译通过）。日志行 `log.Println("rtc handshake", ...)` 补上登录名。
- `Start()` 的启动校验按 00-shared 第 5 节改写，panic 文案写清楚缺哪一项、后果是什么。

配置：`GatewayConfig` 加 `GithubAuth GithubAuthConfig \`yaml:"github_auth"\``，
新结构体和缺省值处理（org / session_ttl / redirect_uri_prefixes 的缺省）写在 `config/config.go`，
缺省填充放在已有的 applyDefault 类逻辑里（先找现成的落点，没有就在 `GatewayConfig` 上加方法）。

## 验证命令（在 `/home/peterq/dev/projects/1s/osec-spider-go` 下）

```bash
go build ./...
go vet ./services/gateway/... ./config/...
go test ./services/gateway/auth/... ./config/... -count=1
```

`config` 包的测试历史上对环境敏感，若 `go test ./config/...` 原本就失败，先 `git stash` 确认是存量问题，
在汇报里写明，不要为了让它过而改无关代码。

## 禁止

不要 commit / push，不要部署，不要 ssh，不要读 `_note/`。
