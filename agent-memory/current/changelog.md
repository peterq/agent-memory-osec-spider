---
title: 项目变更记录（总览归档）
type: knowledge
status: active
created_at: 2026-09-12T11:30:00+08:00
updated_at: 2026-09-16T19:30:00+08:00
priority: low
keywords: [变更记录, changelog, 历史, 总览归档, 生命周期改造, 队列v2, queue-admin, 站点接入, 配置v2, GitHub OAuth]
summary: 按日期倒序的一句话变更流水，每条指向 session/decision 文件；回答"某事哪天做的、细节在哪"
load: rarely
related:
  - agent-memory/00-overview.md
  - agent-memory/current/tasks.md
---

# 项目变更记录（总览归档）

> `00-overview.md` §2 只保留最近 7 天。更早的条目压缩成「日期 + 一句话 + 指针」放这里，
> **原文叙述在各自的 session / decision 文件里**，本文件不复制正文。需要细节就按指针读那一个文件。

## 2026-09-16
- 12:13 **[用户裁定「合并上线」] 十项提案 + 五站合入五仓库主分支并 push**（COMMON `0ead6c0`/`cd85518`、SPIDER `7acb24a`/`70bb955`/`7e4206c`、API `7154290`、STORAGE `3e0d490`、NC-JS `3ccd25d`），四仓 CI 全过；用新版 deploy.sh 逐站上线 5 爬虫（duanjuso/jsnoteclub@jenkins、xiaozi/qileso@res2、ddys@res1，三机首次迁到 releases/current 布局），健康检查全过；十项提案服务未重部 → `sessions/2026/2026-09-16-五站爬虫并行开发.md`、`current/risks.md` R5
- 13:45 **五站爬虫并行开发**：duanjuso/xiaozi/qileso/jsnoteclub/ddys 基于 `integration/ten-proposals` 骨架各开 worktree，5/5 开发+验收通过（2 站返工：测试/probe 直连改走代理池），集成分支 `integration/five-sites` 待用户确认合并 → `sessions/2026/2026-09-16-五站爬虫并行开发.md`、`knowledge/domain-站点-260916接入批次.md`、`decisions/decision-2026-09-16-新站爬虫基于骨架集成分支开发.md`
- 11:20 **云端文档脚本从个人仓库 userscripts 迁入 NC-JS `apps/doc-cloud-spider`**（源码/单测/验证脚本重排，产物与 OSS 对象名不变，单测 59 + 本机 fc-chrome 端到端通过）；11:45 用户确认后合入 nc-js main / SPIDER master 并 push，OSS 上传待人工 → `decisions/decision-2026-09-16-云端文档脚本迁入NC-JS.md`、`sessions/2026/2026-09-16-云端文档脚本迁入NC-JS.md`
- 10:45 **站点发现第二轮**（COMMON worktree `site-discovery-260916`）：98 候选→18 深挖→5 站满足（duanjuso/xiaozi/qileso/jsnoteclub/ddys）+ lzpanx 待裁定；新增 `ratetest.py`/`fetchraw.py`，`sitescan` lastmod 统计、`panlink` 解 atob → `sessions/2026/2026-09-16-站点发现第二轮.md`、`lessons/failure-本地代理池薄导致连接失败误判为站点拒绝.md`
- 10:10 **文档发现任务首轮**：逆向 link3 匿名接口、四平台免登录取正文、六渠道脚本化（COMMON `site-discovery/tools/docfind/`），候选 2042→达标 29 篇，批量任务输出为待执行清单 → `sessions/2026/2026-09-16-文档发现任务.md`、`procedures/workflow-文档发现.md`、`knowledge/domain-在线文档免登录取数.md`、`lessons/failure-link3接口按IP限流直连百次即429.md`
- 十项提案（第 3~12 项）9 条线并行开发 + 逐线验收 + 集成预演完成，用户确认后 12:02 合入五仓库 master/main 并推送；两个新脚本 `scripts/dev/{new_worktree_all,integration_check}.sh` → `sessions/2026/2026-09-16-十项提案并行开发.md`、`lessons/patterns-并行多角色开发的验收与集成.md`、`procedures/workflow-并行多任务开发与合并预演.md`
- 文档爬虫新增腾讯文档表格解析（云端脚本双格式 + 前端识别），本地端到端 6 文档全通；10:45 用户确认后重新集成到飞书重构后的 runtime/站点结构并合入 master/main 并 push，OSS 上传/前端发版待人工 → `sessions/2026/2026-09-16-腾讯文档表格解析.md`、`knowledge/domain-腾讯文档表格解析.md`

- 2026-09-16 飞书文档解析接入开发完成并经用户确认合入三仓库主分支（docx + 多维表格，云端脚本拆 runtime/站点，14 条真实文档验证；OSS 上传与前端发布待人工） → `sessions/2026/2026-09-16-飞书文档解析接入.md`、`knowledge/domain-飞书文档解析.md`
- 08:30 修 `scripts/mail/notify.py` 邮件正文未渲染（`env python3` 命中 miniforge 无 markdown 模块，静默退化 `<pre>`）：shebang 固定系统 python + 自动换解释器 + 内置兜底渲染器 → `lessons/failure-notify脚本静默降级把原始Markdown发成邮件.md`
- 08:05 **分享链接总览 + 搜索总览（SLS）+ p90 告警自动关闭匿名搜索** 上线（COMMON `f2f0881`、SPIDER `2e34623`/`65a1bf8`/`6cb69db`、API `2458a52`、NC-JS `dbbbbcc`）；上线首日修 SLS stage 分词误匹配 → `knowledge/architecture-search-admin.md`、`decisions/decision-2026-09-16-搜索p90告警关闭匿名搜索与总览数据源.md`、`lessons/failure-SLS字段检索按分词匹配误命中其他stage.md`、`sessions/2026/2026-09-16-分享链接与搜索总览纳入后台.md`

## 2026-09-15

- **2026-09-15** 新增 `scripts/mail/notify.py` Markdown→HTML 邮件汇报脚本（用户要求进度/异常及时邮件）→ `procedures/workflow-任务进度邮件汇报.md`、`02-user-preferences.md` 第 13 条
- 09:00 xlLoadShare 失败率修复上线（SPIDER `3270e10`：顶层文件入批次、状态码共用码表、空分享永久失败、失效上报 dry run）；SLS 导出工具 `tools/xl-fail-export` + 重投 288 条 → `knowledge/domain-迅雷分享爬取.md` §5/§6、`sessions/2026/2026-09-15-xlLoadShare修复上线.md`
- 06:46 xlLoadShare 失败率排查：任务级 39% 失败 = 客户端丢顶层文件 75% + 空文件夹 25%，状态码全当临时错误重试放大；新增探针 `scripts/xl_share_probe.sh` → `knowledge/domain-迅雷分享爬取.md`、`sessions/2026/2026-09-15-xlLoadShare失败率排查.md`

## 2026-09-13

- 19:05 转存下载链路体检：链路空转、账号池全失效；新增体检脚本 `scripts/dl_chain_health.sh` → `knowledge/domain-转存下载链路.md`
- 16:35 profile 锁改 2 s 心跳/6 s 过期/被占不等待 409（用户要求，`app-20260913k`），修冻结实例被重试唤醒续锁 → `lessons/failure-FC实例在WebSocket断开后立即冻结.md`
- 15:50 定时清理增加删 >30 天未使用 profile（用户要求，镜像 `app-20260913i`）→ `decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md`
- 14:30 **cdp3 挂 NAS 上线**（镜像 `app-20260913h`）：VPC+两个挂载点、`CDP3DATA`/`CDP3TEMP`、`extensions=` 策略强装、`profile=` 单 tar 持久化+锁、每日 04:30 定时清理；发现 FC 断开即冻结实例 → `decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md`、`sessions/2026/2026-09-13-cdp3挂NAS与持久化会话.md`
- 13:59 用户定规则：删除等不可逆功能上线前必须线上 dry run + 独立手段（CDP/查库）二次复核，禁止复用新功能代码复核 → `procedures/checklist-不可逆操作上线.md`、`02-user-preferences.md` 第 12 条
- 11:41 **fc-chrome 上线**：Tampermonkey 5.5.0 上 OSS、镜像经 jenkins 中转推 ACR、`nc-app-prod-cdp3` 部署、共用域名 `/cdp3/*` 路由（用户执行）、三处回填、两条脚本路径线上全通；期间修了 seedprep `/json/list` 解析、叠层缺策略、closeTarget 竞态、脚本 `@match` 缺 SSO 首跳四个问题。→ `sessions/2026/2026-09-13-fc-chrome上线.md`、`knowledge/architecture-fc-chrome文档爬虫上云.md`

- 2026-09-13 08:30 用户要求：commit-msg 违禁词钩子（邮箱正则、卧槽）→ `scripts/git-hooks/`，已装进本仓库 + 1S 五仓库 → `procedures/checklist-仓库脚本清单.md`
- 2026-09-13 07:55 用户要求：lint 长度改双阈值（>12,000 触发、压到 <6,000、9,000 起提示）→ `decisions/decision-2026-09-13-lint长度双阈值.md`
- 2026-09-13 07:40 状态核实：重爬 263k/1,152k（≈23%）；A' 探测 bnd_03 05:31 因 MySQL 查询失败停止待续跑 → `current/tasks.md`「进行中」

## 2026-09-12

- 2026-09-12 23:34 用户确认：误删 115.3 万条重爬开始（`tools/lc-recrawl` 试点 1,000 条 → 全量，`-rate 10`）；`e16bd98` 部署；Mongo 无数据事实记入 `knowledge/architecture-storage.md`
- 2026-09-12 23:05~23:11 用户授权：止血 → 部署 `b888846` → 发现 bnd「违规」tooltip 误判 930 条 → 修复 `06ef50d` 重新部署 → SPIDER rollout §15.5
- 2026-09-12 22:17 🔴 发现 lifecycle_checker 把 md5 当分享 id，115.5 万条误删（quark/ali）；修复 SPIDER `b888846`，止血待人工 → `lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`、rollout §15
- 2026-09-12 按 open-questions 答复推进：`:cur` 两窗口取证不搬；阶段 D 改 API 侧自动灰度（sonnet 开发中）→ `decisions/decision-2026-09-12-阶段D改由API侧自动灰度分流.md`；A' 探测驱动 `scripts/lc_legacy_probe_all.sh`
- 16:34 **P5 阶段 A/B 上线**：D1 旧链路失效同步钩子（网关双机）、API v2 valid 上报 lc + bnd 去 `has_child`（热态 bnd v3 反超 v2 2×）、A' 存量复检工具链；res2 网关重部遇 ssh 超时半完成态，新增 `deploy.sh redeployHost` 补救。→ `decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md`、`sessions/2026/2026-09-12-P5阶段AB上线.md`、SPIDER rollout §14
- 16:30 输出切 v3 前的 P5 准入计划（A 失效同步钩子 / B bnd 慢查询 / C 复测门槛 / D 灰度与回滚条件，最短 9 天）。→ SPIDER `PRD/res-lifecycle/p5-plan-2026-09-12.md`（`f42e0f2`）
- 15:30 P5 前置对拍跑完，**未通过**（首页重合度 84%、语料级 91.7%；4% 坑位是 legacy 已删 lc 未删的死链，其余是 match_phrase_prefix 分片展开彩票），待用户决策 D1~D4。→ `lessons/failure-v3首页重合度受前缀展开分片彩票影响.md`、`current/open-questions.md`、SPIDER rollout §13
- 15:00 用户确认弃用 report/likes/dislikes/addViews 等 update ES 文档的接口，不做 v3；v3 detail/fileCtx 结构兼容性核对完成。→ `decisions/decision-2026-09-12-弃用文档更新类接口.md`、`knowledge/api-v3-detail-filectx兼容性分析.md`
- 07:00 记忆目录迁至独立仓库 `~/dev/projects/peterq/agent-memory-osec-spider`。→ `02-user-preferences.md`
- 启动记忆系统瘦身（常驻 5.4 万字超规则，`scripts/mem/mem.py` 落地）。→ `decisions/decision-2026-09-12-记忆系统瘦身与脚本化加载.md`
- 02:17 P4 shortfall 89 条定性为 longBoundary 漂移（零丢失），mover 归位 102,601 父文档，终态对拍 0.001% 级。→ `archive/2026/failure-longBoundary漂移导致父子跨索引与shortfall误报.md`

## 2026-09-11

- 10:25 P4 全量 bootstrap 作业 id=8 终结为 `done`（05:16 曾因 verify 差额 0.107% 判 failed，经 cancel id=4 + repair id=10 修正后 retry 通过）。→ `sessions/2026/2026-09-11-p4-bootstrap接管巡检与校验失败取证.md`、`lessons/patterns-长周期生产巡检.md`
- 子 Agent 在 legacy 索引跑 `has_child` 计数导致 ES 节点重启、集群 red 27 分钟。→ `current/risks.md`

## 2026-09-10

- 上午代理池监控上线闭环：「代理池总览」全 0 定位为上报侧未部署，`proxy` + 20 个爬虫 service 重部后即有数据；新增只读巡检 `tools/proxy-admin-check`。→ `procedures/troubleshooting-代理池总览无数据.md`、`sessions/2026/2026-09-10-代理池监控上线.md`

## 2026-09-09

- 凌晨完成「配置按进程拆代码」（SPIDER `4f5f528`→`883daeb`），网关双机 11:53/12:04 部署，爬虫容器与 proxy 于 09-10 全部重部；09-08 按"拆两份文件"理解的实现已整体回退。→ `decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`、`lessons/failure-把拆配置理解成拆文件.md`

> 2026-09-02 ~ 2026-09-08 的记录已归档到 `archive/2026/changelog-2026-09-上旬.md`。
