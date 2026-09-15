---
title: 决策：v2 延迟熔断后以 rps 2500 起步 + 动态峰值守护续跑全量 bootstrap
type: archive
status: archived
created_at: 2026-09-06T11:50:00+08:00
updated_at: 2026-09-16T10:40:00+08:00
priority: high
keywords: [bootstrap, id=8, v2 延迟, 熔断, rps, 动态峰值, 守护, rethrottle, res_lc_job params, lc_adaptive_rps]
summary: 11:08 v2 搜索延迟 13.5× 熔断后，用户选择 rps 2500 起步并由监测程序按 10 分钟区间的慢请求占比动态调峰续跑；参数经 UPDATE res_lc_job 持久化 + _rethrottle 即时生效
load: rarely
related:
  - agent-memory/archive/2026/decision-2026-09-06-全量bootstrap熔断后原地resume.md
  - agent-memory/lessons/patterns-长周期生产巡检.md
  - agent-memory/current/tasks.md
---

> 2026-09-12 归档：P4 全量 bootstrap 已于 09-11 done，本决策仅供复盘；有效结论已提炼到 `lessons/patterns-长周期生产巡检.md` 与 `archive/2026/domain-bootstrap吞吐实测数据.md`。

# 决策：动态峰值 rps 守护续跑

## 背景

作业 id=8 copy_parent 尾段（94%）rps 6000 把 v2 搜索延迟推到 5,469 ms（基线 404），事故核心 25 分钟内 743 次真实搜索 43% >2 s、21% >5 s、最慢 57 s、无 5xx。pause 后 8 分钟回落。copy_child 数据量是父文档 15 倍，原参数续跑必再击穿。

## 已证实的事实

- [事实] `runBootstrapJob` 每次进入（含 resume）从 `res_lc_job.params` 重新解析参数，运行中不重读；无改参数 RPC，`UPDATE res_lc_job SET params=JSON_SET(...)`（paused 态）是唯一且合理的路径，不丢进度。
- [事实] 每个新窗口 reindex 以 params 的 rps 起步；`_rethrottle` 对 sliced 父任务生效。
- [事实] 网关自带守护只在 copy_child 阶段启动，且只看 heap（`latencyProbe` 从未注入）；copy_parent 阶段无任何自动降速——本次事故就发生在无守护阶段。
- [事实] `windowTargetDocs` 已缓存进 `progress.windows`，现在改它不生效也不丢进度；copy_child 复用 join 窗口缓存；窗口按父文档数配平，不保证子文档数配平。

## 备选方案

A rps 2500 立即续跑（≈3.6 天）；B 仅夜间跑（7~11 天）；C A + 低峰试探 4000（≈2.3 天）；D 先补守护再跑（0.5~1 人日）。

## 最终决策（[用户确认 2026-09-06 11:45]）

**A + 动态峰值，由监测程序守护执行**：起始 peak 2500；每 10 分钟区间统计 res2 `GET:/api/v2/search` 慢请求（>2 s）占比 r：r<40% → peak+=1000；40%≤r≤50% → 维持；r>50% → **peak 立即减半（最低 1000），pause 2 分钟后以减半后的 peak resume**（[用户修正 11:55]）。
主控补充安全边界（用户确认）：peak 上限 10000（**[用户修正 2026-09-06 19:00] 提高到 18000**，因 r 仅 10~20% 而 throttled 占比 50%，被上限封顶）；区间样本 <30 视为稳定可加档，但此时上限为正常上限的 60%（6000）（[用户修正 11:55]）；heap ≥85% 连续 15 s → rethrottle 到 max(1000, peak/2) 且本区间禁加档，10 分钟不回落 → pause；非 green / failed / breaker 增长 / 网关容器变化 → pause + 邮件 + 守护退出。双通道施加：UPDATE params 持久化 + 5 秒轮询 `_rethrottle` 即时生效。实现为 SPIDER `scripts/lc_adaptive_rps.sh` + `scripts/lc_v2_slow_ratio.sh`。

## 复盘条件

- 夜间样本少导致 peak 顶到上限后 heap 触发硬熔断 → 调低上限。
- 后续排期：把 heap/延迟守护提升到 `runBootstrapJob` 级并注入真实 v2 延迟探针（0.5~1 人日）。
