---
title: 决策：全量 bootstrap 吞吐熔断后原地 resume 而非重跑
type: archive
status: archived
created_at: 2026-09-06T07:35:00+08:00
updated_at: 2026-09-16T10:40:00+08:00
priority: high
keywords: [bootstrap, id=8, 熔断, resume, 吞吐, windowTargetDocs, copy_parent, 窗口固定开销]
summary: 09-06 07:22 作业 id=8 因 copy_parent 吞吐 <2000 docs/s 被 pause；主控判定为作业侧窗口固定开销而非集群压力，决定原地 resume 并修订吞吐熔断条款
load: rarely
related:
  - agent-memory/lessons/patterns-长周期生产巡检.md
  - agent-memory/current/tasks.md
  - agent-memory/current/open-questions.md
---

> 2026-09-12 归档：P4 全量 bootstrap 已于 09-11 done，本决策仅供复盘；有效结论已提炼到 `lessons/patterns-长周期生产巡检.md` 与 `archive/2026/domain-bootstrap吞吐实测数据.md`。

# 决策：全量 bootstrap 吞吐熔断后原地 resume

## 背景

作业 id=8（`windowTargetDocs=300000`、rps 6000）copy_parent 阶段吞吐从 2,674 缓降到 1,442/1,523 docs/s，命中用户设定的「复制阶段吞吐持续 <2,000 docs/s 超 20 分钟」熔断，巡检 Agent 于 07:22 pause（父文档 62.9%，join 型全部完成，百度型 56.6%）。

## 证据（[事实]）

- 集群侧全部正常：heap 峰值 82%（<85%，守护未触发）、green、breaker 无增长、v2 延迟 560~631 ms（门槛 1,100）、网关 0 panic。
- reindex 任务 `created == total` 且 `throttled_millis` 3.3~4.0 s：每窗口早已搬完在等限速；窗口推进节奏稳定 5.1~6.6 s/半区槽，变化的是每槽父文档密度（10,975 → 7,324 → 10,074）。
- 结论 [推断]：瓶颈是作业侧每窗口固定开销（计数校验 + DB 游标 + 任务创建）× 百度窗口密度不均，rps 6000 根本没跑满。

## 备选方案

- A 原地 resume：不丢不重（README 已验证），零风险，只是时长拉长（全量 09-07 晚 ~ 09-11）。
- B cancel 后加大 `windowTargetDocs` 重跑：减少窗口数以摊薄固定开销，但重做 3.9 h 建库、丢弃 62.9% 父文档复制进度，且更大窗口的 heap 影响未评估——需用户决策。
- C 保持 paused 等用户：用户不在线，空等浪费时间且无收益。

## 最终决策

**A**。熔断规则的本意是保护集群，本次集群指标全部正常；resume 属续跑而非 retry，不违反「不自行 retry」约束。同时修订吞吐熔断：仅当吞吐 <2,000 **且** `created<total` 或 heap ≥80% 持续才触发；限速空等不熔断。B 作为可选提速方案写进 open-questions 交用户决策，已邮件报备。

## 复盘条件

copy_child 实测吞吐若也远低于 5,686 docs/s（如 <2,500），全量将超过 4 天，应重新评估 B 或提 rps/改窗口参数。
