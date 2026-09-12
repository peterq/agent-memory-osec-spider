---
title: 成功经验：生命周期改造端到端验收抓出的 5 类坑
type: lesson
status: archived
created_at: 2026-09-05T20:00:00+08:00
updated_at: 2026-09-12T22:36:00+08:00
priority: high
keywords: [验收, ES 6.7, refresh, _reindex, BatchUpsert, !id, recover, 作业 panic, 网关崩溃, index_role, 别名判据, 幂等]
summary: Opus 端到端验收在真实进程链路上抓出的阻塞级缺陷及其规避规则，写网关内长作业/ES 批量操作时对照检查
load: rarely
related:
  - agent-memory/sessions/2026/2026-09-04-资源生命周期改造PRD.md
  - agent-memory/lessons/patterns-并行重构的分阶段切分.md
---

# 生命周期改造验收发现（2026-09-05）

报告正本：`osec-spider-go/PRD/res-lifecycle/acceptance-2026-09-05.md`。

## 规则（写代码时对照）
1. **ES `refresh_interval=60s` 的索引上，`_reindex` / `_delete_by_query` / 搬迁后计数校验必须 `refresh=true`**，否则校验读到 0、源文档永远删不掉（开发与验收各踩一次）。
2. **`sql_util.BatchUpsert` 默认把 `id` 当自增主键剔除**：业务主键叫 `id` 的表必须传 `"!id"`，`created_at/updated_at` 要 ignore 让 MySQL 默认值生效。
3. **并入网关的任何后台作业 goroutine 必须 recover**：一个 nil map panic 会带崩整个 spider 网关（5 个既有 RPC 全挂）。验收要主动触发每种作业。
4. **"幂等"要在轮换之后再验一次**：按日期推导索引名的初始化在轮换后会撞 `has more than one write index`，还会把刚删的旧索引重建出来。
5. **上报接口不能复活终态行**：`ReportUpsert` 对 `status=invalid` 的行要么忽略要么按新入库重置，不能只改 status。
6. **流转判据用真实别名指向，不用 DB 里的角色字段**：角色字段没人回填就永远不命中，且不报错。
7. **fail-fast 要在启动期**：配置缺失延迟到首个请求才 Fatal，进程会先"假装健康"骗过部署检查。
8. **联调用例建的 index template 必须在用例结束时删除**，否则匹配 `res_short_*` 的残留模板会让后续建索引 400。
9. 验收 Agent 用 opus、并给它"直接修小问题"的权限，性价比高：本次 269 次工具调用抓出 2 个阻塞 + 3 个重要缺陷，均为开发 Agent 自测盲区。
