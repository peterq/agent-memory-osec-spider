---
title: 站点知识：2026-09 接入的 5 个资源站（dyyjmax/fuxipan/feikuai/kuakes/haisou）
type: knowledge
status: active
created_at: 2026-09-03T15:50:00+08:00
updated_at: 2026-09-03T15:50:00+08:00
priority: high
keywords: [dyyjmax, fuxipan, feikuai, kuakes, haisou, Flarum, 苹果CMS, magicpost, 站点接入, 子命令]
summary: 本批 5 个站点的形态、子命令、规模、各自的坑与实现状态；详细规格见各自 PRD
load: on-demand
related:
  - agent-memory/knowledge/domain-站点-misoso.md
  - agent-memory/knowledge/domain-站点-kkpans.md
  - agent-memory/lessons/failure-haisou搜索接口收紧.md
  - agent-memory/procedures/workflow-并行开发多站点爬虫.md
---

# 2026-09 接入批次（5 站）

本文件只记**记忆层面需要的索引与坑**，接口/参数/字段的完整规格在各站 PRD 里，
路径见下表。同批的 `www.misoso.cc` 单独成文，见 `domain-站点-misoso.md`。

## 总表

| 站点 | 子命令 | 形态 | 规模 | 实现状态 |
|---|---|---|---|---|
| `bbs.dyyjmax.org` | `bbs_dyyjmax` | Flarum 论坛，SSR + 公开 JSON API | 79987 帖 | ✅ 已合并，联网验收通过 |
| `fuxipan.com` | `bbs_fuxipan` | SSR 详情页 `/doc/<24位id>`，分级 sitemap | 约 30.75 万 | ✅ 已合并，联网验收通过 |
| `feikuai.tv` | `bbs_feikuai` | 苹果CMS，`/voddetail/<id>.html` id 枚举 | 约 1 万条含链 | ✅ 已合并，联网验收通过 |
| `kuakes.com` | `bbs_kuakes` | WordPress + magicpost 插件 | 5618 篇 | ✅ 已合并，联网验收通过 |
| `haisou.cc` | `keyword_haisou` | Nuxt SPA，关键词搜索型 | 约 565 万 | ⚠️ 已合并但**未联网验收** |

PRD 一律在 `osec-spider-go/PRD/2609/<域名>.md`；
探测脚本一律在 `osec-spider-go/scripts/<站点>_probe.py`（`probe`/`dump`/`verify`）。
代码：前 4 站在 `services/bbs/`，haisou 在 `services/haisou/`。

**全部未上线**（未接入 `deploy.sh`，部署主机待定），与 kkpans 现状一致。

## 各站要点与坑

### bbs.dyyjmax.org —— 本批最干净的站
- Flarum 自带公开 API `GET /api/discussions?page[limit]=N&page[offset]=M`，
  **curl 必须加 `--globoff`**，否则 `[limit]` 被当成 glob 语法。
  用二分查 offset 可精确定位总数（实测 79987，与 sitemap 完全一致）。
- ⚠️ **坑**：详情页 `<meta name="description">` 会把正文截断，产出**"腰斩"的分享链接 id**。
  爬虫只扫 API 的 `contentHtml`、不碰整页 HTML，从源头绕开。
  这类"页面某处存在残缺链接副本"的陷阱在别的模板站也可能有。

### fuxipan.com（伏羲盘）
- 无列表 API，纯 SSR + 分级 sitemap（`sitemap-index.xml` → 约 308 个子文件）。
- 详情页 `class="visit-link-btn"` 的 `href` 即完整分享链接（含 `?pwd=`），无独立密码字段。
- 限速约 4 req/s 无限流。类型高度集中于夸克（87%~91%）。
- 去重只在**明确终态**才标记，网络性错误留给下一轮重试——因为单条成本是一次详情页请求，
  比"列表接口一次拿一页"的站更贵，标错了代价大。

### feikuai.tv（飞快TV）
- 苹果CMS，`/voddetail/<id>.html` 按 id 递增枚举，空洞率约 12.9%，要能容忍 404 继续。
- ⚠️ 会 **301 跳到镜像域名 `feikuai.in`**，client 要允许跟随重定向。
- id 上界**动态探测、可配置**，不要写死（实测 257502，日增约 150~200）。
- 四种网盘齐全，但 `ali-share` 实测样本为零，该分支未端到端验证过。

### kuakes.com（酷客网盘社）
- WordPress + **magicpost 插件**：详情页正文**没有**链接，只有
  `<a class="j-wbdlbtn-magicpost" data-pid data-rid>` 按钮；
  真链要 `POST /wp-admin/admin-ajax.php`（`action=wb_mpdl_front&pid=&rid=`），**免登录**。
- ⚠️ **并发 >4 触发连接层封锁（不是 429，是连接超时/拒绝）**，波及之后几分钟内所有请求，
  约 1~2 分钟自动解封。并发缺省值必须 ≤4，且对"连接超时/拒绝"按限流处理（退避重试）。
- 100% 夸克。有效率随年龄衰减明显（2026 年 100%、2024 年 46%）。

### haisou.cc（海搜）—— ⚠️ 未验收
- 关键词搜索型，唯一入口 `POST /api/v2/shares/search`，无可枚举的资源目录。
  `scope` 必须传 `"title"`，否则返回 `10001` 参数有误。
- **百度 `share_code` 已自带开头的 `1`**，正确拼接是 `pan.baidu.com/s/{share_code}`，
  再套 `s/1{code}` 模板会双写导致全部失效。
- **当前跑不通**：`shares/search` 对代理池 IP 一律返回 `13001`(HTTP 429)，
  全新代理 IP 首次请求即被拒。详见 `lessons/failure-haisou搜索接口收紧.md`。

## 共同约定（本批 6 站一致）

- 只采 `bnd` / `ali-share` / `quark` / `xunleipan`，其余类型提交前过滤。
- 一律 `NeedDirect: false` + 无条件订阅代理池。
- 配置节在 `config/config.go`，全套内置缺省值 + `*bool` 开关（nil 视为开启）。
- 联网集成测试用「假 committer + 独立 redis 键前缀 + 环境变量开关」，
  默认 `t.Skip`，断言用站点自己返回的 total 对账。
