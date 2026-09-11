---
title: 失败经验：bootstrap 按 _id 排序翻页打爆生产 ES 堆
type: lesson
status: active
created_at: 2026-09-05T13:30:00+08:00
updated_at: 2026-09-05T13:30:00+08:00
priority: critical
keywords:
  - bootstrap
  - 存量迁移
  - P4
  - sort _id
  - fielddata
  - 熔断器
  - circuit breaker
  - search_after
  - heap
  - Error 1390
  - 占位符
  - BatchUpsert
summary: P4 bootstrap 的 B1 用 sort:["_id"] 在 15.7 亿文档旧索引上翻页, 触发 _id fielddata 加载, 单页 >550s、堆到 99%、熔断器 tripped; 同时 batch=5000×21 列超 MySQL 65535 占位符上限
load: on-demand
related:
  - agent-memory/sessions/2026/2026-09-05-生命周期P4启动失败.md
  - agent-memory/knowledge/architecture-es索引现状.md
---

# 失败经验：bootstrap 按 `_id` 排序翻页打爆生产 ES 堆

## 问题背景

资源生命周期改造 P4「存量迁移(bootstrap)」2026-09-05 13:04 首次启动，10 分钟后失败。
源索引 `enfi_resource_v6_250822` 有 **15.7 亿**文档（父 4434 万 + 子 12.2 亿 + nested 3.08 亿）。

## 失败方法

### 缺陷 A（严重）：`sort:["_id"]` 做 `search_after` 翻页

`services/gateway/lifecycle/bootstrap.go` 的 `bootstrapBuildDbRows`：

```go
body := obj{"size": p.Batch, "query": query, "sort": arr{"_id"}, ...}
```

**PRD §11.3 的 B1/B1b 行也是这么写的 —— 需求与实现共享同一个错误**，评审时没人抓到。

### 缺陷 B：`bootstrap_batch=5000`

`res_lc_*` 分表 21 列，`sql_util.BatchUpsert` 一次 5000 行 = 105,000 个占位符。

## 失败表现

| 现象 | 数值 |
|---|---|
| B1 第一页耗时 | **> 550 秒仍未返回**（10 分钟 `job.cursor` 始终为空、`progress={}`） |
| 每节点 fielddata | 从 ~0 冲到 **7.2~9.0 GB / 14.3 GB 堆** |
| 节点 heap | 最高 **99%**（正常 37~63%） |
| `fielddata` 熔断器 | 5 个数据节点里 **2 个 tripped=1** |
| 最终错误 | `batch upsert res_lc_quark_00 error: Error 1390 (HY000): Prepared statement contains too many placeholders` |

## 根本原因

1. **ES 6.x 按 `_id` 排序要走 fielddata**：`_id` 没有 doc_values，排序时必须把整个索引的 `_id`
   反解（uninvert）进堆。文档量到十亿级时，这既是几十分钟级的 CPU 开销，也是 GB 级的堆开销。
   小样本单测（`bootstrap_test.go` 用伪造 ES）完全碰不到这个代价。
2. **MySQL 预处理语句占位符上限是 65,535**，与「一批多少行」无关，而与 `行数 × 列数` 有关。
   21 列的表安全上限 ≈ 3120 行。

## 规避方法

- 扫全索引取 id，**永远不要 `sort:["_id"]` / `sort:["_uid"]`**。可选：
  - `scroll` + `sort:["_doc"]`（最快，但断点要存 scrollId 或改成按切片重跑）；
  - `search_after` 排在**有 doc_values 的字段**上（如 `ctime` + 一个 tiebreaker）；
  - 直接按切片（月/年）分段，每段用 scroll 跑完。
- 批量 upsert 的批大小要按 `65535 / 列数` 反算，或在 DAO 层按列数自动分片，而不是写死行数。
- 上生产前，**在真实数据量级上先跑一小片演练**（本例只要跑一页就能暴露）。

## 下次行动建议

1. 任何"扫全量索引"的作业，动手前先确认排序字段有没有 doc_values。
2. 重型作业启动后**前 10 分钟必须盯 `_cat/nodes` 的 `heap.percent` 与 `fielddata.memory_size`**，
   而不是只盯作业进度 —— 本例作业进度 10 分钟没动，看进度看不出任何异常，看堆一眼就看出来了。
3. 应急手法（实测有效）：`ControlJob(pause)` → `POST /_cache/clear?fielddata=true`
   （五分片全成功，heap 从 95% 立刻回落到 40%）。
   ⚠️ `POST /_tasks/<id>/_cancel` 会被 Claude Code auto 模式分类器拦截，别指望它。
4. 作业失败后**不要点「重试」**——`retry` 保留 step/cursor 从失败处继续，会用同一段有缺陷的代码重跑。

## 适用边界

ES 6.x/7.x 均适用（7.x 起 `_id` fielddata 默认禁用会直接报错，反而更安全）。
占位符上限是 MySQL 协议层限制，与 ORM 无关。
