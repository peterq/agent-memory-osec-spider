---
title: 会话摘要：kkpans 站点调研与 PRD 产出
type: session
status: active
created_at: 2026-09-02T14:20:00+08:00
updated_at: 2026-09-02T16:05:00+08:00
priority: medium
keywords: [kkpans, 站点调研, PRD, 公开API, 探测脚本]
summary: 探索 www.kkpans.com 并产出爬虫需求文档，沉淀站点知识、调研工作流与对账脚本
load: on-demand
related:
  - agent-memory/knowledge/domain-站点-kkpans.md
  - agent-memory/decisions/decision-2026-09-02-停止磁力资源采集.md
  - agent-memory/procedures/workflow-新站点调研.md
---

# 会话摘要：kkpans 站点调研与 PRD

## 完成事项

- 全面探索 `https://www.kkpans.com`，摸清其公开 JSON API、SSR 数据通道与 sitemap。
- 全量拉取 7964 条资源 + 415 条磁力，与 sitemap.xml 逐条对账（零缺失零多余）。
- 产出需求文档 `osec-spider-go/PRD/2609/www.kkpans.com.md`（415 行，含接口表、字段实测统计、
  全量/增量策略、限速建议、5 个待确认问题、7 条可量化验收标准）。
- 沉淀调研脚本 `osec-spider-go/scripts/kkpans_probe.py`（probe / dump / latest / verify 四个子命令）。

## 关键发现

- 站点前端 bundle 里直接暴露了后端 REST 接口路径与全部查询参数名——
  **从 bundle 挖接口比逐个试 URL 快得多**，这是本次最省时间的一步。
- 该站**无任何反爬**，10 并发实测全 200。
- **不带 `platform` 参数时 `total` 只有 1505**（首页展示子集），若照此翻页会只抓到 19% 的数据。
  全量必须按 5 个 platform 分别拉。
- **页码越界会被钳制回最后一页并重复返回**，翻页循环必须双条件退出，否则死循环。
- 详情页数据与列表项完全一致，**不需要请求详情页**，全量只要 ~83 次请求。

## 新增或改变的事实

- 站内 46.1% 的资源是光鸭云盘（`www.guangyapan.com`）与 UC 网盘（`drive.uc.cn`），
  现有 `spider_contract` 无对应类型，**接不进现有链路**。
- [用户确认] **项目已整体停止磁力/BT 的采集与入库**，只处理 4 种网盘类型。
  这是本次会话最有价值的产出——它是项目级约束，此前记忆里把磁力写成了在采集范围内，已全面更正。

## 做出的决策

用户答复 PRD §8 的 5 个问题：

| # | 决策 |
|---|---|
| Q1 | 光鸭 + UC **本期排除**，只采 quark/xunlei/baidu 共 4295 条 |
| Q2 | 站点侧元数据**不带**进 ES |
| Q3 | **磁力整体不处理、不入库**（项目级约束，见决策记录） |
| Q4 | **不接**关键词队列 |
| Q5 | 经 `deploy.sh` 部署到 **`osec-res1`** |

已据此改写 PRD（删除全部磁力开发内容，§8 由"待确认问题"改为"已确认决策"，验收标准增加
"全程未调用磁力接口"一条），并新建 `decisions/decision-2026-09-02-停止磁力资源采集.md`。

用户随后又定了三项实现细节：命令名 `keyword_kkpans` → **`bbs_kkpans`**（新建 `services/bbs` 包，
文件 `kkpan.com.go`，因为该爬虫是全站遍历型而非关键词驱动）；
**全量周期 24h → 30 天**（退化为兜底补漏）；**增量周期 10 分钟 → 30 分钟**（成为日常主力）。

## 遇到的问题

- `grep -oE` 在含中文的大 JS bundle 上会报 "exceeds complexity limits"，改用 Python 正则处理。

## 后续行动

- 开发 `keyword_kkpans` 爬虫，PRD 已定稿、决策已确认，无阻塞。

## 值得沉淀的经验

已提炼到 `procedures/workflow-新站点调研.md`（通用调研步骤 + 四项必测）
与 `knowledge/domain-站点-kkpans.md`（该站专属结论）。
