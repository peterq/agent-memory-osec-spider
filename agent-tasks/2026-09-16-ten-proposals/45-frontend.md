# 角色 45：NC-JS 后台页面 —— 账号健康 / 站点健康 / 队列绝对阈值告警（提案 6、7 前端）

短名 `health-observe`。worktree：`ncjs-wt-health-observe`（分支 `feat/health-observe`，主控建好后才派）。依赖 COMMON `feat/health-observe` 分支的契约提交（hash 见 `99-notes.md`）。

## 目标

spiderAdmin 新增「账号健康」「站点健康」两个页面（列表 + 手动重检/确认下线候选），队列告警规则页支持新增的绝对阈值字段；全部带 mock 开关与冒烟测试。

## 必读

1. `agent-tasks/2026-09-16-share-search-overview/00-shared.md` §4.5（前端结构、RPC 客户端创建、mock 开关、可复用组件、冒烟测试范本）与 `40-frontend.md`（上一次页面的做法）。
2. `agent-memory/knowledge/architecture-nc-js-qiankun与后台页面.md`、`architecture-nc-js-网关对接.md`。
3. COMMON `common-wt-health-observe/rpc/spider/health_rpc/health.proto` 与 `queue_admin_rpc/queue_admin.proto`（字段语义以注释为准）。
4. TS 生成脚本 `nc-js/packages/catalyst/scripts/devops/protc_gen.sh`：**生成时 proto 来源要指向 `common-wt-health-observe`**（临时改路径，不提交脚本改动；生成物提交）。

## 硬性约束
- **绝不运行 `pnpm build`/`build-only`**。只允许 `pnpm exec vitest run`、`vue-tsc --build --force`、lint。
- 只改 `admin/spiderAdmin` 与 `packages/catalyst/contract/rpc/**` 生成物；菜单/插槽照既有写法。

## 交付
分支/提交、页面清单、mock 客户端方法覆盖、vitest 与 type-check 输出。
