---
title: 失败经验：link3.cc 匿名接口按 IP 限流，直连约 100 次即 429
type: lesson
status: active
created_at: 2026-09-16T09:30:00+08:00
updated_at: 2026-09-16T09:30:00+08:00
priority: high
keywords: [link3.cc, 429, 限流, 代理池, no_auth/user, search_user, sitemap, 文档发现]
questions:
  - link3.cc 批量抓主页为什么 429，怎么绕
  - 代理池只有几个 IP 时 link3 全量该怎么跑
summary: link3 no_auth/user 接口按 IP 限流，直连约 100 次即 429；批量必须走代理池，代理少时改用 search_user 关键词定向搜博主
load: on-demand
related:
  - agent-memory/procedures/workflow-文档发现.md
  - agent-memory/procedures/workflow-站点发现.md
---

# link3.cc 匿名接口按 IP 限流

## 问题背景
文档发现任务要从 link3.cc（数字名片/聚合链接站）2 万个用户主页里找贴了在线文档的网盘博主。
前端逆向出匿名接口 `POST https://v5.api.link3.cc:5678/api/no_auth/user {"username"}`（`chunk_286` 里，`apiBaseUrl` 带 5678 端口）。

## 失败方法与表现
- 直连 6 并发跑全量：前 ~100 次 200，之后连续 1300 次 `http 429`，本机 IP 当场进入限流窗口（几分钟后才恢复）。
- 首次全量还在取 `sitemap.xml` 时就 ConnectTimeout——link3 出口偶发抖动，sitemap 要直连+重试，不要走代理。

## 根本原因
接口按来源 IP 计数限流（阈值约 100 次/窗口），与并发无关；切到代理池后每个代理 IP 各有同样额度。

## 规避方法（已固化在 `docfind/link3_harvest.py`）
1. 批量一律 `--require-proxy`；429 时 `pool.report_bad(sess.last_proxy, 90)` 换下一个代理（`httputil.ProxiedSession` 新增 `last_proxy`）。
2. 代理池只有个位数 IP 时（本机 `proxypool.py status` 常见 1~3 个），全量 2 万用户吞吐只有 15~50 条/分钟；**优先 `--search`**：`/api/search/search_user {currentPage, perPage, search}` 匿名可用，按"网盘/夸克/短剧/资源…"20 个词搜出 427 个博主，命中率远高于全量。注意分页对同一关键词返回重复结果，看到"新 0"就停。
3. sitemap 直连拿，公开静态文件不限流。

## 下次行动建议
如需全量，挑代理池充足的时段跑（`--resume` 可续），或把用户名清单分片交给线上爬虫走生产代理池。

## 适用边界
仅 link3.cc；其他 SPA 站逆向出的匿名接口同样要先小样本探限流阈值再放量。
