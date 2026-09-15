---
title: 决策：P5 阶段 D 切流改由 API 工程服务端自动灰度分流（30% 起、每 100 个 v3 请求 +1%）
type: decision
status: active
created_at: 2026-09-12T22:45:00+08:00
updated_at: 2026-09-15T14:20:00+08:00
priority: high
keywords: [阶段D, 灰度, 分流, search_canary, v3切流, 自动回落]
questions:
  - 搜索流量怎么从 v2 切到 v3，谁来切
  - search_canary 是什么，比例怎么涨、异常怎么回滚
summary: 用户 09-12 裁定：API 在 /api/v2/search 服务端按比例走 v3，30% 起、无异常每 100 个 v3 请求 +1% 到全量，异常自动回落 0% 并告警，状态存 redis
load: on-demand
related:
  - agent-memory/decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md
  - agent-tasks/2026-09-12-p5-stage-d-canary/10-api-canary.md
---

# 决策：阶段 D 改由 API 侧自动灰度分流

## 背景
p5-plan §5 原定由唯一调用方 `dashengpan_web` 改请求路径切流（先 `searchType=match` ~20% → 3 天 → 全量），需跨部门对接。

## 最终决策（[用户确认 2026-09-12]）
API 工程在 `/api/v2/search` 的 controller 层分流：命中则按同样的 `v` 映射调 `search.SearchV3`/`SearchV1V3`；
起始 30%，实时监控，若无异常每累计 100 个 v3 请求 +1%，最终全量；调用方零改动。

## 实现要点（简报 `agent-tasks/2026-09-12-p5-stage-d-canary/`）
- 包 `services/search-canary`，开关 `search_canary.enabled` 缺省 false；状态（percent/paused/计数）与 v2/v3 分钟桶统计放 redis，res1/res2 共享。
- 异常判据沿用 p5-plan §5.5：v3 错误率 >0.1% 或慢占比 > v2×1.5（30 min 窗口、样本 ≥200）→ 比例归 0 + paused + 告警；人工 `-resume`/`-set` 恢复。
- `search.go`/`search_v3.go` 不进 diff；redis 任何错误按 v2 降级。
- CLI `tools/search-canary`：`-status/-set/-pause/-resume/-reset`。

## 影响
- 回滚不再依赖调用方：`-set 0` 或关开关，无需重启。
- 启用前置仍是 D4：阶段 C 门槛全过；且须等 lifecycle_checker 误删事故止血与恢复方案确定后再定启用时点（`lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`）。

## 复盘条件
全量后 3 天无异常 → 阶段 D 完成；若自动回落 ≥2 次，回到阶段 C 找原因而不是调阈值。

## 当前状态
**已完成开发** API `6bbbfb8`（主控复核 controller 接入与 `decideStep`；build/test 过），缺省关闭、未部署。
启用步骤见 API `services/search-canary/README.md`：配置 `search_canary.enabled: true` + `notify_url` → 重部 res1/res2 → `go run ./tools/search-canary -status`。
⚠️ 参数提醒：按"每 100 个 v3 请求 +1%"，30% 起在实际流量下 30%→100% 可能只需几十分钟；若要贴近 p5-plan 的 3 天观察，把 `step_every_v3_requests` 调大（如 20,000）。

**执行（09-15）**：08:47/08:50 两台宿主机 `config.yaml` 追加 `search_canary` 生效（rollout §17）；用户 14:05 把步长改为每 4,000 个 v3 请求 +1%，并要求每半小时邮件汇报（`osec-resource-api/scripts/search_canary_report.sh`）。首 20 分钟 v3 占 32%、错误 0、v3 P50/P95 151/608 ms 优于 v2 290/1305。
