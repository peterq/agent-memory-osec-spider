---
title: 站点知识：www.kkpans.com（KK网盘）
type: knowledge
status: active
created_at: 2026-09-02T14:20:00+08:00
updated_at: 2026-09-02T15:25:00+08:00
priority: medium
keywords: [kkpans, KK网盘, 站点调研, 公开API, SSR, 光鸭云盘, 磁力, PRD]
summary: kkpans 的公开 JSON API、分页陷阱、数据规模与采集范围（只采 quark/xunlei/baidu 4295 条）；爬虫已于 2026-09-02 实现为 bbs_kkpans
load: on-demand
related:
  - agent-memory/procedures/workflow-新站点调研.md
  - agent-memory/decisions/decision-2026-09-02-停止磁力资源采集.md
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/knowledge/concept-术语表.md
---

# www.kkpans.com（KK网盘）

需求文档正本：`osec-spider-go/PRD/2609/www.kkpans.com.md`（§11 是实现落地记录）
调研/对账脚本：`osec-spider-go/scripts/kkpans_probe.py`

## 实现状态

- [事实 2026-09-02] **爬虫已实现并联网实测通过**：命令 `./spider bbs_kkpans`，
  代码 `osec-spider-go/services/bbs/kkpan.com.go`，集成测试 `services/bbs/kkpan.com_test.go`
  （默认跳过，`KKPANS_IT=1` 开启；`KKPANS_IT_ALL=1` 跑全量 4295 条约 45 秒）。
  配置节 `services.kkpans`（`config/config.go` 的 `KkpansConfig`），部署 `./deploy.sh kkpans` → `osec-res1`。
- [事实] 实现相对 PRD 有 4 处刻意偏差（缺省视为开启 / redis 键前缀可注入 / 增量首轮只取一页 /
  去重 TTL 由全量周期推导），理由见 PRD §11.2。

## 核心结论（2026-09-02 实测）

- [事实] 站点是 React SPA + 自研 SSR（`x-kkpan-ssr: react`，Express + Cloudflare）。
- [事实] **存在无鉴权公开 JSON API**，是首选采集通道：
  - `GET /api/resources/public?page&limit&platform&sort&search&file_type&source_id&category_slug`
  - `GET /api/magnets/public?page&limit&search&sort`
  - `GET /api/resource-categories/public`
- [事实] **无任何反爬**：无验证码/Cookie/签名/Referer/UA 校验；10 并发实测全 200。
  robots.txt 只禁 `/admin`、`/api/admin/`、`/api/auth/`。
- [事实] **列表项已含 `share_link`，不需要请求详情页**——详情页的 `resource` 字段与列表项完全一致。

## 三个必须知道的坑

1. **不带 `platform` 时 `total` 只有 1505**，那是 `show_on_homepage=true` 的子集。
   全量遍历**必须按 platform 逐个拉**（quark/baidu/guangya/xunlei/uc，合计 7964，与 sitemap 完全一致）。
2. **`limit` 服务端硬上限 100**，传 500/1000 被静默截断为 100；magnets 传 200 直接 400。
3. **页码越界不报错**：超出末页会被钳制回最后一页并**重复返回同样数据**。
   翻页退出条件必须是 `len(data) < limit` **或** `resp.page != 请求的 page`，
   否则会死循环。

## 数据规模与支持度

| platform | 域名 | 条数 | 现有链路 |
|---|---|---|---|
| quark | pan.quark.cn | 4254 | ✅ TypeQuark |
| guangya（光鸭云盘） | www.guangyapan.com | 3624 | ❌ 无此类型 |
| uc | drive.uc.cn | 45 | ❌ 无此类型 |
| xunlei | pan.xunlei.com | 35 | ✅ TypeXunlei |
| baidu | pan.baidu.com | 6 | ✅ TypeBnd |
| 磁力 | magnet: | 415 | ⛔ 项目已停止磁力采集 |

- [用户确认 2026-09-02] **本期采集范围 = quark + xunlei + baidu = 4295 条**。
  光鸭+UC 3669 条（46.1%）需新增网盘类型，本期排除；磁力 415 条按项目全局约束不采集。
- [用户确认 2026-09-02] 爬虫命令 `bbs_kkpans`，代码落在 `services/bbs/kkpan.com.go`（新建 `services/bbs` 包，
  用于承载论坛/站点遍历型爬虫，区别于关键词驱动的 `services/keyword/`）；
  全量遍历 30 天一轮（兜底补漏），增量 30 分钟一轮（日常主力）；经 `deploy.sh` 部署到 `osec-res1`。
- [事实] 站点收录跨度 2026-06-03 ~ 2026-09-01，日均新增约 90 条。
- [事实] `sort=oldest` 是稳定的全量遍历序（API 100/页 与 HTML 24/页 两条通道各跑一遍，去重后均恰好 == total，零重复零遗漏）；
  但它**不是严格按 created_at 排序**，不能靠时间提前终止。
- [事实] `sort=latest` 按 `updated_at` 倒序，适合做增量水位线。

## 备用通道

若 `/api/*` 被关闭：每个 SSR 页面 `<body>` 末尾有
`<script>window.__KKPAN_SSR_DATA__ = {...}</script>`，含同样的数据，
但每页固定 24 条、查询参数名不同（页面用 `content_type`，API 用 `file_type`/`platform`）。
`/sitemap.xml`（1.5MB）含全部明细 URL 与 `lastmod`，`/rss.xml` 含最近 100 条，可作低成本变更探针。
