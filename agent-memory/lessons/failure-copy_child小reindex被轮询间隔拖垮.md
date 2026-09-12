---
title: 失败经验：大量小 _reindex 被固定 10 s 轮询间隔拖垮
type: lesson
status: active
created_at: 2026-09-05T15:40:00+08:00
updated_at: 2026-09-12T22:36:00+08:00
priority: high
keywords:
  - bootstrap
  - copy_child
  - reindexPollInterval
  - _reindex
  - 轮询间隔
  - 吞吐
  - 生命周期
  - 测试替身屏蔽缺陷
summary: bootstrap B3c copy_child 上万个小 reindex 被固定 3 s 轮询拖垮，改指数退避后吞吐恢复
questions:
  - P4 第二次演练，copy_child 为什么这么慢（轮询空等）
load: on-demand
related:
  - agent-memory/lessons/failure-bootstrap按id排序打爆ES堆.md
  - agent-memory/sessions/2026/2026-09-05-生命周期P4演练.md
---

# 失败经验：大量小 `_reindex` 被固定轮询间隔拖垮

## 问题背景

SPIDER 生命周期改造 P4 存量迁移（bootstrap）。缺陷 A（`sort:["_id"]` 打爆 ES 堆）与
缺陷 B（MySQL 占位符超限）修复后重排，2026-08 单月实跑的 B1/B1b/B3/B4 都很快
（建 DB 行 2.5 min、复制父文档 9 min），**卡死在 B3c `copy_child`**。

## 失败方法

`services/gateway/lifecycle/bootstrap.go` `bootstrapCopyChildren`：
每 `move_batch`（缺省 **200**）个父 id 发**一次** `_reindex`
（`{"terms":{"join#resource":[…200 个 id…]}}`），然后调 `runReindexStep` 等它结束。

## 失败表现

- 实测 **22~24 秒/批**（两个独立窗口交叉验证：5 min 窗口 23.2 s/批，19 min 窗口 21.9 s/批）。
- 换算：2026-08 单月 658,053 个父 id → 3,290 批 → **约 21 小时**；
  全量 join 型约 1,470 万 → 73,500 批 → **约 20 天**。
- **不是 ES 累**：全程集群 green、heap 48~62%、fielddata 与基线持平、磁盘充裕。

## 根本原因

`services/gateway/lifecycle/rotation.go:840`

```go
var reindexPollInterval = 10 * time.Second
```

`waitEsTask` 按这个间隔轮询 `_tasks/<id>`。这种只搬约 1,000 个子文档的 `_reindex`
**实际不到 1 秒**就结束，却要等 1~2 个 10 秒周期才被发现。
**耗时几乎全花在轮询等待上。**

该常量对轮换 / 整索引搬迁那种"少量大 reindex"完全合理，
对 `copy_child` 这种"上万次小 reindex"是病态的 —— 同一个常量服务了两种量纲相反的场景。

## 为什么测试抓不到（与缺陷 A/B 同构）

`bootstrap_it_test.go:399` 把 `reindexPollInterval` 改成 **200 ms** 再跑联调，
正好把这个缺陷屏蔽掉了 —— 联调 140 s 跑完 5 万文档，看不出任何问题。

> **通用规律**：凡是被测试替身调快 / 调小 / 调简的生产常量
> （轮询间隔、批大小、超时、限速、数据量），都要**单独做一次量纲估算**：
> 「生产规模 ÷ 单位代价 = 多久」。三次 P4 缺陷（A 的 15.7 亿文档 fielddata、
> B 的 5000×21 占位符、本次的 10 s × 73,500 次）全部是这一类，
> 全部是单测/联调绿灯但一上生产就废。

## 规避方法

- `waitEsTask` 改**指数退避**：200 ms 起、×1.5、封顶 10 s。
  对大 reindex 额外开销可忽略，对小 reindex 是数量级提升。
- 或给 `copy_child` 单独用大得多的批（父 id 数上千），摊薄每次 reindex 的固定开销。
- 两者可叠加。

## 下次行动建议

1. 演练时**不要只看"有没有报错"，要算完成时间**。本次是靠"5 分钟游标推进量 → 批数 → 总时长"
   这个换算发现的，作业本身一切正常、日志零错误。
2. 新引入一个"循环里调用外部长操作 API"的代码路径时，先问：
   **这个循环在生产会跑多少次？每次的固定开销是多少？**
3. 断点游标设计得好就不亏：作业 `id=4` 停在 `paused`（游标 `res_lc_quark_00|40ba…`），
   修完可**原地 resume 续跑**，不用从头。**不要点 retry，retry 会从头开始。**

## 适用边界

任何"外层循环 × 每次等一个异步任务"的批处理：
`_reindex` / `_delete_by_query` / `_update_by_query` / 云 API 的 job 轮询都同理。
