# 角色：记忆维护（agent-memory）

按 COMMON 仓库根 `AGENTS.md` 内嵌的 agent-memory 技能规范维护 `agent-memory/`。
本次任务的全部事实来源是同目录的 `00-shared.md`（协议正本）与 `99-notes.md`（过程裁定、
OAuth App 事实、两次联调发现的阻断问题），以及三条已推送的提交：

- SPIDER `41832ca` feat(gateway): 后台登录改为 GitHub OAuth, 限 1second 组织成员
- NC-JS `5808d42` feat(admin): 后台登录改为 GitHub 授权, 替代固定管理秘钥
- COMMON `ac5cfc5` feat(common): CallerInfo 增加 GithubLogin, 沉淀浏览器调试与 CDP 驱动脚本

先读 `agent-memory/00-overview.md` 与 `01-index.md` 摸清现有结构与写作风格，再动手。
**不要**把下面的清单原样抄进文件，要按各文件的体例改写、提炼。

## 必须产出/更新的内容

1. **会话摘要** `sessions/2026/2026-09-08-后台登录改为github授权.md`：
   完成事项、关键发现、做出的决策、后续行动（见下面第 6 条"未完成"）。

2. **决策记录** `decisions/decision-2026-09-08-后台登录改为github-oauth.md`，要写清这几个被认真权衡过的点：
   - OAuth code 交换放在**网关 Go 侧**而不是 Cloudflare Pages Function：因为实测网关机
     osec-res1 直连 `api.github.com` 200/0.5s，不存在 GFW 风险，放网关能少一个中转、
     secret 只存一处。
   - **建 prod / dev 两个 OAuth App**（而不是一个 App 配多回调）：GitHub 新版表单其实支持
     一个 App 最多 10 个回调地址（我最初"只能配一个"的说法是过时信息，已当场纠正），
     但用户仍选择两个 App，理由是本地开发用的 secret 与生产隔离。
   - **client_id 由网关握手 403 时下发**，前端不写死：于是"连哪个网关就用哪套 App"，
     一份前端代码同时适配本地与生产。这是整个设计里最省事的一环。
   - **保留 rtc_token 作为可关闭兜底**（`allow_rtc_token`，生产 false）：GitHub 或组织
     不可用时还能进后台。启动校验改成"GitHub 三件套齐全 或 allow_rtc_token=true"。

3. **失败经验** `lessons/failure-握手回包附加字段被传输层丢弃.md`（**本次最值钱的一条**）：
   网关 403 回包里的 `needLogin/githubClientId/...` 到不了业务层，因为
   `packages/catalyst/contract/rpc/grpc_rtc/RtcTransport.ts` 的 `cancelAllPendingCalls`
   把握手失败原因重建成了 protobuf 的 `UnaryCallResponse`，只留得下 `code` 和 `message`。
   现象是"登录门不出现、弹的还是旧的管理秘钥输入框"，两轮静态审查（含专门的验收 Agent）
   都没发现，是真实浏览器联调一眼看出来的。规避方法：握手阶段要传给业务层的结构化信息
   走专门的回调（`onReply`/`onHandshakeError`），不要指望它能从 RPC 错误通道里穿过来。
   适用边界：这条 RTC-gRPC 传输是自研的，任何"想让握手回包带业务字段"的需求都会踩同一个坑。

4. **成功经验** `lessons/success-桩网关加cdp浏览器做登录链路联调.md`：
   方法论——涉及浏览器交互的改造，静态审查 + 单测不足以验收，要造一个**只保留被测链路**的
   桩服务（`osec-spider-go/tools/stubgw`：只有真实 rtcHandshake + 最小 SpiderRpc，
   不依赖 redis/mysql/ES）并用带登录态的调试浏览器实测。本次靠它抓到两个阻断级问题
   （字段被丢弃、失败原因被下一次重试覆盖），都是"代码看起来完全正确"的那种。
   记下可复用资产：`COMMON/scripts/agent-browser.sh`、`COMMON/scripts/cdp.py`、
   `osec-spider-go/tools/stubgw`、`osec-spider-go/tools/ghauthcheck`。

5. **流程** `procedures/workflow-带登录态的浏览器自动化.md`：
   启动/复用调试浏览器、用 cdp.py 导航求值填表、以及"Chrome 默认 profile 上开
   --remote-debugging-port 会被安全策略拦截，必须用独立 user-data-dir"这个前提。
   profile 在 `COMMON/.agent-browser/profile`（已 gitignore），人工登录一次可长期复用。

6. **当前状态**：更新 `00-overview.md` 第 2 节与 `current/tasks.md`（或等价文件）——
   代码三仓库已合并并 push，但**未部署**：
   - 待用户把 `.agent-browser/gateway-github-auth-snippet.yaml` 的内容贴进
     `_note/config/spider.prod.yaml` 的 `services.gateway` 下（含 client_secret 与
     session_secret，Agent 不能碰那个文件）；
   - 网关部署仍受既有阻塞影响（网关双机在跑 `hotfix/p4-bootstrap`，不要从 master 构建网关）；
   - 前端 `admin/qiankun` 与两个子应用需要 deployProd 才会生效。
   还要记一条：**上线顺序必须是"先网关后前端"**，否则新前端连旧网关会拿不到登录参数、
   老前端连新网关会因为 allow_rtc_token=false 而全员被拒。

7. **知识文件订正**（很重要，否则后续会话会读到过时结论）：
   - `knowledge/architecture-nc-js.md` 第 5 节现在写着"鉴权只有全局 RtcToken、403 时
     prompt 请输入管理秘钥"，已经不成立，改写为新的登录机制并指向新文件
     （`githubAuth.ts` / `GwLoginGate.tsx` / `spidergw.ts` 的 needLogin/loginError）。
   - SPIDER 的架构知识文件里凡是描述"RTC 握手只校验 rtc_token"的地方一并订正。

8. **参考** `knowledge/` 或 `reference` 类文件里记下（**只记非机密项**）：
   两个 OAuth App 的名称、client_id、管理页 URL、已注册回调列表、组织策略
   （1second 自有应用自动放行，不需审批）；并注明 secret 存放位置是
   `COMMON/.agent-browser/oauth-credentials.txt`（未纳入 git），**严禁把 secret 写进任何记忆文件**。

9. 最后更新 `01-index.md`：新增文件全部登记（文件索引表 + 关键词索引 + 最近更新），
   并检查是否有指向不存在文件的死链。

## 交付

改完 `git -C /home/peterq/dev/projects/1s/enfi-resource-common status --short` 自查一遍，
**不要 commit、不要 push**（由主控统一提交），汇报新增/修改了哪些文件、各自记了什么。
