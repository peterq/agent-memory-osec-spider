# P5 阶段 D：API 侧 v2→v3 自动灰度分流 —— 共享上下文（2026-09-12）

## 背景

资源 ES 索引生命周期改造 P5 要把搜索流量从 `/api/v2/search`（旧索引 `resource`）切到 v3（新索引 `res_lc_all`）。
原计划由调用方 `dashengpan_web` 改路径切流，用户 09-12 改为：**API 工程自己分流**——
`/api/v2/search` 的请求在服务端按比例改走 v3 的查询实现（`search.SearchV3` / `search.SearchV1V3`），
从 30% 起步、实时监控、无异常则每累计 100 个 v3 请求 +1%，直到 100%；出现异常自动回落到 0% 并告警。
调用方**不需要任何改动**，回滚 = 把比例置 0 或关开关，无需重启。

正本计划：SPIDER `PRD/res-lifecycle/p5-plan-2026-09-12.md` §5（回滚触发条件在 §5.5）。
上线时机由主控决定（阶段 C 复测通过后），**本任务只做代码 + 单测 + 文档，缺省关闭**。

## 仓库

| 简称 | 路径 | module | 说明 |
|---|---|---|---|
| API | `/home/peterq/dev/projects/1s/osec-resource-api` | `github.com/1s/enfi-resource-api` | 本任务唯一改动仓库 |
| SPIDER | `/home/peterq/dev/projects/1s/osec-spider-go` | 只读参考 | `services/gateway/lifecycle/alert.go` 的告警投递方式；`services/proxy-provider` 的 redis 分钟桶统计 |

## 硬性约束（违反即返工）

- `services/search/search.go`（SearchV1/SearchV2）与 `services/search/search_v3.go` **不允许出现在 diff 里**：分流只在 controller 层选择调用哪一个实现。
- **开关缺省关闭**：`search_canary.enabled` 缺省 false 时 `SearchApi` 的行为与现在逐字节一致（含日志字段）。
- 响应结构不变：v3 返回的 `search.Results` 原样走既有 `encryptData`/`util.Response` 路径。
- 两台 API 主机（res1/res2）共享灰度状态：比例、累计计数、暂停标记、窗口统计全部放 redis（`config.GetRedis()`），进程内不保存权威状态。
- 生产凭据在 `_note/config/*.yaml`，**禁止明文进代码/测试/文档/汇报**。
- 中文注释；错误用 `github.com/pkg/errors`；沿用同包风格（先读 `controller/api.go`、`controller/api_v3.go`、`services/parallel-control/`）。
- git：不加 `Co-Authored-By`；commit message 中文，前缀 `feat(search-canary): …`；**完成后 commit 并 push master**，被拦则如实汇报。
- 禁止 Monitor / 后台任务；单测不联网、不连生产 redis（用 miniredis 或接口 fake；仓库若已有 redis 测试桩就复用）。
- 不部署、不改生产配置、不写生产 redis。

## 验证命令

```bash
cd /home/peterq/dev/projects/1s/osec-resource-api && go build ./... && go vet ./controller/... ./services/... && go test ./services/search-canary/... ./controller/...
```

## 交付格式

汇报 ≤400 字中文：改了哪些文件（路径:行）、测试结果（命令 + 原文）、commit hash、push 状态、**明确列出未做/无法验证的项**。不要复述代码。
