---
title: 会话摘要：P4 全量 bootstrap 接管巡检（第 19~26 轮）与校验失败取证
type: session
status: active
created_at: 2026-09-11T06:30:00+08:00
updated_at: 2026-09-12T02:40:00+08:00
priority: high
keywords: [bootstrap, id=8, 巡检, 网关重部, 883daeb, verify 失败, repair, 双索引副本, shortfallSlices, rollout §12]
summary: 09-09 12:00 接管：核实网关重部完成、派 8 轮 Opus 巡检直至作业 09-11 05:16 以 failed 终结、只读取证给出 repair→retry 恢复路径与 5 项用户决策、rollout §12 落盘
load: on-demand
related:
  - agent-memory/current/tasks.md
  - agent-memory/lessons/patterns-长周期生产巡检.md
  - agent-tasks/2026-09-09-p4-bootstrap-patrol/
---

# 会话摘要

## 完成事项

- 接手时现场核查：旧会话 Opus 部署 Agent 仍存活并正在操作 res2，未并发介入，观察至其走完「res2 12:04 → resume 12:13 → 守护 12:17」；核对 md5/panic/热更新参数/leader。
- 第 19~26 轮巡检（Opus，每轮 ≈5 h，独立隧道 18085，简报落盘 `agent-tasks/2026-09-09-p4-bootstrap-patrol/`），全程零生产介入，仅 4 次自建隧道重建。
- 作业 id=8 09-11 05:16 终结 `failed`（verify：cur 差 0.107%），copy_child 跑满 1620/1620；守护自行退出。
- 校验取证（Opus 只读）：long 也超标（ES 多 59,565，0.146%）、cur 零漏搬、long 盈余为同 id 双索引副本、shortfall 89 条缺口 420 万（2026-06 整窗 dst=0）。
- rollout `PRD/res-lifecycle/rollout-2026-09-05.md` §12（SPIDER `26337bd`）；`lc_patrol_sample.sh` 两处修正（`8a3d25a`、`fefbf10`）；取证只读脚本固化派 sonnet 执行中。
- 记忆：patterns #67~#89（23 条），tasks/overview/index 逐轮同步，共 12 次 commit+push。

## 关键发现

- resume 后被清掉的旧 `failedSlices` 不在 `done` 集合，会被自动重跑（5.5 h），逐条记入 `shortfallSlices`。
- `_count` 差分在晚间会被业务 `delete-by-query` 抵消出现净负；尾段改槽口径。
- 白天吞吐 ≈ 夜间 61%，与 r% 强负相关；完成估算必须昼夜加权。
- `bootstrapVerify` 首个索引失败即 return，另一半从未对拍；差额要分方向（DB>ES vs ES>DB）。

## 做出的决策

- 主控：不并发接管旧会话正在做的部署；巡检 Agent 用独立端口；尾段 15 分钟采样；取证只读、不自行跑 repair。

## 09-11 用户决策后的执行（续）

- 用户决策：cancel id=4 / repair 白天跑 / skipEsToDb=false → repair id=10（2h55m）→ 复核 → retry id=8 **10:25 done**。
- shortfall 只读分析推翻前提（longBoundary 漂移致父子跨索引，零丢失）；用户决策 lc-check 加 `-trigger-move` / 只修相关 / 放宽 → DB 枚举 102,601 父 → mover 归位 09-11 18:09 → 09-12 02:17 完成，终态对拍 0.001% 级。
- 观测侧事故 1 次（子 Agent 在 legacy 跑 has_child 致节点重启，red 27 min，无数据丢失），已加 ES 只读白名单硬约束。
- 代码：`3b8cc13`/`aac5f84`/`61cf1db`/`e856540`/`93f4d38` 已提交未部署。

## 后续行动（原记录，已完成）

1. repair 守卫：`force:true` 还是 cancel id=4；2. repair 时间窗（建议夜间低峰）；3. `skipEsToDb`；4. shortfall 补搬优先级；5. 之后 retry id=8 → done。
代码待改：`bootstrapVerify` 两索引都对拍后再汇总。

## 值得沉淀的经验

- 见 patterns #67~#89；子 Agent 简报按「00-shared / 10-patrol / 90-verify / 91-verify-failed / 20-scripts」分文件，prompt 只给路径，主控每轮只改口径补充段，有效。
- 安全：`docker inspect` 打印 Env 会把 OSS AK/SK 带进会话记录（本次发生一次），核对容器时只 grep 非敏感字段。
