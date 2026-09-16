# 角色 30：启动自检与依赖降级（提案 5）

短名 `startup-selfcheck`。worktree：`spider-wt-startup-selfcheck`、`api-wt-startup-selfcheck`、`storage-wt-startup-selfcheck`（分支 `feat/startup-selfcheck`）。不改 COMMON。

## 目标

1. 网关 `initEs()` 连不上 ES 直接 panic → 改为「有限重试 + 告警 + 降级启动」，单个依赖故障不能拉不起网关。
2. 三个服务启动时做依赖自检：ES 集群名/别名存在性、redis ping、MySQL ping、下游网关地址可达；结果打一条结构化日志并暴露 Prometheus 指标 `startup_selfcheck{dep,ok}`。
3. 只读工具 `tools/config-audit`（SPIDER 仓库）：读本机指定的多份配置文件（SPIDER/API/STORAGE），对比 ES 主机、redis 地址/db、MySQL 主机是否一致，输出差异表；**永远不打印口令/AK/SK**（打印前脱敏为 `***`）。背景：API 配置的 ES 主机与 STORAGE/网关不一致（`agent-memory/lessons/failure-网关重启暴露ES集群已更换.md`、`failure-resdb的ES端点指向已下线集群.md`）。

## 必读

1. SPIDER `services/gateway/gateway.go` `initEs()`（约 72 行起）与 `Start()` 的模块注册顺序。
2. `agent-memory/lessons/failure-旁路能力初始化拖垮主流程.md`：哪些能 Fatal、哪些必须降级。
3. API `config/elasticsearch.go`、`config/config.go`、`api-starter.go`；STORAGE `db/db.go`、`storage.go`。
4. SPIDER `illuminate/` 下已有的基础设施包（看有没有 prom 指标封装可复用；COMMON `prom/` 也有）。

## 设计

- SPIDER 新包 `illuminate/selfcheck`：`Run(ctx, []Check) Report`，`Check{Name, Critical bool, Fn func(ctx) error}`；`Critical=true` 且失败 → 按配置 `startup.retry`（默认 5 次、间隔 3s 指数）重试，仍失败则返回错误由调用方决定是否退出；非 critical 失败只告警。
  API/STORAGE 不能 import SPIDER，所以把同一份包**复制**为各自的 `internal/selfcheck`（三份代码相同，注释里注明「与 SPIDER illuminate/selfcheck 同源」；本轮不放 COMMON 是为了不与其他角色抢 COMMON）。
- 网关 ES：`initEs` 改为返回 error；ES 不可达时网关仍启动，不依赖 ES 的模块（队列调度、proxy_admin）照常，依赖 ES 的模块（lifecycle、search_admin）注册失败只记日志（已有此语义，确认即可）；后台每 30s 重试建连，成功后热补上。
- 告警复用 `lifecycle/alert.go` 的 `fire()` 风格（若不可达，改成日志即可，不要引入新依赖）。
- 配置节 `startup:`（`retry`、`interval_ms`、`fail_fast *bool` 默认 false），三仓库都要缺省值内置。

## 文件所有权

SPIDER：`illuminate/selfcheck/**`、`services/gateway/gateway.go`（只改 initEs 与调用处）、`config/gateway/gateway.go`（加字段）、`tools/config-audit/**`。
API：`internal/selfcheck/**`、`config/elasticsearch.go`、`config/config.go`（加字段）、`api-starter.go`。
STORAGE：`internal/selfcheck/**`、`db/db.go`、`storage.go`、`config/config.go`（加字段）。

## 验证

三仓库 `go build ./...`；单测：selfcheck 重试/降级逻辑（假 Check）、config-audit 用临时 yaml 对比与脱敏（断言输出不含口令字面量）。

## 交付

分支/提交、文件清单、三服务自检项清单表、测试输出；`config-audit` 对本机三份 dev 配置的运行结果（脱敏后）。
