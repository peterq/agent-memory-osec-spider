# 角色 10：SPIDER 网关 —— D1 legacy→lc 失效同步钩子

## 目标

旧清理队列 `clearExpire` 的消费者 `res_scheduler.cleaner.HandleTask` 在完成"删旧索引 + `AddInvalidResLink`"后，
**通知 lifecycle**：若该资源在 `res_lc_*` 分表里 `status=1` 且 `next_check_at > now`，把 `next_check_at` 提前到 now，
让 lc 扫描器在下一轮（≤ `scan_interval_sec` 30 s）把它捞去复检；判失效走既有 `clear.go`。

## 必读文件（按顺序）

1. `services/gateway/res_scheduler/clear_expire.go` —— 改动落点 `HandleTask`/`cleaner`/`StartClearConsumer`。
2. `services/gateway/res_scheduler/res_scheduler.go` L60-100 —— `ResSchedulerConfig`/`NewResScheduler` 是注入口。
3. `services/gateway/gateway.go` L338-405 —— 装配顺序：`NewResScheduler` 先于 `lifecycle.Register`，而 lifecycle 的 `*Service` 在 `Register` 内部创建、不返回。**你要解决这个先后问题**（见"设计"）。
4. `services/gateway/lifecycle/register.go`、`service.go` —— `Register`/`NewService`/`enabled()`/`writeEvent`。
5. `services/gateway/lifecycle/dao.go` L220-350 —— `GetById`/`DeferNextCheck`/`MarkInvalid` 的写法，新方法照这个风格。
6. `services/gateway/lifecycle/clear.go` —— 理解 lcClear→pushLegacyClear→clearExpire 的回流，确认**不成环**。
7. `services/gateway/lifecycle/models.go` L14-35, L88-100 —— 字段与事件枚举（`Event` 列 varchar(24)）。
8. `services/gateway/lifecycle/metrics.go` L60-90 —— 指标注册方式。
9. `services/gateway/lifecycle/config.go`、`params.go` —— 静态配置 + `applyDefault` 的写法（要加一个静态配置项）。
10. `services/gateway/lifecycle/queues.go` L30-70 —— 注意 lifecycle **刻意不 import res_scheduler**（避免循环依赖），所以接口要定义在 res_scheduler 侧，lifecycle 只是结构上实现它。
11. `services/gateway/lifecycle/dao_test.go`、`clear.go` 相关测试、`services/gateway/res_scheduler/pre_check_smoke_test.go` —— 测试怎么写（用什么 DB/mock）。
12. PRD 正本 `PRD/res-lifecycle/p5-plan-2026-09-12.md` §2.1~2.3。

## 设计（已由主控裁定，不要另起方案）

### res_scheduler 侧
```go
// LegacyInvalidHinter 旧链路判失效后通知生命周期模块"提前复检"的最小接口, 由 lifecycle.Service 实现。
// nil 表示 lifecycle 未接入, 钩子整体跳过 —— v2 链路行为不变。
type LegacyInvalidHinter interface {
    HintLegacyInvalid(typ, shareId, resId string) // 不返回 error: 旁路能力, 失败只在实现内部记日志/打点
}
```
- `ResSchedulerConfig` 加字段 `LegacyInvalidHinter LegacyInvalidHinter`；`cleaner` 持有它。
- `HandleTask` 在 `AddInvalidResLink` 成功后调用 `c.hinter.HintLegacyInvalid(task.Type, task.ID, utils.Md5str(link))`（resId 与前面删 ES 用的同一个 md5）。
  钩子**不影响返回值**：hinter 为 nil 直接跳过；调用放在最后，任何 panic 都不能冒出来（实现里 recover 或保证不 panic）。
- `StartClearConsumer` 签名可以改成接 `ResSchedulerConfig` 或多加一个参数，二选一，保持调用点最少。

### lifecycle 侧
- `Service` 增加方法 `HintLegacyInvalid(typ, shareId, resId string)`：
  1. `!s.enabled()` → 直接 return（打点 `skipped_disabled` 可选）。
  2. `normalizeType(typ)` 不认识 → return。
  3. 限速：静态配置 `Config.LegacyHintPerMin int`（yaml `legacy_hint_per_min`，缺省 0 = 不限）；超限 → 打点 `rate_limited` 并 return。
     用一个简单的进程内滑动窗口/令牌桶即可（不引入新依赖），放在 `Service` 上，并发安全。
  4. `row, err := s.dao.GetById(typ, resId)`；err → 记日志 + 打点 `error`；nil → `skipped_no_row`；`row.Status != StatusActive` → `skipped_status`；`!row.NextCheckAt.After(now)` → `skipped_due`（已到期，扫描器本来就会捞）。
  5. 否则 `s.dao.AdvanceNextCheck(typ, resId, now)`：`UPDATE <table> SET next_check_at=? WHERE id=? AND status=1 AND next_check_at > ?`（条件写进 SQL，避免与扫描器/回写并发时倒退）。返回受影响行数；=0 也算 ok（并发已处理）。
  6. `s.writeEvent(resId, typ, EventLegacyInvalidHint, row.IndexName, "", "legacy clearExpire hinted, shareId=<...>", "legacy-hook")`；新增常量 `EventLegacyInvalidHint = "legacy_invalid_hint"`（19 字符 < 24）。
  7. 指标 `res_lc_legacy_hint_total{type,result}`，result ∈ advanced/skipped_no_row/skipped_status/skipped_due/rate_limited/error。
- `README.md`（lifecycle 包内）补一节「旧链路失效同步钩子」：链路图、不成环的理由、限速配置、指标名。

### 装配（gateway.go）
- 把 `lifecycle.Register` 拆成两步或让它返回 `*Service`：推荐 `lifecycle.Register(...) (*Service, error)`，
  然后 `res_scheduler` 侧提供 `resScheduler.SetLegacyInvalidHinter(svc)`（或在 `ResScheduler` 接口上加此方法，
  内部原子替换 cleaner 的 hinter；`clearExpire` 消费者在 `NewResScheduler` 就已经跑起来了，所以 hinter 必须用
  `atomic.Pointer`/mutex 保护）。
  两种做法任选其一，但**注册失败或 lifecycle 未启用时钩子必须是空操作**。
- 注意 `Register` 返回错误的分支现在只 `log.Println`，保持不阻断网关启动。

### 不成环自证（写进 README 与单测注释）
lcClear(`doClear`)：删 lc 索引 → `AddInvalidResLink` → `MarkInvalid`(status=2) → `pushLegacyClear` → `clearExpire.HandleTask` → 钩子 `GetById` 得 status=2 → skip。

## 测试

- 单测 `res_scheduler`：`HandleTask` 用假 hinter 记录调用；覆盖 hinter=nil（不调用、返回值不变）与 hinter 非 nil（被调用一次、参数正确）。ES 与 resDao 用现有测试里的 mock/fake 方式；若包内没有可用 fake，最小化地为 `deleteByEsDocId` 抽接口，**不要改动业务逻辑**。
- 单测 `lifecycle`：`HintLegacyInvalid` 三分支（无行 / status=2 / status=1 且 next 在未来）+ 限速分支。看 `dao_test.go` 用的是什么 DB（sqlite in-memory 或 IT env）照做。
- 联网集成（可选，仅当 `scripts/lifecycle_it_env.sh` 能在本机跑起来）：造一条 `status=1` 且 `next_check_at=+1d` 的行，直接调 `HintLegacyInvalid`，断言 DB `next_check_at<=now` 且事件表有 `legacy_invalid_hint`。跑不起来就在汇报里写明"IT 未跑"。
- `go build ./... && go vet ./services/gateway/... && go test ./services/gateway/res_scheduler/... ./services/gateway/lifecycle/... -run '<你新增的测试名|已有相关测试>' -count=1`。全包 `go test ./services/gateway/lifecycle/...` 若有依赖外部环境的用例失败，把失败原文贴出来并说明是否与本次改动相关。

## 交付

按 00-shared.md 的交付格式。额外列出：接口定义位置、限速配置键名、指标名、事件常量名、`Register` 签名是否改动。
