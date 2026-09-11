---
title: 失败经验：copy_child 的真正瓶颈是子文档量 × reindex 限速，不是轮询
type: lesson
status: active
created_at: 2026-09-05T16:50:00+08:00
updated_at: 2026-09-05T16:50:00+08:00
priority: high
keywords: [copy_child, bootstrap, reindex, requests_per_second, 限速, 子文档, file_count, 量纲估算, 生命周期, P4, slices]
summary: 修完轮询空等后 copy_child 只快 2.1 倍——因为真正的工作量是 3245 万/单月、7.4 亿/全量的子文档，被 reindex 的 2000 rps 限速卡死
load: on-demand
related:
  - agent-memory/lessons/failure-copy_child小reindex被轮询间隔拖垮.md
  - agent-memory/lessons/failure-bootstrap按id排序打爆ES堆.md
  - agent-memory/current/tasks.md
---

# 失败经验：copy_child 的真正瓶颈是子文档量 × reindex 限速

## 问题背景

[事实] 生命周期 P4 bootstrap 的 B3c/B4c `copy_child`：把旧索引里 join 型资源的 `file` 子文档
复制到新索引。前一轮定位到"每 200 个父 id 发一次小 `_reindex`、却按固定 10 s 轮询"，
修复为**指数退避 + 批大小解耦（`bootstrap_copy_batch`=2000）**，PRD README §11.8.7 估算
"单月 6~17 分钟、全量 2~6 小时"。

## 失败方法

直接按修复后的估算安排验收门槛（每批秒级、单月 ≤30 分钟），准备验收通过就放全量。

## 失败表现

[事实] 2026-09-05 16:16~16:29 生产复测（作业 `id=4` resume，2026-08 单月）：

| | 批大小 | 单批耗时 | 父 id 吞吐 |
|---|---|---|---|
| 修复前 | 200 | 21.9 s | 9.1 /s |
| 修复后 | 2000 | **63~103 s** | **19.4 /s** |

只快了 **2.1 倍**（估算是"单批快 7~20 倍 × 批数降到 1/10"）。单月剩余需 **约 7 小时**。

## 根本原因

[事实] **估算只算了"调用次数"，从来没算过"文档量"**。对旧索引做一次聚合就能拿到：

```
join=resource AND valid=1 AND ctime ∈ [2026-08-01, 2026-09-01)
→ 父文档 649,472，sum(file_count) = 32,449,681
    quark       644,148 父 → 32,234,398 子（平均 50.0）
    xunleipan     3,448 父 →    148,232 子（平均 43.0）
    aliyundrive   1,876 父 →     67,051 子（平均 35.7）
```

- **单月要搬 3245 万个子文档**，全量（join 型约 1470 万父 id × 50）≈ **7.4 亿子文档**。
- `_reindex` 的 `RequestsPerSecond` 缺省 **2000**（5 个 slice 各 400）。
  单月 32.45 M ÷ 2000 = **4.5 小时**下界，全量 ≈ **4.3 天**。
  → **"单月 30 分钟"在 rps=2000 下数学上就不可能**（需要约 18,000 rps）。
- 实测只跑到 **913 docs/s**（限速上限的 46%），差额花在
  `terms{join#resource:[2000 个 id]}` 在 **15.8 亿文档**旧索引上的检索，以及 **slice 分配不均**
  （抓到一批：5 个 slice 里一个独吞 65% 的文档，单批墙钟由最慢 slice 决定）。

## 规避方法

1. **先算量纲再定门槛**：任何"搬数据"的估算，第一步是 `sum(file_count)` / `_count` 这类
   一次聚合就能拿到的**文档量**，再除以有效速率。批数只是次要因子。
2. 拿到量纲后立刻回头检查限速常量（`requests_per_second`、`slices`、分片数）是否与量纲匹配。
3. 观察生产任务时用 `GET _tasks?actions=*reindex&detailed=true`，里面
   `total`/`created`/`throttled_millis`/`requests_per_second` 直接告诉你**时间花在限速还是检索上**
   （`throttled_millis` 是 5 个 slice 的累计值，除以 slice 数才是墙钟）。

## 下次行动建议

- 短期：`CreateJob` 的 `requestsPerSecond` 是作业参数，**不改代码**就能试 6000~10000/`-1`；
  但实测只有限速上限的 46%，单纯放开最多再快约 2 倍，到不了 30 分钟。
- 中期：消除 slice 不均（按父 id 的 routing 分组成批，或 slices 远大于分片数）。
- 根治：`copy_child` 从"按父 id 分批 reindex"改成**按 ctime 窗口整段 reindex 子文档**
  （和 B1/B3 一样窗口切片），把每批固定开销摊到接近零 —— 量纲上唯一有希望把全量压进 24 h 的做法。

## 适用边界

针对 ES 6.x 父子（join）文档的存量搬迁。同样的思路适用于任何"按 id 列表分批调用外部批处理"
的场景：**先量文档/记录数，再谈批大小与并发**。
