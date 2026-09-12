---
title: 未解决的问题
type: question
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T16:15:00+08:00
priority: high
keywords: [P5, 待确认, 用户确认, 存量复检, 切流, 灰度]
summary: 待用户确认：P5 A' 存量复检节奏、阶段 D 调用方切流对接，及 :cur 半区窗口、代理池口径等历史项
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

## 2026-09-11 shortfall 修复 = mover 父归位（**已完成** 09-12 02:17，102,601 父归位）

- [待确认] 2 个 `:cur` 半区窗口（`t202608290000`/`t202608310000`，父在 long、子在 cur，21,451 子）是否同法处理（target=long，规模小）。

### 原记录

- [待确认] TriggerMove 入口：NC-JS 后台界面手工投递（≤200/批）还是给 lc-check 加 `-trigger-move` flag（改代码）。
- [待确认] 范围：只修 shortfall 相关 ≈1.5~2 万父（6~9 h）还是 `res_short_202609` 里全部 utime<now-90d 的 220,333 父（≈92 h，语义上本就该沉 long）。
- [待确认] 是否放宽 `move_batch`（200）/`move_interval_sec`（300）加速；`enabled`/`dual_write_legacy` 不动。
- 前置：repair id=11 done。禁用 `copyMode=ids`。详见 `lessons/failure-longBoundary漂移导致父子跨索引与shortfall误报.md`。

## 代理池监控首批数据里几个场景成功率为 0（2026-09-10，待确认口径）

首个 5 分钟窗口（09:53~09:58）：`lifecycle_checker_quark`/`lifecycle_checker_bnd` total 2290/2008、ok=0、`httpError` 占 7 成；
`keyword_upyunso`/`keyword_funletu`/`keyword_pansearch_me` ok=0、几乎全是 `ipUnusable`。
- [待确认] lifecycle_checker 的"资源已失效"响应（非 2xx 或业务码）是否被 `ClassifyResult` 记成 httpError——若是，这两个场景的成功率天然为 0，前端口径需要区分"代理请求成功"与"资源有效"。
- [待确认] 三个 keyword 站是否已经不可达（站点下线/改域名），还是代理池对该站全部不可用；可用 `tools/proxy-admin-check -scene keyword_upyunso` 观察几小时再判断。

用户答复：



> kkpans 爬虫 PRD 的 5 个问题已于 2026-09-02 全部答复并落地，
> 决策见 `osec-spider-go/PRD/2609/www.kkpans.com.md` §8
> 与 `agent-memory/decisions/decision-2026-09-02-停止磁力资源采集.md`。

## 资源生命周期改造（2026-09-05）——已全部确认，见决策文件

- [用户确认 2026-09-05] Q1 全量复制；Q2 先不加副本；Q3 version 变化作更新判据；**Q4 每类型 16 桶（64 张表）**；
  **Q5 v3 只覆盖 search 与 valid 两类接口**；Q6 百度存量迁入。当前无待确认问题。

## P5 准入执行中（2026-09-12）—— D1~D4 已由用户以「执行 p5-plan」采纳，见 `decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md`

- [待确认] 阶段 A' 存量提前复检（约 170 万条 bootstrap 迁入但旧链路已删的 lc 行）何时开始、每天多少批（建议按 lc checker 吞吐每天 ≤20 万，`TriggerCheck(force)` ≤200/批）。
  - 答复：
- [待确认] 阶段 D 切流由调用方 `dashengpan_web` 改路径，需要哪位对接、何时可改（不在本仓库范围）。
  - 答复：
