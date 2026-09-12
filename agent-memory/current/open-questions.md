---
title: 未解决的问题
type: question
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T12:10:00+08:00
priority: low
keywords: [疑问, 待确认, 用户确认, 生命周期, lifecycle, Q1~Q6]
summary: 当前没有待确认问题（生命周期 Q1~Q6 已于 2026-09-05 确认）
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
- [待确认] 5 个未部署代码提交何时随网关发版（`3b8cc13` verify 汇总、`aac5f84` trigger-move、`61cf1db` longBoundary 固化、`e856540` ids 范围、`93f4d38` shortfall 两口径）。

### 原记录

- [待确认] TriggerMove 入口：NC-JS 后台界面手工投递（≤200/批）还是给 lc-check 加 `-trigger-move` flag（改代码）。
- [待确认] 范围：只修 shortfall 相关 ≈1.5~2 万父（6~9 h）还是 `res_short_202609` 里全部 utime<now-90d 的 220,333 父（≈92 h，语义上本就该沉 long）。
- [待确认] 是否放宽 `move_batch`（200）/`move_interval_sec`（300）加速；`enabled`/`dual_write_legacy` 不动。
- 前置：repair id=11 done。禁用 `copyMode=ids`。详见 `lessons/failure-longBoundary漂移导致父子跨索引与shortfall误报.md`。

## 2026-09-11 P4 作业 id=8 verify 失败后的恢复（**已完成** 10:25 done）

- [待确认] repair 守卫被 id=4（paused）拦住：用 `-job-params '{"force":true}'`（推荐，当前无 running/pending bootstrap）还是先 cancel id=4？
- [待确认] repair 执行时间窗（建议 23:00~08:00 低峰；全量 43.7M 行 1.5~4 h，对 long 删父 ≈5.3 万 + 子 ≈131 万）。
- [待确认] 是否 `skipEsToDb=true`（取证显示 ① 补录量 ≈0）。
- [待确认] shortfallSlices 89 条（2026-06 整窗 dst=0）补搬放在 id=8 done 之前还是之后。
- 决策后顺序：repair → 只读复核两索引 <0.1% → retry id=8 → done。详见 `current/tasks.md` 09-11 条目、SPIDER rollout §12.6。

## 代理池监控首批数据里几个场景成功率为 0（2026-09-10，待确认口径）

首个 5 分钟窗口（09:53~09:58）：`lifecycle_checker_quark`/`lifecycle_checker_bnd` total 2290/2008、ok=0、`httpError` 占 7 成；
`keyword_upyunso`/`keyword_funletu`/`keyword_pansearch_me` ok=0、几乎全是 `ipUnusable`。
- [待确认] lifecycle_checker 的"资源已失效"响应（非 2xx 或业务码）是否被 `ClassifyResult` 记成 httpError——若是，这两个场景的成功率天然为 0，前端口径需要区分"代理请求成功"与"资源有效"。
- [待确认] 三个 keyword 站是否已经不可达（站点下线/改域名），还是代理池对该站全部不可用；可用 `tools/proxy-admin-check -scene keyword_upyunso` 观察几小时再判断。

用户答复：



> kkpans 爬虫 PRD 的 5 个问题已于 2026-09-02 全部答复并落地，
> 决策见 `osec-spider-go/PRD/2609/www.kkpans.com.md` §8
> 与 `agent-memory/decisions/decision-2026-09-02-停止磁力资源采集.md`。

## 全量 bootstrap 提速方案（2026-09-06，待用户决策）

- [待确认] 作业 id=8 copy_parent 阶段吞吐仅 1,400~2,700 docs/s（瓶颈是每窗口固定开销，rps 6000 未跑满），主控已选择原地 resume 跑完。用户可选：cancel 后以更大 `windowTargetDocs`（如 60~100 万）重跑以减少窗口数——代价是重做 3.9 h 建库、丢弃已复制进度、需重评 heap；或给 lc-check/bootstrap 补"窗口固定开销"优化后再谈。见 `decisions/decision-2026-09-06-全量bootstrap熔断后原地resume.md`。
- [已关闭 2026-09-08] res2 xigua/qingting 按多数派剔除、oss/s3 留空——用户已确认。
- [待确认] 用户本机 18081 隧道（pid 1880789）09-06 03:29 随网络中断消失，是否需要恢复由用户处理。

## 资源生命周期改造（2026-09-05）——已全部确认，见决策文件

- [用户确认 2026-09-05] Q1 全量复制；Q2 先不加副本；Q3 version 变化作更新判据；**Q4 每类型 16 桶（64 张表）**；
  **Q5 v3 只覆盖 search 与 valid 两类接口**；Q6 百度存量迁入。当前无待确认问题。
