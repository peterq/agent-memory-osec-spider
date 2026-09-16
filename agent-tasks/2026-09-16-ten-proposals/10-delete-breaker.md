# 角色 10：删除熔断器（提案 3）

短名 `delete-breaker`。worktree：`common-wt-delete-breaker`、`spider-wt-delete-breaker`、`api-wt-delete-breaker`（分支 `feat/delete-breaker`）。

## 目标

所有「判失效 → 删 ES 文档 / 标失效」的路径统一接一个熔断器：按滑动时间窗口统计失效判定的**绝对数**与**占比**，
任一超阈值即自动停机（拒绝继续删除、把结果改成 error 走重试或落队列）并告警；人工确认后手动恢复。
09-12 事故一小时删了百万条，熔断要把损失压到千级。`agent-memory/procedures/checklist-不可逆操作上线.md` 是靠人执行的清单，本任务把它做进代码。

## 必读

1. `agent-memory/lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`：事故形态（invalid 比例骤升、ok=0），阈值设计以此为准。
2. SPIDER `services/gateway/lifecycle/result.go`：`applyCheckResult`/`onCheckInvalid` 是 lc 链路失效落地点；`stats.go` 已有分钟桶计数器 `resLc:cnt:*`（可复用作窗口数据源）；`alert.go` `fire()` 告警邮件写法（redis SETNX 去抖）。
3. SPIDER `services/gateway/res_scheduler/clear_expire.go`：旧链路 `HandleTask`→`deleteByEsDocId` 删旧索引。
4. SPIDER `services/lifecycle_checker/checker.go`：检测端；熔断触发后检测端也应停止投递失效结果（读同一 redis 状态键）。
5. API `services/valid/valid.go`（约 150~185 行）与 `valid_v3.go`（约 115~140 行）：API v2/v3 `validShareLink` 判失效后直接删 ES 的两处。
6. `agent-tasks/2026-09-16-share-search-overview/00-shared.md` §4.2 redis 键约定风格、§4.4 网关配置节写法。

## 设计（定稿，实现细节自定）

- COMMON 新包 `guard/delbreaker`（无第三方依赖除 go-redis）：
  - `New(rds redis.Cmdable, conf Config) *Breaker`；`Config{Name, WindowSec(默认 600), MaxInvalidAbs(默认 2000), MaxInvalidRatio(默认 0.5), MinSamples(默认 200), Enabled(*bool 默认 true)}`。
  - `Record(kind string /*valid|invalid|error*/, typ string)`：写分钟桶 `delbreaker:<name>:<typ>:<kind>:<yyyymmddHHMM>`（TTL = 2×窗口）。
  - `Allow(typ string) (ok bool, reason string)`：先看熔断状态键 `delbreaker:<name>:tripped:<typ>`（存在即拒绝）；再算窗口内 invalid 绝对数与 invalid/(valid+invalid) 比例，超阈值就 `SETNX` 状态键（无 TTL，人工恢复）并返回 false + reason。
  - `Reset(typ)` 人工恢复；`Status()` 供 RPC/工具展示。
  - redis 不可用 → **fail-open 并记录限频日志**（旁路不能拖垮主流程）。按网盘 `typ` 分别熔断，一个网盘出事不影响其他。
  - 单测（miniredis）：阈值触发、比例触发、样本不足不触发、tripped 后 Allow=false、Reset 恢复、redis 挂掉 fail-open。
- SPIDER 网关：`lifecycle` 与 `res_scheduler/clear_expire` 各持一个 Breaker（name 分别 `lc`、`legacy`），删除前 `Allow`，结果 `Record`；
  被熔断的任务**返回 error 让队列重试**（不要 ack 成功），并调用 `alert.fire` 风格告警（去抖 10 分钟）。
  配置节 `services.lifecycle.breaker` / `services.res_scheduler.breaker`，全部缺省值内置。
  `lifecycle_checker`：`BeforePop` 里读 tripped 键，tripped 时暂停投递并打限频日志（不需要精确，30s 缓存即可）。
- SPIDER 工具 `tools/delbreaker-ctl`：`-status` / `-reset -type quark`，只读 redis + 写状态键，用网关配置里的 redis。
- API：两处删除前 `Allow`（name `api-valid`，配置节 `valid.breaker`），失效判定与删除结果 `Record`；被熔断时**不删且接口返回 `-1` 未知态**（不对外返回失效）。
- COMMON 写 `guard/delbreaker/README.md`（≤40 行：键名、阈值含义、如何 reset、fail-open 语义）。

## 文件所有权

COMMON：`guard/delbreaker/**`。SPIDER：`services/gateway/lifecycle/{result.go,breaker.go(新),alert.go 仅加函数}`、`services/gateway/res_scheduler/clear_expire.go`、`services/lifecycle_checker/checker.go`、`config/gateway/gateway.go`（只加字段）、`tools/delbreaker-ctl/**`。API：`services/valid/{valid.go,valid_v3.go}` **只改删除前后那几行**（另一角色 `valid-unify` 会重写 checker 内部逻辑，勿动判定代码）、`config/config.go`（只加字段）、`api-starter.go` 注入。

## 验证

`go build ./...` 三仓库；`go vet`/`go test` 覆盖 `guard/delbreaker`、`services/gateway/lifecycle`、`services/gateway/res_scheduler`、API `services/valid`。

## 交付

分支/提交、文件清单、阈值缺省值表、测试输出、需主控在生产核对的点（如现网 10 分钟窗口的正常 invalid 基线，用于校准阈值）。
