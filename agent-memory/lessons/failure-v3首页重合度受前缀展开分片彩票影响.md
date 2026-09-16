---
title: 失败经验：v3 与 v2 首页重合度达不到 95%——match_phrase_prefix 的分片词典展开与 legacy→lc 失效未同步
type: lesson
status: active
created_at: 2026-09-12T15:30:00+08:00
updated_at: 2026-09-16T14:35:00+08:00
priority: high
keywords: [P5, 重合度, match_phrase_prefix, 分片彩票, idf, dfs_query_then_fetch, url_check, clearExpire, 死链同步, v3 搜索]
questions:
  - P5 对拍为什么没通过，dfs 能不能让 v3/v2 排序一致
  - 旧索引 url_check 删掉的文档新方案会同步失效吗
summary: P5 对拍首页重合度 84%<95% 的两个根因——4% 坑位是 legacy 已删 lc 未删的死链（无反向失效同步）；其余是 match_phrase_prefix 展开集合随分片词典变化、生僻展开词 idf 加进短语权重，dfs 救不了
load: on-demand
related:
  - agent-memory/current/open-questions.md
  - agent-memory/decisions/decision-2026-09-04-资源索引生命周期改造方案.md
---

# 失败经验：P5 前置对拍未通过的两个根因

正本：SPIDER `PRD/res-lifecycle/rollout-2026-09-05.md` §13、`p5-precheck-2026-09-12.md`。

## 问题背景

PRD §12 P5 验收要求「50 关键词 v2/v3 搜索结果重合度 ≥95%、v3 P99 ≤ v2」。2026-09-12 用真实流量抽 50 个关键词
（`scripts/lc_p5_v2v3_diff.py`）实测：首页 15 条 id 重合度均值 **84.3%**，首页 100 条 91.7%，`total` 差额 0~0.5%；
延迟 P50 v3 +28%，P99 冷态超 13%、热态反超。

## 失败表现与根本原因

**A. 语料级（4.1% 坑位）**：v3 独有的 117 条首页 id 里 31 条在旧索引已不存在，DB 里全部 `status=1, check_count=0`。
双写期只有 lc→legacy 的失效同步（`clear.go` 推 `clearExpire`），**没有 legacy→lc**（`res_scheduler/clear_expire.go`
`HandleTask` 只删旧索引 + `AddInvalidResLink`）。bootstrap 迁入的存量要等 `bootstrap_spread_days`（bnd 180 天）才被 lc 检测，
这期间 v3 会一直比 v2 多返回旧链路已剔除的死链。反向（v2 独有 id）在 `res_lc_all` 全部存在，新方案没漏数据。

**B. 排序级（其余）**：`match_phrase_prefix` 对末词做前缀展开，展开集合取决于**所在分片的词典**；Lucene `MultiPhraseQuery`
把每个展开词的 idf 都加进短语权重。旧索引每分片 3.1 亿文档几乎都含生僻展开词（「晴朗朗」docFreq=1 → idf 19.2），
各分片一致；新方案 `res_short_202609`（2,839 万/分片）与 `res_long_2026` 词典差异大，文档落在哪个物理索引就决定有没有这份加分，
首页按索引洗牌（同一文档「早春 晴朗」短语权重旧 61.3 vs 新 31.5）。`dfs_query_then_fetch` 只统一 idf 数值不统一展开集合，
均值 82%→86%；v3 改 `match_phrase` 也只有 80.7%（v2 侧加分仍在）。**v2 自身顺序也是这种彩票**（legacy 有/无 dfs 对拍 98% 只证明自洽）。
最受影响的是同名近重复资源多的关键词（凡人修仙传、早春晴朗）。

## 规避方法 / 下次行动建议

- 先修 A（`HandleTask` 里对 DB `status=1` 的 id 把 `next_check_at` 提前到 now，交 lc 自己复检；lc 回流任务行已 `status=2` 不成环），再复测。
- 「重合度」口径要按语料级定义（`total` 差额 + 首页 100 条 + 无「旧索引已删」文档），首页 15 条 id 集合在结构上达不到 95%。
- 排序差异要用 `explain` 看 `weight(filename:"…")` 的 idf 求和项，展开集合不同一眼可见；别先猜 analyzer/mapping（两边完全一致）。
- 对拍探针必须按 res-api 三级漏桶算节奏（6/10s、50/5min、100/30min，每路径 1 请求/8 s），不伪造 `Enfi-Forward-IP` 绕过。
- P99 用 50 样本没有统计意义（= 最大值），要 ≥3 轮、间隔 ≥30 min。

## 适用边界

只针对 ES 6.7 + `match_phrase_prefix` + 多物理索引别名的组合；单索引内各分片体量相近时该效应可忽略。
