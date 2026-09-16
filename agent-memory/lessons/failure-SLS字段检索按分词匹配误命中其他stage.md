---
title: 失败经验：SLS 字段检索 `stage:search` 按分词匹配，把 gin 访问日志 `GET:/api/v2/search` 一起算进搜索量
type: lesson
status: active
created_at: 2026-09-16T08:05:00+08:00
updated_at: 2026-09-16T08:05:00+08:00
priority: high
keywords: [SLS, 分词, 字段检索, stage, 精确匹配, where, search_admin, 日志聚合]
questions:
  - 用 SLS 按 stage/字段值统计时为什么数字翻倍或出现 null 行
  - SLS 检索语句怎么做字段精确匹配
summary: SLS 检索 `field:value` 是分词匹配，同一 logstore 里 `stage=GET:/api/v2/search` 的访问日志会被 `stage:search` 命中；统计口径必须再加 SQL `where stage in (...)`（或扫描路径按原值精确过滤），上线首日巡检对比数字才发现
load: on-demand
related:
  - agent-memory/knowledge/architecture-search-admin.md
  - agent-memory/knowledge/architecture-queue-admin.md
---

# SLS 字段检索按分词匹配，误命中其他 stage

## 问题背景
2026-09-16 上线搜索总览（网关 `search_admin`）后用 `tools/search-admin-check` 巡检：1 小时搜索量 2234，但 uid 榜第一名是 `null`（1534 次）、keyword 榜第一名也是 `null`，IP 榜 `avg=0ms`。

## 失败方法
检索前缀 `service:resource-search-api and (stage:search or stage:search-v3)`，以为 `stage:search` 是字段值精确匹配。

## 失败表现
API 的 gin 访问日志（`stage=GET:/api/v2/search`，`data` 里只有 `latency/status/ip`，没有 `uid/kw/duration`）被分词成 `GET / api / v2 / search` 后一起命中，每次搜索被计 2 条，且缺字段的行变成 `null`/0。

## 根本原因
SLS 全文/字段索引默认按分词符切分，`field:value` 是「字段的分词包含 value」，不是等值。同一 logstore 里只要有其他 stage 含同一个词就会串。

## 规避方法
- SQL 路径：检索前缀只做粗筛，真正口径写在 `| select ... where stage in ('search','search-v3')`（`where` 作用于原始字段值，等值）。
- 扫描（降级）路径：拿到原始日志后按 `stage` 原值精确过滤（`filterByEntry`）。
- 新增任何按 stage/type 的 SLS 统计，先用 `tools/sls-probe` 或 `search-admin-check` 看 Top 榜有没有 `null`/明显翻倍。

## 下次行动建议
凡是 SLS 计数类需求，上线当天必做「Top 榜有无 null 键」「总数与另一独立来源（如 Prometheus `http_requests_total`）量级对比」两项核对。

## 适用边界
SLS 检索语法；ES `term`/`match` 的同类差异也适用（`match` 分词、`term` 等值）。
