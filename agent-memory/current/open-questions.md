---
title: 未解决的问题
type: question
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-15T08:20:00+08:00
priority: high
keywords: [待确认, xlLoadShare, 迅雷, 事故恢复, lifecycle_checker, P5, 灰度, 用户确认]
summary: 当前无待用户确认问题（阶段 D 已按裁定启用；进度在 tasks.md）
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


## 转存下载链路账号池是否续期（2026-09-13 体检发现）

正本 `knowledge/domain-转存下载链路.md` §6。链路当前无新任务且账号全失效：阿里 3 个在队账号 refresh token 失效、百度 0 可用账号。

- [待确认] 近期是否还有新的下载批次？若无，可先 `SetEnablePanAccount(false)` 把 3 个失效阿里账号出队，止住每分钟的无效重试日志。
- [待确认] 若要恢复，需人工提供新的阿里 refresh token / 百度账号，Agent 只能投递不能获取凭据。

用户答复：

## 🔴 lifecycle_checker 误判事故（2026-09-12 22:17 发现）——需人工止血 + 恢复决策

正本 SPIDER `PRD/res-lifecycle/rollout-2026-09-05.md` §15；经验 `lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`。

- ✅ 止血与修复部署已于 09-12 23:05~23:11 完成（`b888846` + bnd 判定修复 `06ef50d`，rollout §15.5）。
- [用户确认 09-12] Mongo 无数据、ES 唯一数据源 → 恢复**只能重爬**。方案：导出 1,156,201 条 type/share_id/pwd → 限速投递 `resourcePreCheck` → `*LoadShare` 解析入库、lc 行复活。工具开发中（`agent-tasks/2026-09-12-lc-recrawl/`）。
- ✅ [用户确认 09-12 23:33] 重爬节奏按建议（`-rate 10`，先 1,000 条试点再全量）；`e16bd98` 已部署。当前无待确认问题（恢复进度见 `current/tasks.md`）。
- [待确认] 恢复期间 P5 阶段 C 复测/阶段 D 灰度是否顺延（v2/v3 同等缺这 115.5 万条，重合度不受影响，但对外召回已受损）。

用户答复：

## 已按答复推进（2026-09-12，本节下次清理）

- `:cur` 半区窗口「同法处理」→ 取证后**不处理**：30/30 抽样父子均在 cur、long=0，「父在 long」前提不成立；按 target=long 投递反而会把 8 月底新资源错沉 long。
- 代理池口径 → `lifecycle_checker_*` ok=0 是本次事故（调用方请求错），非口径问题；三个 keyword 站仍 0 成功，列下线候选（`current/tasks.md`）。
- A' 存量复检 → 只读探测驱动 `scripts/lc_legacy_probe_all.sh` 已就绪并在跑；**投递等修复版 checker 上线**。
- 阶段 D → 改为 API 侧自动灰度分流，`decisions/decision-2026-09-12-阶段D改由API侧自动灰度分流.md`，代码开发中。
