---
title: 失败经验：repair 对账作业在 bootstrap 未完成时把 DB 行误标为 deleted
type: lesson
status: active
created_at: 2026-09-06T07:45:00+08:00
updated_at: 2026-09-06T09:20:00+08:00
priority: critical
keywords:
  - repair
  - 对账
  - bootstrap
  - status=3
  - db_to_es
  - MarkDeleted
  - jobRunner
  - 生命周期
summary: bootstrap 未完成时跑 repair 的 db_to_es 会把「尚未复制到 ES」的 DB 行误判为丢失并置 status=3，导致 copy_child 静默漏搬子文档
load: on-demand
related:
  - agent-memory/lessons/patterns-长周期生产巡检.md
  - agent-memory/lessons/failure-copy_child真正瓶颈是子文档量.md
---

# 失败经验：repair 对账在 bootstrap 未完成时误标数据

## 问题背景

[事实] 2026-09-06 07:22 第 2 轮巡检把 P4 全量 bootstrap 作业 `id=8` 按吞吐规则 pause。
07:22:39 起，系统自动排的 **repair 对账作业 `id=9`** 开始跑 `db_to_es`，
到 07:39 已把 **45,886 条** DB 行置成 `status=3`（deleted），速率 **≈50 行/秒（≈18 万行/小时）**，
且仍在 67 张分表的第 1 张（`res_lc_bnd_00`）。

## 根本原因

[事实] `services/gateway/lifecycle/repair.go` 的 `repairDbToEs`：
扫全部 67 张分表的 `status=1` 行 → `LocateIds` 到别名 `res_lc_all` 反查 →
**定位不到就 `MarkDeleted`（status=3）并写一条 event**。

而 bootstrap 的中间态天然满足这个条件：
建库阶段（B1/B2）已把 **全部 4,434 万行**写进 DB（status=1），
copy_parent 只复制到 **2,788 万**父文档 —— 中间 **约 1,646 万行「DB 有 ES 无」是正常中间态，不是故障**。

[事实] 缺少互斥保护：`repair` **不在 `heavyJobKinds` 里**（不抢 `resLifecycle:job` 重型锁），
也没有「存在 running/paused 的 bootstrap 就跳过 `db_to_es`」的判断。

## 触发时序（关键，容易漏看）

[事实] `jobRunner.runJob` 是 **同步调用** handler，`pollOnce` 串行遍历作业。
所以只要 bootstrap 在跑，整个 15 秒轮询循环就被它占住，**其他 pending 作业一律排队**。

1. repair 由 `repair.go` 的定时器在 **每天 04:00**（`now.Hour() != 4` 才跳过）创建为 pending；
2. 04:00 起它一直排不上队 —— 因为 bootstrap 占着轮询循环；
3. **07:22 巡检 pause 掉 bootstrap，恰好把它放行**，17 秒后开始跑。

即：**pause bootstrap 这个「安全动作」本身是误标的触发器**。

## 危害

- [事实] `Dao.ListIdsByIndex` 只取 `status=1`，是 bootstrap **copy_child「按父 id 分批搬子文档」**的数据源
  → 被误标的父文档，其子文档**永远不会被搬**；
- [推断] B5 计数校验按 DB status=1 行数比对，误标行同时从分子分母消失，
  校验很可能**照样通过** → **静默的错误完成**，比直接失败更危险；
- [事实] 这些资源在 DB 侧被视为已删除，脱离生命周期管理；
- [事实] `res_lc_event` 会被写入等量的 repaired 事件行。

## 规避方法

1. **bootstrap 未完成期间不允许跑 repair**：
   - 治标：每天 04:00 前后确认没有 pending 的 repair 作业；pause bootstrap 前先看一眼有没有排队的 repair；
   - 治本：给 `repairDbToEs` 加「存在 state ∈ {running, paused} 的 bootstrap 作业则跳过本步」的保护。
2. **copy_child 启动前必须确认 DB 无被误标的行**，否则漏搬无声无息。
3. 修复已误标的行：依 `res_lc_event` 里 reason=「DB 有 ES 无, 已置为 deleted」+ 时间区间反查，把 `status=3` 改回 `1`。

## 下次行动建议

- [用户确认] 巡检 Agent 每轮开局除了看目标作业，**必须 `lc-check` 默认输出看一眼 `activeJob` 列表**——
  上一轮只盯 `-job 8`，完全没发现旁边多了个 `id=9`。这是本次差点漏掉的关键信号。
- 判断「作业 resume 后没动静」时，先怀疑 **轮询循环被别的作业同步占住**，
  而不是先怀疑集群：现象是 `state=running` 但 `reindex_tasks=0`、文档数不增、`updatedAt` 停在 resume 时刻。
- 巡检 Agent 权限只覆盖目标作业，**pause 别的作业会被 auto mode 分类器拦**；
  遇到这类越界止损需求，立刻发邮件 + 返回报告，不要试图绕过。

## 适用边界

适用于 `services/gateway/lifecycle` 的作业调度模型（同步 runJob + 15s 轮询 + 重型锁只覆盖 heavyJobKinds）。
任何「DB 是元数据、ES 是本体」且存在长时间中间态的迁移作业，都要检查有没有同类对账作业会误判中间态。


## 后续核实与处置（2026-09-06 09:20 补记）

- [事实] 精确影响：仅 `res_lc_bnd_00` 147,432 行（事件 147,437，5 行被正常写入自愈），全部是 id=8 建库阶段新建行；`MarkDeleted` 只改 `status`、`next_check_at`；其它 63 表为 0。
- [事实] 「已修正 147,826」中 389 条是良性「以 ES 为准纠正索引位置」（`res_long_2026`→`res_short_202609`，因 P3 双写已写入 cur）；「去重 14」是物理删除 `res_long_2026` 冗余副本，良性、不可逆、不回滚。
- [事实] 调度串行是第二重伤害：`pollOnce` 同步 `runJob`，repair 跑起来后 id=8 即使 resume 为 running 也拿不到执行权，直到 id=9 被 pause。
- 处置：回滚脚本 SPIDER `scripts/lc_rollback_repair_marked.sh`（`2d32689`）；互斥热修 `repair_guard.go`（master `dd4b7e0` / hotfix `e44b702`），两层保护 + `force` 逃生口；repair 不能进 `heavyJobKinds`（锁在 pause 时释放，堵不住）。
- 教训补充：**pause 一个重作业前先看 `lc-check -jobs` 有没有 pending 的其它作业**；全量 bootstrap 期间任何非 bootstrap 作业出现立即 pause。
