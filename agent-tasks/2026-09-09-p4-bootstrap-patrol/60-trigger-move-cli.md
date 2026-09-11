# 60-trigger-move-cli —— lc-check 增加 `-trigger-move`（Sonnet，只改代码不部署、不连生产）

先读 00-shared.md §2 硬性约束（不 `git add -A`、不碰 `.vscode/launch.json`、不连生产、不打印凭据）。

## 背景

需要把一批父资源 id 排入生命周期 mover 的搬迁集合（`TriggerMove` RPC：`services/gateway/lifecycle/rpc_service.go` 约 441 行，
proto 见 COMMON `rpc/spider/lifecycle_rpc/lifecycle.proto` `TriggerMoveParam{ids, target, operator}`，`triggerBatchLimit=200`，
`target` 只能 `cur|long`，服务端对每个 id 走 `resolveResource("", id)` 解析失败则跳过、成功则 `enqueueMove` 并写事件，返回 Empty）。
`tools/lc-check/main.go` 现有 flag 风格：`-create-job`/`-control-job`/`-update`/`-operator`，走 `lifecycle_rpc.NewLifecycleRpcClient`。

## 要求

1. 新增 flag：
   - `-trigger-move <文件路径>`：文件每行一个资源 id（空行/`#` 开头忽略，自动去重、保序）。
   - `-move-target cur|long`（缺省 `long`）。
   - `-move-batch N`（缺省 200，上限 200，超过报错）。
   - `-move-sleep-ms N`（缺省 0）：每批之间的间隔，给 mover 留消费余量。
   - `-move-dry-run`：只打印将投递的批数/总数/前 5 个 id，不调 RPC。
   - 复用现有 `-operator`（缺省 `lc-check`）。
2. 行为：按批调用 `TriggerMove`，每批打印「批号/总批数、本批 id 数、耗时、成功或错误」；某批出错**不中断**，继续下一批，最后汇总成功批数/失败批数并列出失败批的首个 id，失败批 id 追加写到 `<文件>.failed`（便于重投）。退出码：全部成功 0，否则 1。
   注意 RPC 返回 Empty，不会告诉你 `enqueued` 数（服务端只写审计）——在输出里明确说明「排入数以服务端审计/事件为准」。
3. 更新 `main.go` 头部用法注释（加一行示例：`-trigger-move ids.txt -move-target long -move-batch 200 -move-sleep-ms 500`）。
4. 验证：`go build ./tools/lc-check`、`go vet ./tools/lc-check`；`-move-dry-run` 对一个含重复/空行/注释的临时 id 文件（放 scratchpad，**不要用真实 id**，随便写 `test-1`…）打印正确的批数与去重结果；`-move-batch 201` 报错。不要连任何真实网关。
5. 提交：只 `git add tools/lc-check/main.go`（如需拆文件可加 `tools/lc-check/*.go`），中文提交信息（如 `feat(lc-check): 增加 -trigger-move 批量排入搬迁`），`git pull --rebase --autostash` 后 push master。

## 交付

用法一行、验证输出摘要、提交 hash。
