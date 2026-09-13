---
title: 项目变更记录（总览归档）
type: knowledge
status: active
created_at: 2026-09-12T11:30:00+08:00
updated_at: 2026-09-13T15:55:00+08:00
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

## 2026-09-13

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
- 02:17 P4 shortfall 89 条定性为 longBoundary 漂移（零丢失），mover 归位 102,601 父文档，终态对拍 0.001% 级。→ `lessons/failure-longBoundary漂移导致父子跨索引与shortfall误报.md`

## 2026-09-11

- 10:25 P4 全量 bootstrap 作业 id=8 终结为 `done`（05:16 曾因 verify 差额 0.107% 判 failed，经 cancel id=4 + repair id=10 修正后 retry 通过）。→ `sessions/2026/2026-09-11-p4-bootstrap接管巡检与校验失败取证.md`、`lessons/patterns-长周期生产巡检.md`
- 子 Agent 在 legacy 索引跑 `has_child` 计数导致 ES 节点重启、集群 red 27 分钟。→ `current/risks.md`

## 2026-09-10

- 上午代理池监控上线闭环：「代理池总览」全 0 定位为上报侧未部署，`proxy` + 20 个爬虫 service 重部后即有数据；新增只读巡检 `tools/proxy-admin-check`。→ `procedures/troubleshooting-代理池总览无数据.md`、`sessions/2026/2026-09-10-代理池监控上线.md`

## 2026-09-09

- 凌晨完成「配置按进程拆代码」（SPIDER `4f5f528`→`883daeb`），网关双机 11:53/12:04 部署，爬虫容器与 proxy 于 09-10 全部重部；09-08 按"拆两份文件"理解的实现已整体回退。→ `decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`、`lessons/failure-把拆配置理解成拆文件.md`

## 2026-09-08

- 夜间并行四任务（告警入后台 / 代理池监控入后台 / 资源链接路径追踪 `TraceResLink` / 文档爬虫上云 `fc-chrome` + `doc_crawler`），五仓库已 push 未部署。→ `sessions/2026/2026-09-08-并行四任务监控与文档爬虫上云.md`、`lessons/failure-旁路能力初始化拖垮主流程.md`
- 后台登录改 GitHub OAuth（限 1second 组织成员），三仓已 push 未部署；两轮桩网关 + 调试浏览器联调各抓到一个阻断级缺陷。→ `decisions/decision-2026-09-08-后台登录改为github-oauth.md`、`sessions/2026/2026-09-08-后台登录改为github授权.md`
- `res_lc_*` 数据纳入管理后台（只读，并行 agent 开发）。→ `sessions/2026/2026-09-08-res_lc数据纳入后台.md`、`lessons/failure-proto3零值与负一哨兵冲突.md`
- 配置 v2 上线遗留处置：二进制无本地回落导致未重部的老容器重启即挂，已逐台重建；前端 gwEndpoint 默认值缺陷修复重发。→ `lessons/failure-配置v2二进制无本地回落导致老容器重启即挂.md`、`lessons/failure-前端环境默认值写死本地.md`
- spiderAdmin 线上样式丢失（qiankun 子应用挂错容器）修复。→ `sessions/2026/2026-09-08-spiderAdmin样式修复.md`、`lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md`

## 2026-09-07

- 用 archify 产出资源生命周期架构图。→ `sessions/2026/2026-09-07-资源生命周期架构图.md`、`archive/2026/success-archify画图的几何约束.md`

## 2026-09-05

- 生命周期改造 P0→P3 全部上线并核验通过（67 张 `res_lc_*` 表、三索引四别名、STORAGE 双写、API v3）；遗留 osec-resdb 的 `es_endpoint` 指向已下线 ES 集群。→ `sessions/2026/2026-09-05-生命周期P0上线.md`、`sessions/2026/2026-09-05-生命周期P3上线.md`、`lessons/failure-resdb的ES端点指向已下线集群.md`
- Wave 1 五分支合并、生命周期代码五仓完成并推送（Phase 0 契约 → 5 Agent 并行 → 合并 → Opus 端到端验收）。→ `sessions/2026/2026-09-05-生命周期五分支合并.md`、`sessions/2026/2026-09-05-生命周期改造实施.md`、`archive/2026/success-生命周期改造验收发现.md`
- P4 全量 bootstrap 前三次启动失败与演练。→ `sessions/2026/2026-09-05-生命周期P4启动失败.md`、`sessions/2026/2026-09-05-生命周期P4演练.md`、`sessions/2026/2026-09-05-生命周期P4第三次尝试.md`
- 生命周期改造 PRD v1.1 定稿；实测更正真实资源总量 ≈ 4440 万（旧索引另有 2966 万无 join 的百度父文档）。→ `decisions/decision-2026-09-04-资源索引生命周期改造方案.md`、`knowledge/architecture-es索引现状.md`

## 2026-09-04

- 管理服务并入网关 + 前端两个子应用合并为 `admin/spiderAdmin`；此后管理类需求一律放 `services/gateway/` 下不新增进程。→ `decisions/decision-2026-09-04-管理服务并入网关.md`、`decisions/decision-2026-09-04-前端合并为spiderAdmin.md`
- 队列监控系统 queue-admin 全流程上线（调研→PRD→契约→前后端并行→验收→部署）。→ `knowledge/architecture-queue-admin.md`、`sessions/2026/2026-09-04-队列监控系统queue-admin.md`
- NC-JS 队列监控页开发（通用 schema 渲染器），过程中一次 `pnpm build` 意外上传生产 OSS。→ `sessions/2026/2026-09-04-队列监控前端开发.md`、`lessons/failure-ncjs构建脚本会自动上传OSS.md`
- 队列 v2 收尾清理完成，上线时暴露网关 ES 配置指向已下线集群。→ `decisions/decision-2026-09-04-队列v2统一走网关.md`、`sessions/2026/2026-09-04-队列v2改造收尾清理.md`、`lessons/failure-网关重启暴露ES集群已更换.md`
- `feat/sweep-guard-a/b` 合并冲突取舍。→ `decisions/decision-2026-09-04-合并sweep-guard分支冲突取舍.md`

## 2026-09-03

- 按 `./deploy.sh ps` 清理线上无进程的爬虫代码（21 个命令、26,228 行，含 09-04 第二轮补删）。→ `decisions/decision-2026-09-03-清理下线爬虫代码.md`
- 并行开发并合并站点发现首轮筛出的 6 个站点爬虫（4 个子 Agent + 独立 worktree）。→ `sessions/2026/2026-09-03-并行开发6站爬虫.md`、`knowledge/domain-站点-2609接入批次.md`、`procedures/workflow-并行开发多站点爬虫.md`
- 下线 `haisou.cc`（搜索端点对代理网段做端点级拦截 `13001`，客户端侧改造全部绕不开）。→ `decisions/decision-2026-09-03-下线haisou.md`、`lessons/failure-haisou搜索接口收紧.md`
- 统一 7 个新爬虫的保活语义（`alive()` 改为 `CommitResLink` 返回 nil 时调用）。→ `lessons/success-爬虫保活语义.md`
- 建立常态化「站点发现」任务并跑完首轮（初筛 47 / 深挖 23 / 合格 6）。→ `procedures/workflow-站点发现.md`、`sessions/2026/2026-09-03-站点发现任务首轮.md`
- 决定全站扫描不在启动时触发。→ `decisions/decision-2026-09-03-全站扫描不在启动时触发.md`

## 2026-09-02

- 修复夸克/阿里云盘链接有效性检测（业务码优先、限流不判失效、未知响应报错）。→ `sessions/2026/2026-09-02-修复夸克阿里有效性检测.md`、`knowledge/domain-网盘有效性检测.md`
- kkpans 站点调研与爬虫开发。→ `sessions/2026/2026-09-02-kkpans站点调研与PRD.md`、`sessions/2026/2026-09-02-kkpans爬虫开发.md`、`knowledge/domain-站点-kkpans.md`
- `PPIO → 1s` 重命名收尾与两处存量编译错误修复，四仓 `go build ./...` 全通过。→ `sessions/2026/2026-09-02-重命名收尾与修复编译.md`、`procedures/workflow-本地构建与验证.md`
- 停止磁力/BT 资源采集。→ `decisions/decision-2026-09-02-停止磁力资源采集.md`
- 初始化 `agent-memory/` 记忆体系。→ `sessions/2026/2026-09-02-初始化记忆体系.md`
