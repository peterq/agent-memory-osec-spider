---
title: 未解决的问题
type: question
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-18T10:45:00+08:00
priority: high
keywords: [待确认, 十项提案重部, 存量测试代理, duanjuso速率, lzpanx, robots, 灰度误回落, 账号池]
summary: 待用户确认：站点爬虫运行时重构走哪条路（推荐先做单进程多站点宿主）；站点发现第二轮立项；账号池续期
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

## 站点发现 / 五站爬虫 收尾（2026-09-16）

- ✅ [用户裁定 09-16「合并上线」] 五站与十项提案已合入并 push，5 爬虫已上线（`current/tasks.md`）。
- [待确认] 十项提案涉及的网关/API/STORAGE/NC-JS **是否重部**（代码已合，前置项见 `agent-tasks/2026-09-16-ten-proposals/95-merge-plan.md`「上线前置项」）。
- [待确认] 存量 6 站的联网测试仍是 `NeedDirect:true` 直连，是否也改成走代理池（新 5 站已全部改）。
- [待确认] `www.lzpanx.com`（67.9 万条、其余 5 条达标）robots 声明 `Crawl-delay: 20`：是否遵守？遵守则单 IP 3 条/分钟需靠代理池多 IP 并行；不遵守则直接满足第 6 条。
- [待确认] duanjuso 线上抓取速率约 1 页/秒级且受代理抖动拖慢，150 万存量按此要数月：是否放宽 `services.duanjuso.minRequestInterval`/并发（需在线上配置加节）。

用户答复：

## 转存下载链路账号池是否续期（2026-09-13 体检发现）

正本 `knowledge/domain-转存下载链路.md` §6。链路当前无新任务且账号全失效：阿里 3 个在队账号 refresh token 失效、百度 0 可用账号。

- [待确认] 近期是否还有新的下载批次？若无，可先 `SetEnablePanAccount(false)` 把 3 个失效阿里账号出队，止住每分钟的无效重试日志。
- [待确认] 若要恢复，需人工提供新的阿里 refresh token / 百度账号，Agent 只能投递不能获取凭据。

用户答复：

## 站点爬虫运行时重构选型（2026-09-18）

- 用户提出用 FC + Lua/WASM 重构站点爬虫以压进程数/服务器成本；分析结论与四方案对比见 `knowledge/architecture-站点爬虫运行时方案对比.md`。
- 推荐先做 B「单进程多站点宿主」（3~5 天，零新增成本），FC 路线卡在蜻蜓代理 IP 白名单（需 NAT 固定出口）与按时长计费。
- 待用户裁定：走 B / 直接 A / 先做 B 再评估 D；并确认蜻蜓代理是否支持非 IP 鉴权、哪几台主机可退。
