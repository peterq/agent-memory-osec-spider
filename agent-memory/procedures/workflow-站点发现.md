---
title: 工作流：常态化站点发现任务
type: procedure
status: active
created_at: 2026-09-03T11:20:00+08:00
updated_at: 2026-09-16T10:40:00+08:00
priority: high
keywords: [站点发现, site-discovery, 候选站点, 初筛, 有效率抽样, 工具集, 代理池, 10条每分钟, ratetest, PanSou, PanHub, harvest.py, V2EX, worktree]
summary: `task site-discovery` 的入口、候选渠道、worktree 执行方式与两轮踩坑；正文流程在 site-discovery/README.md
questions:
  - 怎么启动网站发现任务，在 worktree 里怎么跑
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

## 候选从哪来：渠道性价比

- **开源聚合项目的插件目录性价比最高**（`PanSou`、`PanHub` 这类网盘聚合搜索项目，插件/源站目录里
  一次能薅出几十个域名），远高于搜索引擎逐个找。已固化成 `site-discovery/tools/harvest.py`，
  直接跑脚本出候选清单，再进初筛。
- 拿到候选先过 `history.md` 去重（见上一节第 2 条），别把已淘汰的域名再挖一遍。

## 与「新站点调研」的关系

本工作流负责**筛出候选**（广度）；筛出来值得开发的，再走
`procedures/workflow-新站点调研.md` 出 PRD（深度）。两者接力，不要混在一次里做完。

## 分工经验

- 候选生成、初筛、汇总由主 agent 做（掌握全局与去重）。
- 单站深挖派子 agent 并行，模型用 `sonnet`，每个 agent 分 2~3 个站。
  prompt 里**必须把已知的初筛结论写进去**（sitemap 条数、是否有登录墙），省掉重复劳动。
- [2026-09-16] 共享简报落盘 `agent-tasks/YYYY-MM-DD-site-discovery/00-shared.md` + 每组 `N0-group-x.md`，prompt 只给路径；
  简报里要写明「**不要用 Monitor 等后台任务**，用 `until [ -s json ]` 的 run_in_background 等或直接收尾」——
  否则子 agent 会反复停在「等通知」，主控得 SendMessage 催。
- 子 agent 的「证据不足」主控要亲自补一刀再定论：本轮 duanjuso（逆向 bundle 找到公开搜索接口）与 ddys（`ratetest.py` 补吞吐）都从「证据不足」翻成满足。

## 在 worktree 里执行（2026-09-16 起）

- 用 `EnterWorktree` 在 COMMON 上开 `site-discovery-YYMMDD`，报告/history/工具改动全在 worktree，主仓库不动，结束后用户确认合并。
- worktree 会话的 Bash 守卫会拒绝含变量、heredoc、多段管道或跨仓库 `cd` 的命令：脚本一律先 `Write` 到 scratchpad，再用**字面绝对路径**调用；对 agent-memory 仓库的改动用 Edit/Write 工具而非 sed。
- 派子 agent 前先 `tools/proxypool.py status` 看存活数，<5 个时在简报里提醒降并发、放宽 timeout（见 `lessons/failure-本地代理池薄导致连接失败误判为站点拒绝.md`）。

## 两轮踩坑速查

- **规模不能只看 sitemap 条数**：博客型站（jsnoteclub）sitemap 190 条但每篇 5 条链接、总量 7000+；SPA 站（hunhepan）的 sitemap 是搜索词缓存页；SEO 马甲站（squark.cc.cd）1.8 万条全无真链。要看「可枚举实体 × 每实体链接数」。
- **链接可能不是明文**：`atob('<base64>')` 包在 onclick（ddys.io，`panlink.py` 已解）、服务端加密字段（wnsearch.top）、点击后前端换取（zlxapp.top）、客户端加密 + fingerprint（fastsoso.cc）。正则 0 命中先用 `fetchraw.py` 看原文再下结论。
- **更新频率证据链**：sitemap `lastmod`（`sitescan.py` 已统计 7/14/30 天分桶）→ 停更不等于站点停更，再找搜索/最新接口（duanjuso `share_time=week`）或详情页发布日期。
- **纯关键词搜索引擎**（首页零链接、无 sitemap）占本轮初筛淘汰的一半，与 pansou.app 同类，除非先挖出搜索接口否则不值得深挖。
- 第二轮结果：满足 duanjuso.cc / pan.xiaozi.cc / qileso.com / jsnoteclub.com / ddys.io，待裁定 lzpanx.com（robots `Crawl-delay: 20`）→ `sessions/2026/2026-09-16-站点发现第二轮.md`。
