---
title: 工作流：资源站点调研与 PRD 产出
type: procedure
status: active
created_at: 2026-09-02T14:20:00+08:00
updated_at: 2026-09-03T18:10:00+08:00
priority: high
keywords: [站点调研, 爬虫, PRD, SSR, 公开API, 分页陷阱, sitemap, 对账, Flarum, 积分制, IP配额, 域名不一致, 过期sitemap, 越界文件假200]
summary: 接到"探索某资源站并输出爬虫 PRD"时的标准步骤：先找结构化接口，再验证全量可枚举性，最后对账
load: on-demand
related:
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/knowledge/domain-站点-kkpans.md
---

# 资源站点调研 → PRD 工作流

## 顺序（从便宜到贵，找到就停）

1. **`robots.txt` / `sitemap.xml` / `rss.xml`**
   - sitemap 常常直接给出**全站条目总数与明细 URL**，是后续对账的黄金基线。
   - 有 `lastmod` 就意味着可做增量。
2. **首页 HTML**：判断是 SSR 还是纯 CSR。
   - 找 `window.__XXX__ = {...}` 这类 SSR 注水数据（比解析 DOM 稳得多）。
   - React Router/Next 类站点还可能有 `.data` / `?_data=` / `__NEXT_DATA__` 通道。
3. **前端 JS bundle**：`<script type="module" src="/assets/index-*.js">`，
   下载后搜 `/api/`、`URLSearchParams`、`public`、`limit` 等，
   **往往能直接挖出后端未公开文档的 REST 接口和全部查询参数名**。
   > 注意：bundle 里 admin 接口也会一并暴露，**只用 public/无鉴权的那部分**，不要碰 `/admin`、`/auth`。
4. **确认参数枚举值**：在 bundle 里找选项数组（如 `[{label:"夸克",value:"quark"},...]`）比逐个试参数快。

## 必须实测验证的四件事

| 项 | 怎么验 | 常见坑 |
|---|---|---|
| **全量可枚举性** | 各筛选维度的 `total` 相加，与 sitemap 条数比对 | 默认列表常只返回"首页推荐"子集，`total` 远小于真实全量 |
| **分页上限** | 传 `limit=100/500/1000` 看返回条数 | 服务端静默截断，不报错 |
| **越界行为** | 请求 `page=末页+1` 和 `page=9999` | 很多站会**钳制回最后一页并重复返回**，翻页循环必须用 `len(data)<limit \|\| resp.page!=req.page` 双条件退出 |
| **排序稳定性** | 用目标 sort 跑完整一轮，看 `len(去重集合) == total` | 按时间排序的列表在翻页期间会漂移，导致漏抓 |

## 限流探测

先串行 20 次看是否有 429，再并发 10 次看是否有 429。
**探测结果要写进 PRD**（并发数、间隔、超时的建议值必须有实测依据，不要拍脑袋）。
**限流不一定表现为 429**：2026-09-03 探测 `kuakes.com` 时，并发 10 直接触发了连接层面的
封锁（`curl`/`requests` 连接超时，HTTP 状态码都拿不到），且波及到之后几分钟内**所有**请求
（包括普通页面 GET），过一段时间（约1~2分钟）自动解封；串行 40 次、并发 4 次都稳定无问题。
遇到"连接超时/拒绝"而不是 429 时，同样按限流处理（退避重试，别当成站点挂了），
并把"安全并发数"（本例是 ≤4~5）写进结论。

## 识别"网盘资源站建站插件/模板"，一眼定位链接接口

不少 WordPress 网盘资源站用的是同一批商业插件/主题（如 `storeys` 主题 +
`magicpost` 插件），特征：详情页正文里**没有**直接暴露的网盘分享链接，只有一个
`<a class="j-wbdlbtn-magicpost" data-pid="<文章ID>" data-rid="...">XX网盘转存</a>` 按钮；
真正的链接要靠前端 JS 发 `POST /wp-admin/admin-ajax.php`（`action=wb_mpdl_front&pid=&rid=`）
换回来（返回体形如 `{"code":0,"data":{"url":"https://pan.quark.cn/s/...","pwd":""}}`）。
遇到"sitemap 里全是文章页，但正文 regex 抓不到任何网盘链接"时，先看页面里有没有
`magicpost`/`wbdlbtn`/`admin-ajax` 这类线索，再去翻插件的 `assets/*.js`
（通常是打包压缩过的，搜 `ajax_url`/`fetch`/`action:` 就能找到真正的接口和参数名），
比假设"这站需要登录才能拿链接"更准——实测这类站的 ajax 接口大多**不需要登录**
（只是前端文案会吓唬你"游客免费次数已用完"，不代表接口真的按此限流，需要实测验证）。

## sitemap 声明存在但实际死链 / 内容域名与访问域名不一致

2026-09-03 调研 `quark4k.com`（Flarum 论坛）和 `misoso.cc` 时踩到两个变种坑：

1. **`robots.txt` 里的 `Sitemap:` 声明了，但子 sitemap 实际 404**（如 `quark4k.com/sitemap.xml`
   指向 `sitemap-0.xml`，请求返回 404）。这解释了初筛脚本"未探到 sitemap"的原因——
   不能因为 `robots.txt` 里写了就认为 sitemap 可用，必须**逐级请求到叶子文件**才算数。
   遇到这种情况且站点是知名论坛程序（Flarum/Discuz/NodeBB），优先找**该程序自带的公开 JSON API**
   替代 sitemap 做规模盘点：Flarum 是 `GET /api/discussions?page[limit]=1&page[offset]=N`
   （**注意 `curl` 必须加 `--globoff`，否则会把 `[limit]` 当成 URL glob 语法**），
   用二分查找 offset 定位总数，比逐页 BFS 快得多；`GET /api/tags` 还能拿到分类计数交叉验证。
2. **`robots.txt`/首页引用的 sitemap 域名和实际访问域名不是同一个**：`www.misoso.cc` 的
   `robots.txt` 直接指向 `www.melost.cn` 的 sitemap，而且 sitemap 里的 URL 也全是
   `melost.cn`。**直接用 misoso.cc 自己的域名去拼详情页路径会 410**——遇到"首页能开、
   但 sitemap/资源全部指向另一个域名"时，必须用**目标 URL 本身给出的域名**发请求验证，
   不能想当然地在被评估域名上拼路径；调研结论里要明确写清楚"真正该抓的域名是哪个"。
3. **内容站自己的 robots.txt 也可能指向一份过期 sitemap**：上面这个案例里，
   `melost.cn` 自己的 robots.txt 指向 `/static/sitemap.xml`，这份文件只有 99 个
   子文件、`lastmod` 全部停在 2025-03-07；而 `misoso.cc` 的 robots.txt 指向的是
   `/static/sitemap/sitemap-index.xml`，有 1254 个子文件，才是实时更新的那份。
   **两份 sitemap 都能正常打开、都不报错**，唯一能分辨新旧的办法是比较条目数量级
   和 `lastmod`。教训：拿到 sitemap 后先看条目数是否和站点其他规模信号（如首页
   "共 XX 万条"文案、分类计数）量级一致，不一致就要怀疑是不是拿到了旧快照。
4. **越界的分页/子 sitemap 文件可能返回"假 200"而不是 404**：现代前端框架站点
   常见 SPA 通配路由兜底，请求一个不存在的子 sitemap（如 `disk-9999.xml`）会返回
   HTTP 200 的首页 HTML，而不是 404/410（`content-type` 会从 `text/xml` 变成
   `text/html`，但状态码看不出异常）。判断文件是否真实存在不能只看状态码，要看
   "响应体能否解析成预期的结构"（如合法的 `<urlset>` XML）。

## 搜索型/积分制站点：搜索响应可能已经直出真实链接，无需再调"详情/兑换"接口

2026-09-03 调研 `haisou.cc`（Nuxt SPA + 积分/会员系统）：前端有一整套"搜索扣积分、
查看详情再扣积分"的产品设计（`credit_cost_search`、`credit_cost_fetch_share` 等字段
在 `/api/v2/common/configs` 里都能查到），**但直接绕过前端、纯 HTTP 调用 `search` 接口，
返回体里已经带了真实的 `share_code`/`share_pwd`，且 `meta.credits_consumed` 记录为 0**——
不要被前端 UI 的"看起来要花钱/要登录"吓退，先直接试裸接口，很多时候详情/兑换那一步
只是 UI 层面的转化钩子，数据本身在搜索响应里已经给全了。
但要注意**匿名调用通常有 IP 级别的每日免费额度**（该站约 50 次/天，超额返回业务码
`{"success":false,"error":{"code":11003,"message":"今日额度已用完，请明天再试"}}`，
HTTP 403），规模化爬取要按"多 IP 轮换"或"批量注册账号（若注册门槛低，如仅需邮箱验证码）"
设计，写进 PRD 的限速/账号策略里，不能假装无限量。

## 网盘 ID 拼接：不同来源站给的 share_code 格式可能已经包含固定前缀

百度网盘的标准分享链接是 `pan.baidu.com/s/1<code>`，`site-discovery/tools/panlink.py`
里的正则/模板都是按"`code` 不含开头的 `1`"设计的。但**从第三方聚合站的搜索/列表接口拿到的
`share_code` 字段，可能已经自带这个开头的 `1`**（如 haisou.cc）——直接套用
`https://pan.baidu.com/s/1{share_code}` 模板拼接会导致**双写一个 `1`，所有链接实测全部失效**，
容易被误判成"这个来源的百度网盘链接质量差"。**拼接前务必打印几个真实样例人工确认前缀**，
或者两种拼法都跑一遍 `pancheck.py` 对比有效率，选有效率明显更高的那种。

## 产出

1. **PRD** → `osec-spider-go/PRD/YYMM/<域名>.md`。必须包含：
   站点概况与反爬结论、接口清单与参数表、字段实测特征（含空值/异常值统计）、
   与现有 `spider_contract` 类型的支持度对照、全量/增量策略、限速建议、待确认问题、**可量化的验收标准**。
2. **调研脚本** → `osec-spider-go/scripts/<站点>_probe.py`，
   至少支持 `probe`（打印总数与字段样例）/ `dump`（全量导出）/ `verify`（与 sitemap 对账）。
   开发完成后用它给 Go 爬虫做入库对账，站点改版时也靠它第一时间发现。

## 与现有链路对接的固定套路

- 网盘分享链接：`spider_common.NewResLinkCommitter().CommitResLink(&ResLink{Url, Pwd, Client, Refer})`，
  内部按 `spider_contract.TypeFromUrl` 分发。**不支持的网盘类型必须在提交前过滤掉**，
  否则会命中 `default` 分支刷 `unsupported type` 错误日志。
- 磁力：**不采集**。项目只处理 4 种网盘类型，见 `decisions/decision-2026-09-02-停止磁力资源采集.md`。
  调研时站点的磁力接口可以记录留档，但不产生开发任务。
- 参考实现：`services/keyword/keyword2024/www.pansearch.me.go`（结构最完整的近代爬虫）。
