---
title: 站点知识：www.misoso.cc（影盘社，实抓 www.melost.cn）
type: knowledge
status: active
created_at: 2026-09-03T18:10:00+08:00
updated_at: 2026-09-03T18:10:00+08:00
priority: medium
keywords: [misoso, melost.cn, 影盘社, 域名不一致, sitemap陷阱, 越界文件, 假200, hunhepan, ReMan, bbs_misoso]
summary: misoso.cc 实际抓取域名是 melost.cn；sitemap 有"过期快照"与"越界文件假200"两个陷阱；爬虫已于 2026-09-03 实现为 bbs_misoso（626万条规模，未实跑全量）
load: on-demand
related:
  - agent-memory/procedures/workflow-新站点调研.md
  - agent-memory/lessons/success-爬虫联网集成测试.md
  - agent-memory/knowledge/domain-站点-kkpans.md
---

# www.misoso.cc（影盘社，实抓 www.melost.cn）

需求文档正本：`osec-spider-go/PRD/2609/www.misoso.cc.md`（§11 是实现落地记录）
调研/对账脚本：`osec-spider-go/scripts/misoso_probe.py`

## 实现状态

- [事实 2026-09-03] **爬虫已实现并小样本联网实测通过**：命令 `./spider bbs_misoso`，
  代码 `osec-spider-go/services/bbs/misoso.cc.go`，集成测试 `services/bbs/misoso.cc_test.go`
  （默认跳过，`MISOSO_IT=1` 开启）。配置节 `services.misoso`（`config/config.go` 的 `MisosoConfig`）。
- [事实] **本次开发绝对未实跑全量**（626 万条规模），全量单轮条目数用环境变量
  `MISOSO_FULL_SWEEP_ITEM_LIMIT` 兜底，生产缺省值是 0(不限)。
- [事实] `deploy.sh` **未注册**，部署机器待定（kkpans 用的是单机 `osec-res1`，misoso
  规模是它的 1400 倍，可能需要专门评估）。

## 核心结论（2026-09-03 实测）

- [事实] **域名不一致**：`www.misoso.cc` 自身是 CSR 引流壳站，详情页请求 100% 返回
  HTTP 410；真实内容、sitemap、SSR 详情页全部在 `www.melost.cn`。爬虫的
  `ContentBaseUrl` 硬编码为 melost.cn，`Client` 提交标识仍用 `www.misoso.cc`。
- [事实] **sitemap 有两层坑，比 `workflow-新站点调研.md` 已记录的"域名不一致"更进一步**：
  1. `melost.cn` **自己** robots.txt 指向的 `/static/sitemap.xml` 是**过期快照**
     （只有 99 个 disk 文件，`lastmod` 全部停在 2025-03-07）；
  2. 必须用 `misoso.cc` robots.txt 指向的 `/static/sitemap/sitemap-index.xml`
     才是实时更新的那份（1254 个 disk 文件，与站点当前规模一致）。
  **教训**：即使拿到了"内容站自己的" robots.txt，也不能想当然认为它是最新的——
  同一个站点可能存在多份 sitemap，要用条目数量级/`lastmod` 交叉验证选对那份。
- [事实] **越界 disk-N.xml 返回假 200**：请求不存在的 `disk-9999.xml` 会被站点 SPA
  兜底成首页 HTML，HTTP 状态码仍是 200（`content-type` 从 `text/xml` 变成
  `text/html`），不是常见的 404。判断文件是否真实存在只能靠"响应体能否解析成合法
  `<urlset>` XML"，不能信状态码。这类"SPA 通配路由把任何路径都兜底成 200"的行为
  在其他现代前端框架站点上也可能出现，遇到"越界探测应该 404 却一直 200"时可以按
  这个思路排查。
- [事实] 该站用的是开源/商业模板 "ReMan"（`docs.hunhepan.com/reman/`），后续如果
  调研到同模板的其他资源站，本文档的 sitemap 结构、详情页 `class="jump-link"`
  抽取方式大概率可以直接复用。
- [事实] 数据规模：sitemap-index 下辖 **1254** 个 `disk-N.xml`(每个最多 5000 条) +
  1 个 `movie-1.xml`(42 条，实测不含网盘链接，内容已被 disk-*.xml 完整覆盖，爬虫不处理)。
  约 **626 万条**，是目前接入站点里规模最大的一个。disk 文件按序号递增追加，
  只有最新一个文件在增长，其余全部封存（5000 条打满不再变化）。
- [事实] **网盘类型构成随抽样批次波动明显**：site-discovery 首轮全站随机抽样 80 条
  是 quark 93.75% + ali-share 6.25%、0% 百度；本次只抽样"最新一批"(disk-1254.xml)
  却是 quark ~56%、**bnd(百度) ~44%**，未见 ali-share。结论：**不能用某一次抽样的
  类型占比做长期基线**，监控/复核要用运行时的真实分布。
- [事实] 详情页 SSR 渲染，链接位置固定在 `<a class="jump-link" href="...">`（页面里
  还有一个自引用的"复制本页链接" `jump-link`，靠网盘域名正则天然过滤，无需按 class
  特判）；提取码若存在已经拼在 href 的 `?pwd=` 里，不需要单独解析。
- [事实] 反爬：无验证码/登录墙，CDN 是 TencentEdgeOne；site-discovery 首轮实测
  并发 10 时 9/10 成功，建议并发 5~8。

## 与 kkpans 的设计差异（重要，别把 kkpans 的模式直接照搬）

- kkpans 的列表 API 自带 `share_link` 字段，翻页即可拿到全部数据；misoso 的
  sitemap **只给 URL 列表**，必须逐条请求详情页才能拿到链接——吞吐瓶颈是"详情页
  请求数"而不是"翻页次数"，626 万次请求意味着一轮全量预计要跑数天到数周。
- 全量遍历为此设计了**按 disk 文件的 redis cursor 断点续跑** + **单轮条目数硬顶
  的安全阀**（`FullSweepMaxItemsPerRound`，必须在"进入文件之前"截断，不能等处理完
  整个 5000 条的文件才检查，开发时先踩了这个坑才改对）。
- 去重键从"每条目一个 key"改成"每个 disk 文件一个 redis hash"（field=docId,
  value=lastmod），把 top-level key 数量从 626 万压到 1254，对 redis 更友好。
- **增量设计踩过一个坑**：最初想"多看尾部 2 个文件保险"，结果倒数第 2 个文件
  实测已经是写满 5000 条的封存文件，导致每轮增量都要多做 5000 次 redis 去重检查
  （虽然不产生 HTTP 请求，但违背"增量应该很轻"的设计目标）。已改成只看最新 1 个
  文件（唯一还在增长的那个）。**教训：站点是"只有最新文件会变化"的追加式存储时，
  增量不需要"多看几个保险"，看对那一个文件就够，多看反而增加无谓开销。**
