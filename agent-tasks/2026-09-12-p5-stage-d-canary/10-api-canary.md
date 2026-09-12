# 角色 10：API —— `services/search-canary` 包 + `SearchApi` 接入

## 必读
1. `controller/api.go` `SearchApi`（L131 起）—— 参数解析后 `v=="1"` 走 `search.SearchV1`、`v=="2"` 走 `search.SearchV2`（L279-283）。
2. `controller/api_v3.go` `SearchApiV3` —— v3 的镜像分派：`v=1 → search.SearchV1V3`、`v=2 → search.SearchV3`；灰度命中时**按同样的 v 映射**调 v3 实现。
3. `api-starter.go` L30-60 与 L85-105 —— 既有 prometheus 指标注册与中间件写法，新指标照此注册。
4. `services/parallel-control/` —— 本仓库用 redis 做共享控制的既有写法（`config.GetRedis()`、go-redis v6 API）。
5. `config/config.go` —— 加配置节的位置；`config.yaml`/`config_dev.yaml` 加缺省示例（enabled: false）。
6. SPIDER `services/gateway/lifecycle/alert.go` `fire()`（L276-305）—— 告警投递：POST JSON `{subject, htmlContent, source}` 到 notify_url，redis SetNX 去抖。**照抄投递格式**，notify_url 走配置（生产值主控上线时填，与 SPIDER `services.lifecycle.alert.notify_url` 同一个接口）。
7. SPIDER `PRD/res-lifecycle/p5-plan-2026-09-12.md` §5.3/§5.5 —— 观察项与回滚触发条件（下面已换算成参数）。

## 交付 (1)：`services/search-canary` 包

### 配置 `search_canary`（`config.SearchCanaryConfig`，全部有缺省值）
| 键 | 缺省 | 说明 |
|---|---|---|
| `enabled` | false | 总开关；false 时 `Decide` 恒返回 v2 且不碰 redis |
| `initial_percent` | 30 | 首次启用时写入 redis 的起始比例（redis 已有值则不覆盖） |
| `step_percent` | 1 | 每次自动上调的幅度 |
| `step_every_v3_requests` | 100 | 每累计多少个 v3 请求评估一次上调 |
| `max_percent` | 100 | 上限 |
| `healthy_window_sec` | 1800 | 上调前要求"最近这么久无异常" |
| `error_ratio_max` | 0.001 | v3 5xx/内部错误占比上限（§5.5：0.1%） |
| `slow_ms` | 2000 | 慢请求阈值 |
| `slow_ratio_factor` | 1.5 | v3 慢占比 > v2 慢占比 × 该系数 判异常 |
| `min_sample` | 200 | 异常判定的最小 v3 样本（窗口内不足则不判） |
| `notify_url` | "" | 空则只写日志 |
| `key_prefix` | `resSearchCanary:` | redis 键前缀 |

### redis 状态（hash `<prefix>state`）
`percent`（当前比例，0~100）、`paused`（0/1，异常回落后置 1，人工恢复前不再自动上调）、`v3_since_step`（自上次评估以来的 v3 计数）、`updated_at`、`last_reason`（最近一次变更原因，人读）。
窗口统计：分钟桶 `<prefix>m:<backend>:<yyyymmddHHMM>` hash 字段 `total/error/slow`，TTL 2 h（照 SPIDER proxy-provider 分钟桶的思路，不必复用其代码）。

### 接口
```go
type Decision struct{ Backend string /* "v2"|"v3" */; Percent int }
func (c *Canary) Decide(ctx) Decision                      // enabled=false → v2；paused 不影响已定比例（只是不再上调）
func (c *Canary) Observe(backend string, status int, dur time.Duration)  // 写分钟桶；backend=="v3" 时 v3_since_step++，到 step_every 触发一次 evaluate
func (c *Canary) evaluate(ctx)                             // 见下
func (c *Canary) Snapshot(ctx) (State, error)              // 供后台/CLI 读
func (c *Canary) Set(ctx, percent int, reason string) / Pause / Resume
```
`evaluate` 逻辑（纯函数 `decideStep(stats, state, conf) (newPercent int, pause bool, reason string)` 单独抽出便于单测）：
- 取最近 `healthy_window_sec` 内 v2/v3 桶汇总；v3 样本 < `min_sample` → 不动。
- **异常**：v3 error/total > `error_ratio_max`，或 v3 slow/total > v2 slow/total × `slow_ratio_factor`（v2 样本为 0 时只看 v3 slow/total > 0.2）→ `percent=0, paused=1`，告警（去抖 30 min），写 `last_reason`。
- 健康且未 paused 且 percent < max → `percent += step_percent`（封顶 max），`v3_since_step=0`。
- 分流抽样用 `rand.Intn(100) < percent`，不做一致性哈希（无状态请求，无需粘性）。
- `Decide`/`Observe` 任何 redis 错误**只记日志、按 v2 处理**（旁路能力不能拖垮搜索；参考记忆 `lessons/failure-旁路能力初始化拖垮主流程.md` 的教训：初始化失败也必须降级而不是 panic）。

### 指标（注册进既有 prometheus）
`search_canary_percent`（gauge）、`search_canary_requests_total{backend, outcome=ok|error|slow}`、`search_canary_transitions_total{kind=step|pause|manual}`。

## 交付 (2)：`SearchApi` 接入（`controller/api.go`）
- 在 v 分派处：`d := s.canary.Decide(ctx)`；`d.Backend=="v3"` 时 `v=="1"→search.SearchV1V3`、`v=="2"→search.SearchV3`（参数与 `SearchApiV3` 逐项一致，含 `resType`）。
- 日志 `logData["backend"]=d.Backend`、`logData["canaryPercent"]=d.Percent`（enabled=false 时**不加**这两个字段，保持日志逐字节一致）。
- defer 里 `s.canary.Observe(backend, httpStatus, duration)`；`searchError != nil` 记 status 500。
- `EnfiResourceApi` 构造处注入 `*canary.Canary`（照 `parallelControl` 的注入方式）。

## 交付 (3)：CLI `tools/search-canary`（go run，经 ssh 隧道连生产 redis 不在本任务范围，只连配置里的 redis）
`-status` 打印 State + 最近 30 min v2/v3 total/error/slow；`-set 30 -reason "…"`、`-pause`、`-resume`、`-reset`（删 state 与桶）。写操作打印前后值。顶部用法注释照 SPIDER `tools/lc-check/main.go` 的风格。

## 交付 (4)：文档
`services/search-canary/README.md`（中文）：为什么在 API 侧分流、状态/参数表、启用步骤（改配置 `enabled: true` → 重部 → `-status` 看比例 30 → 观察）、异常回落后如何恢复（`-resume` 或 `-set`）、回滚（`-set 0` 或 `enabled: false`）、观察命令（SLS 按 `backend` 字段拆 v2/v3 的耗时与 5xx；prometheus 指标名）。

## 单测（必须）
- `decideStep` 表驱动：健康上调、封顶、样本不足不动、error 超限回落+pause、slow 比例超限回落、paused 不上调、v2 无样本时的兜底。
- `Decide` 在 enabled=false 时恒 v2 且不访问 redis（用 fake 断言零调用）。
- redis 分钟桶写读用 miniredis（`github.com/alicebob/miniredis/v2`，若 go.mod 没有则加；不要连真实 redis）。

## 验证
见 00-shared.md。另：`go run ./tools/search-canary -h` 能打印用法。
