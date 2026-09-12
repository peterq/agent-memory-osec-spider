---
title: 未解决的问题
type: question
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T23:05:00+08:00
priority: high
keywords: [待确认, 事故恢复, lifecycle_checker, P5, 灰度, 用户确认]
summary: 待用户确认：checker 误删事故的止血执行与 115.5 万条恢复方案；A'/阶段 D 已按答复推进
questions:
  - 当前有哪些待用户确认的问题
load: on-demand
related:
  - agent-memory/current/tasks.md
  - agent-memory/decisions/
---

> rules: 1. 只记录**未解决的问题**，已答复的落地问题不再重复。2. 已答复的问题在落地后即删除,
   只保留未答复的待确认问题, 以免占用context. 3. `答复`段落由用户编辑, 但可由Agent在合适时随问题一起清理掉.

# 未解决的问题

## 🔴 lifecycle_checker 误判事故（2026-09-12 22:17 发现）——需人工止血 + 恢复决策

正本 SPIDER `PRD/res-lifecycle/rollout-2026-09-05.md` §15；经验 `lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`。

- [待人工] 止血：`ssh osec-jenkins "docker stop spider-lifecycle_checker"`（Agent 执行被安全策略拦截）。停之前每小时 ≈ +7,000 条误删。
- [待人工] 部署修复 SPIDER `b888846`：`./deploy.sh lifecycle_checker`，看容器 5 秒统计出现 `valid>0`。
- [待确认] 恢复方案：从 Mongo `share_files` 回灌 115.5 万条（quark 1,115,264 / ali-share 40,007）→ 删 `invalid_link_*` 对应行 → `storage.UpsertResource` → 修复版 `TriggerCheck(force)` 复检。
  需新写回灌工具（≈1 人日，STORAGE 或 SPIDER devops），回灌吞吐走正常入库链路。是否做、何时做、由谁做？
- [待确认] 恢复期间 P5 阶段 C 复测/阶段 D 灰度是否顺延（v2/v3 同等缺这 115.5 万条，重合度不受影响，但对外召回已受损）。

用户答复：

## 已按答复推进（2026-09-12，本节下次清理）

- `:cur` 半区窗口「同法处理」→ 取证后**不处理**：30/30 抽样父子均在 cur、long=0，「父在 long」前提不成立；按 target=long 投递反而会把 8 月底新资源错沉 long。
- 代理池口径 → `lifecycle_checker_*` ok=0 是本次事故（调用方请求错），非口径问题；三个 keyword 站仍 0 成功，列下线候选（`current/tasks.md`）。
- A' 存量复检 → 只读探测驱动 `scripts/lc_legacy_probe_all.sh` 已就绪并在跑；**投递等修复版 checker 上线**。
- 阶段 D → 改为 API 侧自动灰度分流，`decisions/decision-2026-09-12-阶段D改由API侧自动灰度分流.md`，代码开发中。
