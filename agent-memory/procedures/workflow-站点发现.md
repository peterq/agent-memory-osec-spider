---
title: 工作流：常态化站点发现任务
type: procedure
status: active
created_at: 2026-09-03T11:20:00+08:00
updated_at: 2026-09-03T16:20:00+08:00
priority: high
keywords: [站点发现, site-discovery, 候选站点, 初筛, 有效率抽样, 工具集, 代理池, 10条每分钟]
summary: 收到 `task site-discovery` / `启动网站发现任务` 时的入口与要点；正文流程在 site-discovery/README.md
load: on-demand
related:
  - agent-memory/procedures/workflow-新站点调研.md
  - agent-memory/knowledge/domain-网盘有效性检测.md
  - agent-memory/lessons/success-网盘失效判定原则.md
---

# 常态化站点发现任务

## 触发词

`task site-discovery`、`启动网站发现任务`。看到这类简短指令直接按流程干，**不需要用户再复述需求**。

## 正文在哪

完整流程、验收标准、子 agent prompt 模板：`site-discovery/README.md`（COMMON 仓库）。
工具说明：`site-discovery/tools/README.md`。
已探索站点总表（防重复）：`site-discovery/history.md`。
每次任务的站点报告：`site-discovery/YYMMDD/<主域名>.md`。

## 四条不能忘的

0. **[用户确认 2026-09-03] 抓分享链接一律走 IP 代理池，不允许仅用本机直连**。
   确认有反爬的站点必须带 `--require-proxy`，拿不到代理就失败退出，
   **绝不静默降级成直连**（本机 IP 被拉黑会毁掉后续所有调研）。
   相应地，验收标准第 6 条的口径是「**单 IP ≥10 条分享链接/分钟**」——
   有 Cloudflare、并发高了触发验证码，都**不构成否决理由**，吞吐交给代理池横向扩。


1. **动手前先跑 `python3 site-discovery/tools/selftest.py`**。
   脚本依赖夸克/阿里/百度/迅雷的第三方接口，对方改版会让判定静默失效——
   拿失效的工具去评估站点，会把有效链接全判成 unknown 甚至 invalid，结论全错。
2. **先读 `history.md` 排除已探索域名**，再读 SPIDER `services/` 排除已实现站点。
   每次任务要输出 5~10 个**新**站点。
3. **所有探索过的站点都要记进 `history.md`，包括不满足的**，并写清卡在哪一条。
   这是这个常态化任务不重复劳动的唯一保障。

## 与「新站点调研」的关系

本工作流负责**筛出候选**（广度）；筛出来值得开发的，再走
`procedures/workflow-新站点调研.md` 出 PRD（深度）。两者接力，不要混在一次里做完。

## 分工经验

- 候选生成、初筛、汇总由主 agent 做（掌握全局与去重）。
- 单站深挖派子 agent 并行，模型用 `sonnet`，每个 agent 分 2~3 个站。
  prompt 里**必须把已知的初筛结论写进去**（sitemap 条数、是否有登录墙），省掉重复劳动。
