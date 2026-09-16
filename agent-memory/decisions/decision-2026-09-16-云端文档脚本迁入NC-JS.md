---
title: 云端文档爬虫脚本从个人仓库 userscripts 迁入 NC-JS apps/doc-cloud-spider
type: decision
status: active
created_at: 2026-09-16T11:20:00+08:00
updated_at: 2026-09-16T11:45:00+08:00
priority: high
keywords: [doc-cloud-spider, userscripts, NC-JS, 云端脚本, fc-chrome, doc-crawler, 迁移, 个人仓库]
questions:
  - 云端文档爬虫脚本 doc-cloud.user.js 源码在哪个仓库, 为什么迁到 nc-js
summary: 云端文档脚本从个人仓库 userscripts 迁入 NC-JS apps/doc-cloud-spider(独立 vite 包), 产物与 OSS 对象名不变; PC 端油猴插件暂留
load: on-demand
related:
  - agent-memory/knowledge/domain-飞书文档解析.md
  - agent-memory/knowledge/domain-腾讯文档表格解析.md
  - agent-memory/knowledge/architecture-fc-chrome文档爬虫上云.md
---

# 决策：云端文档脚本迁入 NC-JS `apps/doc-cloud-spider`

## 背景
线上 doc-crawler（SPIDER）通过 fc-chrome（COMMON）注入的云端脚本 `doc-cloud.user.js`，其源码、构建配置与验证脚本一直放在用户的**个人工程** `~/dev/projects/peterq/userscripts`（`src/cloud/`、`vite.cloud.config.ts`、`scripts/verify_cloud.py`、`scripts/qqdoc-verify.ts`）。项目生产链路依赖个人仓库不合理（[用户确认 2026-09-16]）。

## 要解决的问题
把项目相关代码收进项目仓库并做恰当重构，保证构建/测试/验证在项目内闭环，且不改线上契约（OSS 对象名、协议、SPIDER 配置缺省值）。

## 备选方案
- **A. NC-JS `apps/doc-cloud-spider`（选定）**：pnpm workspace 已有 vite/vitest/typescript 工具链，`apps/` 已有同类独立构建目标（cdp-driver）；前端提交框识别链接的 `spiderUtil.ts` 也在同仓库，改站点时一处改完。缺点：与后台子应用同仓，但它本来就是"前端工程"。
- B. COMMON `fc-chrome/` 旁挂 node 包：与注入方同目录，但 Go 仓库混 node 工具链、CI 与 gitignore 都要另起炉灶。
- C. SPIDER 内放：与 doc-crawler 同仓，缺点同 B。
- D. 单独新仓库：多一个仓库要维护，与"不新增进程/仓库"的取向不符。

## 最终决策
方案 A。包名 `@nc/doc-cloud-spider`，目录结构 `src/main.ts`（入口）+ `src/runtime.ts` + `src/sites/{kdoc,feishu,feishuParse,qqdoc,qqdoc/*}`，单测与夹具同迁；monkey 插件只在 `vite build` 启用，vitest/vite-node 共用同一 `vite.config.ts`；`verify:qqdoc` 用 `vite-node` devDependency 直跑，去掉个人仓库的 `dev-vite-node.mjs` 兜底；上传仍是人工 `pnpm upload`（同时写旧对象名 `kdoc.user.js`）。脚本头 version 0.3.0→0.3.1 以区分迁移后的首个构建。

## 决策原因
工具链现成、与前端识别逻辑同仓、`apps/` 已有先例；产物与 OSS 对象名不变，SPIDER/COMMON 只改注释，线上零变更。

## 影响
- 个人仓库 `userscripts` 的 `src/cloud/`、`vite.cloud.config.ts`、`scripts/{verify_cloud.py,qqdoc-verify.ts,dev-vite-node.mjs}` 成为**过时副本**，后续改动只在 NC-JS 做；[用户裁定 2026-09-16] **不删除**，也不要再去改它。
- PC 端油猴调度器插件（`userscripts/src/plugins/{scheduler,kdoc,spiderGw,panShareDownload}`，产物 `frontend/pan-admin-prod/doc_spider/userscript.user.js`）**未迁**：它与个人油猴框架（插件系统/Vue UI/xbridge）深度耦合，迁移=搬整个框架；且 doc-crawler 已能独立消费队列，该插件 [用户裁定 2026-09-16] **暂时不动**。
- 记忆仓库 `scripts/docspider/e2e-local-fcchrome.sh` 缺省脚本目录改为 `nc-js/apps/doc-cloud-spider/dist`。

## 复盘条件
若后续云端脚本要复用后台 catalyst 的 RPC 客户端（直接从页面提交而非 console 回传），再评估是否并入 `packages/`。

## 当前状态
[事实 2026-09-16 11:45] 用户确认后已合并：NC-JS `main`（`4d921bf` 合入，与 health-observe 并存）、SPIDER `master`（`8c9b1c0`），均已 push；worktree 与分支已删。合并后冻结 lock 安装 + 单测 59 + 构建复验通过。**待人工**：`apps/doc-cloud-spider` `pnpm build && pnpm upload`。
