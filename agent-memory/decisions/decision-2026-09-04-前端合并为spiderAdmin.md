---
title: 决策：docSpiderScheduler + resSpiderScheduler 合并为 spiderAdmin
type: decision
status: active
created_at: 2026-09-04T21:00:00+08:00
updated_at: 2026-09-04T21:00:00+08:00
priority: high
keywords: [spiderAdmin, NC-JS, 子应用合并, qiankun, 布局, apps.json]
summary: 两个后台子应用合并成 admin/spiderAdmin 并重做左侧栏布局，全应用只保留一条 RTC 连接
load: on-demand
related:
  - agent-memory/knowledge/architecture-nc-js.md
  - agent-memory/decisions/decision-2026-09-04-管理服务并入网关.md
---

# 决策：前端合并为 spiderAdmin

## 背景

NC-JS `admin/` 下 `docSpiderScheduler`（文档爬虫）与 `resSpiderScheduler`（资源配置 + 队列监控）
是两个独立 qiankun 子应用，各自建一条到网关的 RTC 连接、各自一套裸 `<Tabs>` 页面，
用户评价"过于简陋"，且两者面向的是同一批运维人员、同一个后端网关。

## 决策（用户 2026-09-04 拍板）

1. 合并为**一个**子应用 `admin/spiderAdmin`（`@nc/spider-admin`，`activeRule`/`homepage` = `/spiderAdmin`），
   删除两个旧目录。
2. 布局改为 **左侧栏 + 顶栏**（`Layout.Sider` + `Layout.Header`），侧栏三组菜单：
   队列监控（总览/队列详情/日志搜索/黑名单）、资源配置（配置项）、文档爬虫（爬取中/队列中/已收录）。
3. 全应用**只允许一条 RTC 连接**：`useGwClient()` 统一产出
   `spiderRpc / docRpc / resSchedulerRpc / downloadRpc / queueAdminRpc`。

## 关键实现点

- `queueAdminRpc` 挂到同一条 transport（前提是后端已并入网关，见
  `decision-2026-09-04-管理服务并入网关.md`）；`catalyst/.../spiderGw/queueAdmin.ts`
  从"独立连接管理"缩到只剩一个 `mock` 开关，`ModalQueueAdminConfig` 删除。
- 文档爬虫的 `Scheduler` 类不再自建连接，改由外壳把 client 传进来。
- 无 vue-router：菜单 key 存 localStorage（`layout/navState.ts`），
  `layout/LazyKeepAlive.tsx` 复刻原 AntDV `<Tabs>` 的"首次访问才挂载、之后只隐藏"语义，
  否则切菜单会丢掉分页/自动刷新状态。
- `Page` + `PageHeader` 统一页头与卡片式页体，`ConfigProvider` 统一主题 token。

## 影响与代价

- **`mfe()` 插件只 upsert 不删** apps.json 条目，旧的两条要人工用
  `admin/spiderAdmin/scripts/removeMfeApps.mjs`（默认 dry-run，加 `--yes` 才写）摘除。
- 旧子应用在 OSS 上的静态目录不会自动清理（无害，可择日删）。
- 前端各页面的 localStorage 键沿用旧值（`spiderGwConfig`/`gwEndpoint` 等），
  但页签选择键从 `schedulerTab`/`resSpiderSchedulerUi.tab` 换成新的菜单 key，
  老用户首次进入会落到默认页，属可接受的一次性体验。

## 复盘条件

若后续管理页面数量涨到左侧一级菜单放不下（>3 组、>12 项），再考虑引入真正的路由与二级折叠菜单。
