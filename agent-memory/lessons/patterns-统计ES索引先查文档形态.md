---
title: 可迁移模式：统计/迁移 ES 索引前先分清文档形态
type: lesson
status: active
created_at: 2026-09-05T11:00:00+08:00
updated_at: 2026-09-05T11:00:00+08:00
priority: high
keywords: [ES, join, nested, must_not exists, 文档形态, 统计漏算, 迁移前核查]
summary: 同一索引可能混着两代写入形态；只按 join=resource 统计会漏掉三分之二资源，任何统计/迁移前先做 exists/must_not exists 对账
load: on-demand
related:
  - agent-memory/knowledge/architecture-es索引现状.md
  - agent-memory/sessions/2026/2026-09-04-资源生命周期改造PRD.md
---

# 可迁移模式：统计/迁移 ES 索引前先分清文档形态

## 问题
2026-09-04 调研资源索引时按 `term join=resource` 统计得 1530 万父文档，方案与容量估算都按此写；
第二天复核 `must_not exists join` 才发现还有 2966 万无 join 的百度父文档（文件清单在 nested `filelist`），
真实资源总量 4440 万，PRD 全部数字返工。

## 推荐做法
1. 先 `docs.count` 对账：`总 docs = Σ(各形态父文档) + 子文档 + nested 内部文档`，对不上就说明漏了一种形态。
2. 对每个"用来分类的字段"（join / type / 某个标志位）都跑一遍 `exists` 与 `must_not exists`。
3. 抽样各形态各 1 条 `_source` 看清结构，再定 mapping / 查询 / 迁移方案。
4. 写入代码有多条路径（本例 STORAGE 的 `UpsertResource` 与 `UpsertBigResource`）时，逐条路径确认写出的文档长什么样。

## 适用边界
所有"存量索引长期演进、多套写入路径并存"的 ES/搜索系统；新建索引且单一写入路径时不需要。
