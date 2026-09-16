# 过程追加（主控维护）

- 2026-09-16 派单：10/20/30/40/50/60/70/80/85 九个开发角色并行（sonnet），45（NC-JS 前端）待 40 交付契约后派。
- 合并顺序预案：COMMON 分支先（delete-breaker → valid-unify → health-observe → ci → secrets），每合一个 `go build`；再 SPIDER/API/STORAGE。合并前须用户确认。
- 已知重叠文件：API `services/valid/valid.go`/`valid_v3.go`（10 与 20）；SPIDER `config/gateway/gateway.go`、`services/gateway/gateway.go`（10/30/40）；API `config/config.go`（10/30/85）；两份下载测试文件（50 加标签、60 改内容）。

## 交付/验收进度
- ✅ 85 search-config：`api-wt-search-config` `7677fcf`，验收通过（search_canary 未接 featureflag 为授权简化；keywords.txt 与 PRD p5-recheck 对拍表逐行一致）。待用户确认合并。
- ✅ 40 health-observe：COMMON `common-wt-health-observe` `69acf64`（health_rpc 契约 + queue_admin.proto absThreshold 字段，45 前端可依赖）；SPIDER `spider-wt-health-observe` `161483b`（新模块 `services/gateway/health` 账号池探测+站点巡检、`download_scheduler/probe.go`、queue_admin absThreshold+SiteRecentStats、修复 `spider_gateway_service.go` ListQueue 的 SCAN 游标 bug）。`go build ./...` 全过；`go vet`/`go test` 覆盖改动包，新增 20 个用例全绿（本机 redis db15，无生产依赖）。待主控在生产验证：账号探测真实调用效果、ListQueue 修复后前端/其它调用方是否受影响（此前恒为空，行为变化）。45 前端可基于此契约开工。
- 📦 70 deploy-rollback：SPIDER `8c40e6e` / API `f26023b` / STORAGE `a0e9cf2`，验收中。⚠️ 开发中只读误连 osec-res1 两次（无写操作），已邮件通报、追加硬规则 §7。
- 📦 20 valid-unify：COMMON `7d1712d` / SPIDER `5942c38`+`a48662e` / API `47040af`+`23eba5d`，验收中。阿里改单请求实现；41031 已入码表。
- 记忆仓库同时有另一会话在提交（腾讯文档任务），本任务提交一律用 pathspec `-- agent-tasks ...`。
- 📦 30 startup-selfcheck：SPIDER `4873c60` / API `665d2e8` / STORAGE `50a7d8d`，返工中（STORAGE metrics 端口改可配、README 写清降级语义差异）。
- 📦 50 ci：COMMON `4b522ba` / SPIDER `bdedb7e` / API `94a6356` / STORAGE `a8a376f`，验收中。需用户在 GitHub 配 4 个 secret（COMMON_REPO_TOKEN / PAN_REPO_TOKEN / PAN_CLIENT_CORE_REPO_TOKEN / SPIDER_REPO_TOKEN）。COMMON 重生成了 `common_message.pb.go`、`rpc/storage/rpc.pb.go`（PPIO 描述符修正）——与 valid-unify/health-observe 的 COMMON 分支合并时留意生成物冲突。
- 🔁 80 crawler-skeleton：`e9b4fe6` 只迁 kkpans/feikuai，已打回继续迁其余 4 站。
- ⚠️ 经验：简报里让 ci 角色「跑 `go test ./...` 看连接失败找漏网测试」等于让测试真的连生产；正确做法是 `unshare -rn` 无网络环境下跑。已在验收要求中改正，收尾时提炼进 lessons。
