# 角色：验收

先读 `00-shared.md`（协议正本）、`10-backend-go.md`、`11-frontend.md`（各自的要求），
再看两位开发 Agent 改出来的工作区（`git -C <repo> diff` / `git status`）。**你只审查、不改代码**
（除非发现的是一行以内的明显笔误，且在报告里写明改了什么）。

## 验收清单

### A. 协议一致性（最重要）
逐字段比对网关回包与前端读取：`session/expiresAt/user{login,name,avatarUrl}/needLogin/
githubClientId/githubAuthorizeUrl/githubScope/githubOrg/allowRtcToken`，
以及首帧 `token/clientName/githubCode/redirectUri`。**Go 的 json tag 与 TS 的属性名必须逐字一致**
（大小写、驼峰），任何一处对不上就是阻断级问题。

### B. 安全
1. 会话票据签名比较是否用了 `hmac.Equal`（常量时间）；过期是否真的被拒。
2. `client_secret` / `access_token` / `session` 是否出现在任何日志、错误信息、注释、测试数据里。
3. 组织成员判定：是否要求 `state == "active"`（`pending` 邀请中必须拒绝），404/403 是否都判为非成员。
4. `redirectUri` 是否做了白名单前缀校验。
5. 前端 state 参数是否生成随机值并在回调时校验（CSRF）；code 是否用后即从地址栏抹除。
6. 启动校验：GitHub 配置缺失且 `allow_rtc_token=false` 时是否 panic（避免网关无人能连或裸奔）。

### C. 行为
1. 未登录时前端**不会**每秒重连死刷（看 `mustInitOk` 改造后的循环）。
2. 会话过期/被篡改时前端能回到登录页而不是白屏或死循环。
3. `allow_rtc_token=true` 时旧的管理秘钥通道仍可用（兜底不能被改坏）。
4. 现有测试 `admin/spiderAdmin` 的 vitest 仍然全绿。

### D. 编译与测试（自己跑一遍，不要只信开发 Agent 的报告）
```bash
cd /home/peterq/dev/projects/1s/osec-spider-go && go build ./... && go vet ./services/gateway/... && go test ./services/gateway/auth/... -count=1
npx vue-tsc --noEmit -p admin/spiderAdmin/tsconfig.app.json && npx vitest run --root admin/spiderAdmin
```
**禁止**跑 `pnpm build` / `vite build` / `deployProd` / 任何部署或 ssh 命令。

## 交付

按 `阻断级 / 建议级 / 通过项` 三档给结论，每条写清：文件:行、问题、为什么是问题、建议怎么改。
没有问题就明确说"未发现阻断级问题"，不要为了凑数编问题。
