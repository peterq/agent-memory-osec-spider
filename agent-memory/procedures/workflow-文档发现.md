---
title: 工作流：文档发现任务（在线文档里的网盘链接）
type: procedure
status: active
created_at: 2026-09-16T09:30:00+08:00
updated_at: 2026-09-16T09:30:00+08:00
priority: high
keywords: [文档发现, doc-discovery, docfind, 腾讯文档, 金山文档, 飞书, 石墨, link3.cc, GitHub代码搜索, 候选渠道, docfetch, docverify]
questions:
  - 怎么找包含网盘链接的在线文档（腾讯/金山/飞书/石墨）
  - task doc-discovery / 启动文档发现任务 该怎么做
  - 文档发现的候选渠道有哪些、哪个性价比高
summary: `task doc-discovery` 的入口、验收口径、渠道性价比与硬规则；流程与脚本在 COMMON site-discovery/tools/docfind/README.md
load: on-demand
related:
  - agent-memory/procedures/workflow-站点发现.md
  - agent-memory/knowledge/domain-在线文档免登录取数.md
  - agent-memory/lessons/failure-link3接口按IP限流直连百次即429.md
---

# 文档发现任务

## 触发词

`task doc-discovery`、`启动文档发现任务`、「找包含网盘链接的在线文档」。直接按流程干，不必复述需求。

## 正本在哪

- 方法论 + 标准流程 + 踩坑：COMMON `site-discovery/tools/docfind/README.md`
- 脚本：同目录 `github_harvest.py` / `link3_harvest.py` / `page_harvest.py` / `tg_harvest.py`（候选）
  → `cands.py`（汇总去重）→ `docfetch.py`（免登录抓正文抽链接）→ `docverify.py`（过滤 + 抽样有效率 + 报告）
- 已探索文档总表（防重复）：`site-discovery/doc-discovery/history.md`；每次任务明细 `doc-discovery/YYMMDD/`
- 四平台免登录取数细节：`knowledge/domain-在线文档免登录取数.md`

## 验收口径（与站点发现同源）

免登录 `ok` · 4 种受支持网盘去重 ≥100 条 · 平台修改时间在 30 天内 · 固定种子抽 40~50 条 `pancheck` 有效率 ≥60%（unknown 不进分母但披露）。

## 四条不能忘的

0. **link3.cc 接口按 IP 限流，直连约 100 次即 429**：批量必须 `--require-proxy`，且代理池只有个位数 IP 时优先跑 `--search`（关键词定向搜博主，4 百多个）而不是全量 sitemap（2 万用户要几小时）。
1. 动手前先 `python3 site-discovery/tools/selftest.py`（有效性判定依赖第三方接口）。
2. 金山/石墨必须走本机 9222 Chrome（`scripts/agent-browser.sh start`），串行约 1 篇/分钟，**多开 3 个 `--shard i/3` worker 并行**。
3. 所有探索过的文档都记进 `doc-discovery/history.md`（含不满足的）。

## 渠道性价比（2026-09-16 实测）

GitHub 代码搜索（千级，一次 1277 篇）≫ link3 关键词搜索（百级博主）> 文档聚合站 pan.gx.cn / 论坛帖 > 工具 WebSearch（每次 ~10 条）> 知乎/CSDN 文章 > Telegram 频道预览（几乎只贴网盘链接）。
百度/搜狗/必应/DuckDuckGo 用 curl 直搜基本拿不到结果；`site:kdocs.cn`、`site:shimo.im` 搜索引擎不索引正文。

## 与文档爬虫的关系

本任务只负责**找文档 + 验收**；满足的文档交给线上文档爬虫（`doc_scheduler` 队列 / 后台「文档」页提交）。
线上爬虫当前只解析金山表格，腾讯表格解析是 `current/tasks.md` 的 P1 任务——本任务实测的 opendoc 分块/逐 tab 取法可直接复用。
