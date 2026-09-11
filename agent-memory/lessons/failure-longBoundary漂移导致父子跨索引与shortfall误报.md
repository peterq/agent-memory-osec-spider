---
title: 失败经验：longBoundary 按 time.Now() 计算导致长跑 bootstrap 父子跨索引、shortfall 全部误报
type: lesson
status: active
created_at: 2026-09-11T12:10:00+08:00
updated_at: 2026-09-11T17:00:00+08:00
priority: critical
keywords: [bootstrap, longBoundary, shortfallSlices, has_parent, parent_id, copyMode=ids, mover, TriggerMove, 父子跨索引, res_short_202609, res_long_2026]
summary: id=8 的 89 条 shortfallSlices（420 万）不是子文档丢失，而是 copy_parent 与 copy_child 各自用 time.Now() 算 90 天边界、6 天长跑后漂移，父进 cur 子进 long；copyMode=ids 补搬是错误且危险的做法，正确修法是 mover 让父归位
load: on-demand
related:
  - agent-memory/lessons/patterns-长周期生产巡检.md
  - agent-memory/lessons/failure-copy_child计数校验对称差误判重跑.md
  - agent-memory/current/tasks.md
---

# 失败经验：longBoundary 漂移导致父子跨索引

## 问题背景

[事实] id=8（09-05 23:01 → 09-11 10:25，含多次 pause/resume）done 后 `progress.shortfallSlices` 89 条，缺口 4,199,824 子文档（4.92%），
`child:t202606100000:long` 整窗 dst=0。主控原计划按 README 用 `copyMode=ids` 补搬。

## 根本原因（只读取证，09-11）

- [事实] `bootstrapCopyParents`（bootstrap.go:819）与 `bootstrapCopyChildrenByWindow`（bootstrap.go:1115）**各自** `longBoundary = time.Now().AddDate(0,0,-90)`。
  copy_parent 在 09-05/06 跑，boundary≈06-07：`utime=2026-06-10` 的父判 cur → 进 `res_short_202609`；copy_child 在 09-09 之后跑，boundary≈06-11/13，同批父落 long 半区 → 子进 `res_long_2026`。
  缺口比例随日期严格递增（06-01 3% → 06-08 95% → 06-09~11 100%），正是边界扫过的形状。抽样 47/47 父在 cur、0/47 在 long；20 父的子 legacy 951 = long 951，cur 0。
- [事实] 少数超大父（单父 34 万子）是线上写入把 `utime`/DB `last_update_at` 更新成 09-07，父被写进 cur。
- [事实] `ChildShortfall.dst` 用 `has_parent` 口径，无法区分「子没搬」与「父不在本索引」，89 条全部是后者。`parent_id` 口径 legacy = long 分毫不差。

## 失败方法（未执行，分析阶段识别）

- `copyMode=ids` 新建 bootstrap：会重跑 B0~B2（`bsStepBefore` 从 0 起）；B1 `BatchUpsert` 固定写 `Status=1` 会把 repair 刚标的 status=3 翻回、重置全部 `next_check_at`；copy_parent 以当前 boundary 再判 long 造成**父跨索引双份**（`op_type=create` 只防同索引）；
  `bootstrapCopyChildrenByIds` 用 `ListIdsByIndex`（dao.go:663）**无 ctime 过滤**，`ctimeFrom/ctimeTo` 挡不住，退化为全量（cur 274.6 万 + long 全部，63~103 s/批）。同时任何 pending/running bootstrap 会把在跑的 repair 置 paused 且不自动恢复。
- 裸 `kind=reindex` 把父补到 long：不删源、不改 DB → 双份 + DB/ES 不一致。
- 等自愈：`next_check_at` 被打散到 09-18~12-02；超大父 `last_update_at` 已是 09-07，`decideOnValid` 判「未满 90 天」永不下沉。

## 正确做法

- **mover 让父归位**：`TriggerMove{ids≤200, target:"long"}`（rpc_service.go:441），`moveBatch`（mover.go:141）= `_reindex(ids+父子)` → 校验 → `_delete_by_query` 删源 → 回写 DB index_name/index_role；子已在 long 的变 version_conflict 无害。
  目标集合：`res_short_202609` 中 `join=resource` 且 `utime < now-90d` 的父，实测 **220,333**（占 cur 父 8.0%）；速率 `move_batch=200`/`move_interval_sec=300` ≈ 2,400 父/h（仅 shortfall 相关 1.5~2 万父 6~9 h；全量约 92 h）。
  前置：repair id=11 done；`enabled=true`、`move_on_check=true`。中止：停投递即可。
- 核验三查：父 `ids` probe 在 long / `parent_id` 计数 / `has_parent` 计数一致。

## 下次行动建议 / 代码待改（1~3 已于 09-11 修复：SPIDER `61cf1db`/`e856540`/`93f4d38`，4 已实现 `aac5f84`；均未部署）

1. `longBoundary` 固化进 `progress`，整个作业生命周期复用同一值（长周期作业禁止在各阶段各自取 now）。
2. shortfall 记账增加 `parent_id` 口径计数或「目标索引缺失父数」，区分两类成因。
3. `bootstrapCopyChildrenByIds` 必须尊重 `ctimeFrom/ctimeTo`，或 README 删除「小范围修补」说法。
4. lc-check 增加 `-trigger-move` 入口（当前只能走后台界面/自写 RPC 客户端）。

## 适用边界

任何跨天的、分阶段按「相对当前时间」分流的迁移作业都有同类风险；判据是缺口比例随日期单调变化。
