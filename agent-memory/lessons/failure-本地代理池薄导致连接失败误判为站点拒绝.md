---
title: 失败经验：本地代理池太薄时，连接层失败会被误判成站点拒绝/反爬
type: lesson
status: active
created_at: 2026-09-16T10:40:00+08:00
updated_at: 2026-09-16T10:40:00+08:00
priority: high
keywords: [代理池, RemoteDisconnected, code=0, 站点发现, ratetest, 直连复核, 误判, 吞吐实测]
questions:
  - 调研站点时经代理大量连接失败，怎么分辨是代理问题还是站点封锁
  - 单 IP 吞吐怎么测才不被代理池噪声干扰
summary: 代理池薄时 code=0 像站点拒绝；直连复核 + ratetest 双出口对比，只有 403/429 才算限流
load: on-demand
related:
  - agent-memory/procedures/workflow-站点发现.md
  - agent-memory/lessons/success-本地代理池打通.md
---

# 本地代理池薄导致连接失败误判为站点拒绝

## 问题背景

2026-09-16 站点发现第二轮，本地代理池（生产 redis 频道同步）全程只有 1~7 个代理存活，
5 个子 agent 并发争抢。`triage.py` 初筛里 30+ 个站经代理出现**整齐的 ~5 s `Connection aborted / RemoteDisconnected`**，
`sitescan.py` 经代理「从 sitemap 取种子」频繁返回 0 条，`ratetest` 经代理 6/20 次 `code=0`。

## 失败表现

- 子 agent 把 `pan.xiaozi.cc` / `xiaojiwo.top` 的代理断连写成「疑似拒绝数据中心 IP」；`ddys.io` 吞吐因此「证据不足」；`duanjuso.cc` 吞吐测出 2.2 条/分钟被判不达标。
- 直连复核后：xiaozi/xiaojiwo 代理 3/3 成功（纯抖动）；duanjuso 直连 46 条/分钟、代理成功请求每页出链；ddys 成功段 13.6 条/分钟。**全部是代理侧问题，站点零 403/429。**

## 根本原因

- 代理池规模小 + 多 agent 并发 → 单个代理超时/被目标站 RST 的概率放大；`RedisProxyFeed` 的坏代理淘汰又让池子瞬时归零。
- 连接层失败（`code=0`）和站点限流（403/429/验证码）在工具输出里长得一样，子 agent 没有分开统计。

## 规避方法

1. **初筛阶段**：`FETCH_ERROR` 的站一律再用 `--no-proxy` 跑一次（未确认反爬的站允许直连初筛）；两条出口都失败才记「无法访问」。
2. **吞吐实测**：用 `tools/ratetest.py` 分别跑 `--require-proxy` 与 `--no-proxy`（无反爬迹象的站），只有 403/429 才算站点限流；`code=0` 归代理侧，报告里必须分开写。
3. **判定口径**：代理请求「有时成功」即抖动，整套评估继续走代理；只有代理**稳定** 0/N 而直连全成功，才怀疑站点拒绝代理出口。
4. 派子 agent 前先 `proxypool.py status` 看存活数；<5 个时提醒子 agent 降并发、放宽 timeout，并在简报里写明这条。

## 适用边界

只针对本地开发代理池（生产 proxy-provider 池子大得多）。已确认反爬的站点仍然禁止直连，只能靠放宽 timeout/重试等代理恢复。
