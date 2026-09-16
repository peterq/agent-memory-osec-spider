---
title: 未解决的问题
type: question
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-16T11:30:00+08:00
priority: high
keywords: [待确认, doc-cloud-spider, 站点发现, lzpanx, robots, 立项, xlLoadShare, 事故恢复, 用户确认]
summary: 待用户确认：云端脚本迁移合并；灰度误回落防复发；站点发现立项；账号池续期
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

## 云端文档脚本迁入 NC-JS：合并与个人仓库收尾（2026-09-16 11:20）

正本 `decisions/decision-2026-09-16-云端文档脚本迁入NC-JS.md`，清单 `agent-tasks/2026-09-16-doc-cloud-migrate/00-shared.md`。

- [待确认] NC-JS `feat/doc-cloud-spider`（`4d921bf`）与 SPIDER 同名分支（`8c9b1c0`，仅注释）是否合并 main/master 并 push。
- [待确认] 个人仓库 `userscripts` 里过时的 `src/cloud/`、`vite.cloud.config.ts`、`scripts/{verify_cloud.py,qqdoc-verify.ts,dev-vite-node.mjs}` 及 `build:cloud/upload:cloud` 脚本是否由用户删除（Agent 不动个人仓库）。
- [待确认] PC 端油猴调度器插件（`userscripts/src/plugins/{scheduler,kdoc,spiderGw}`，与个人油猴框架耦合）是下线、还是后续单独立项迁入 NC-JS？

用户答复：


## 灰度误回落的防复发（2026-09-16 11:00）

10:51 canary 因 1 条 v3 500（深翻页 page=3678×15 > ES max_result_window 10,000；同参数 v2 同样 500）回落到 0%，11:00 已 `search-canary -set 43 -resume` 恢复。同类深翻页请求（机器人）会再次触发误回落。
- [待确认] 方案 A：API 层拦截 `page*pageSize > 10000`（返回空结果或 400），v2/v3 同改并重部——根治并修掉既有 500；方案 B：放宽 `error_ratio_max` 0.001→0.005、`min_sample` 200→1000（宿主机配置 + restart）；C：A+B。

用户答复：


## 站点发现第二轮：立项与 robots 裁定（2026-09-16）

正本 COMMON worktree `site-discovery-260916` 的 `site-discovery/history.md` 与 `260916/*.md`；摘要 `sessions/2026/2026-09-16-站点发现第二轮.md`。

- [待确认] 5 个满足站（duanjuso.cc ≈150 万条 / pan.xiaozi.cc / qileso.com / jsnoteclub.com / ddys.io）选哪些立项走 `workflow-新站点调研` 出 PRD？建议先 duanjuso.cc（公开搜索接口 + 直连 46 条/分钟）。
- [待确认] `www.lzpanx.com`（67.9 万条、其余 5 条达标）robots 声明 `Crawl-delay: 20`：是否遵守？遵守则单 IP 3 条/分钟需靠代理池多 IP 并行；不遵守则直接满足第 6 条。
- [待确认] worktree 分支 `worktree-site-discovery-260916`（报告 + 工具改动）是否合并 master。

用户答复：

## 转存下载链路账号池是否续期（2026-09-13 体检发现）

正本 `knowledge/domain-转存下载链路.md` §6。链路当前无新任务且账号全失效：阿里 3 个在队账号 refresh token 失效、百度 0 可用账号。

- [待确认] 近期是否还有新的下载批次？若无，可先 `SetEnablePanAccount(false)` 把 3 个失效阿里账号出队，止住每分钟的无效重试日志。
- [待确认] 若要恢复，需人工提供新的阿里 refresh token / 百度账号，Agent 只能投递不能获取凭据。

用户答复：

