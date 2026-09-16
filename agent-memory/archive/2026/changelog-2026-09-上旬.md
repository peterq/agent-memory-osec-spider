---
title: 变更流水归档：2026-09-02 ~ 2026-09-08
type: archive
status: archived
created_at: 2026-09-16T09:00:00+08:00
updated_at: 2026-09-16T09:00:00+08:00
priority: low
keywords: [changelog, 变更记录, 2026-09 上旬]
summary: 从 current/changelog.md 拆出的 2026-09-02~09-08 一句话变更流水（磁力停采、清理下线爬虫、队列 v2、管理台合并、配置 v2、OAuth 等）
load: rarely
related:
  - agent-memory/current/changelog.md
---

# 变更流水（2026-09-02 ~ 2026-09-08）

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
- 下线 `haisou.cc`（搜索端点对代理网段做端点级拦截 `13001`，客户端侧改造全部绕不开）。→ `decisions/decision-2026-09-03-下线haisou.md`、`archive/2026/failure-haisou搜索接口收紧.md`
- 统一 7 个新爬虫的保活语义（`alive()` 改为 `CommitResLink` 返回 nil 时调用）。→ `lessons/success-爬虫保活语义.md`
- 建立常态化「站点发现」任务并跑完首轮（初筛 47 / 深挖 23 / 合格 6）。→ `procedures/workflow-站点发现.md`、`sessions/2026/2026-09-03-站点发现任务首轮.md`
- 决定全站扫描不在启动时触发。→ `decisions/decision-2026-09-03-全站扫描不在启动时触发.md`

## 2026-09-02

- 修复夸克/阿里云盘链接有效性检测（业务码优先、限流不判失效、未知响应报错）。→ `sessions/2026/2026-09-02-修复夸克阿里有效性检测.md`、`knowledge/domain-网盘有效性检测.md`
- kkpans 站点调研与爬虫开发。→ `sessions/2026/2026-09-02-kkpans站点调研与PRD.md`、`sessions/2026/2026-09-02-kkpans爬虫开发.md`、`knowledge/domain-站点-kkpans.md`
- `PPIO → 1s` 重命名收尾与两处存量编译错误修复，四仓 `go build ./...` 全通过。→ `sessions/2026/2026-09-02-重命名收尾与修复编译.md`、`procedures/workflow-本地构建与验证.md`
- 停止磁力/BT 资源采集。→ `decisions/decision-2026-09-02-停止磁力资源采集.md`
- 初始化 `agent-memory/` 记忆体系。→ `sessions/2026/2026-09-02-初始化记忆体系.md`
