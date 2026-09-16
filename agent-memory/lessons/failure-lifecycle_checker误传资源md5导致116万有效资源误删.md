---
title: 失败经验：lifecycle_checker 把资源 md5 当分享 id，116 万有效资源被误判失效并从新旧索引删除
type: lesson
status: active
created_at: 2026-09-12T22:40:00+08:00
updated_at: 2026-09-16T14:35:00+08:00
priority: critical
keywords: [lifecycle_checker, 误删, dry run, ShareId, 违规tooltip, bnd判定, invalid_link, 失效率告警, 事故, 恢复]
questions:
  - lifecycle_checker 为什么把夸克资源全判失效
  - 116 万条资源误删是怎么回事，怎么恢复
summary: checker 用 task.Id(md5) 而非 ShareId 探测致 115.5 万条 quark/ali 误删，bnd 又因「违规」tooltip 误判 930 条；修复已上线，恢复只能重爬
load: on-demand
related:
  - agent-memory/procedures/checklist-不可逆操作上线.md  # 事故后定下的上线硬规则
  - agent-memory/current/risks.md
  - agent-memory/current/tasks.md
  - agent-memory/lessons/success-网盘失效判定原则.md
  - agent-memory/lessons/failure-旁路能力初始化拖垮主流程.md
---

# 失败经验：lifecycle_checker 误传资源 md5

正本（含取证命令与数字）：SPIDER `PRD/res-lifecycle/rollout-2026-09-05.md` §15。

## 问题背景
资源生命周期改造的独立探测进程 `lifecycle_checker`（`osec-jenkins`，SPIDER `718f160` 09-04 新增）自 09-05 14:43 起消费 `lcCheck:*` 队列。
09-12 22:17 推进 P5 A' 时发现 `lc-check` 总览 `valid1h=0 / invalid1h=14217 / base7d=1.0`——**7 天里没有一条判有效**。

## 失败表现
- 代理池监控 `lifecycle_checker_quark` ok=0、httpErr 78%，而同池同站 `quark` 场景成功率 73~88%（09-10 首批数据就有此现象，当时归因"失效响应被记成 httpError"而搁置）。
- 容器统计：quark `valid=0 invalid=416454`、ali-share `valid=0 invalid=14756`、bnd/xunlei 全部 error（未知响应）。
- `res_lc_event` `invalid`+`检测判定失效`：**quark 1,115,264 + ali-share 40,007 = 1,155,271**（每天 ≈16 万）；抽样 40/40 已从 `resource` 与 `res_lc_all` 删除、DB status=2。

## 根本原因
`services/lifecycle_checker/checker.go` `HandleTask` 调 `ValidShareId(ctx, typ, task.Id, task.Pwd)`；`CheckTask.Id` 是资源 md5，分享 id 在 `task.ShareId`。
夸克/阿里接口收到 md5 回「分享不存在」（已知失效业务码）→ Invalid → `onCheckInvalid` → `lcClear`：删 lc 文档、写 `invalid_link_<type>`（阻止再入库）、推旧 `clearExpire` **直接删旧索引（无复核）**。
单测 fake 按 shareId 取结果但用例只填 `Id`，两字段同值 → 等价于没测。
「失效率突增」告警是相对 7 天基线的倍数，基线从第一天起就是 100% → 永远不触发。

## 规避方法（已落地 SPIDER `b888846`）
- `HandleTask` 改传 `task.ShareId`；ShareId 为空拒绝探测、按 Error 上报（绝不落 Invalid）。
- 单测里 `Id`/`ShareId` 故意不同值；新增空 shareId 用例。
- 文案匹配整页是第二个坑：判定必须先看业务码/状态码，文案只在业务码非 0 时兜底，且用真实页面片段做单测。
- 网关告警新增 `invalid_ratio_absolute`（缺省 0.5，不看基线，样本 ≥500 即告警）。

## 下次行动建议
1. 任何「判失效 → 不可逆删」的探测器**上线首日看 valid/invalid 绝对数**，valid=0 直接停。
2. 契约里语义不同的同类型字段（Id/ShareId、resId/shareId），单测必须给不同值，fake 用"错的那个"做键。
3. 监控里某场景 100% 失败而同站其它场景正常 → 立即查调用方请求构造，不要归因到目标站/代理池。
4. **[用户确认 09-13] 硬规则**：此类功能上线前必须线上 dry run，再用 CDP/查库等与新功能无关的手段抽样复核，通过才正式开启 → `procedures/checklist-不可逆操作上线.md`。
5. 恢复路径（[用户确认 09-12] Mongo 无数据、ES 唯一数据源 → **只能重爬**）：`res_lc_event` 取 res_id → 分表取 share_id/pwd → 按限速投递 `resourcePreCheck`（`CommitResLink`）→ `*LoadShare` 解析 → `SaveResource` 写新旧索引，lc 上报把 status=2 行复活（rpc_service.go 703）；真失效的由解析器 `SubmitValid(0)`。`invalid_link_*` 只写不读，不拦截。

## 补记：第二个误判源（09-12 23:06，修复版上线 2 分钟发现）
bnd checker 正则 `(不存在|违规|链接已过期)` 匹配整页，而正常分享页模板固定带 `部分文件违规，已被过滤` tooltip → 有效分享判失效，2 分钟 930 条。
API 侧 `bnd-api.go` 早已特判「部分文件违规」，SPIDER 没同步。修复 SPIDER `06ef50d`：`classifyBndShare` 看 `"errno":0`/HTTP 404/提取码页，文案只在 errno≠0 时兜底。
**处置状态**：23:05 止血、23:06 部署 `b888846`、23:08 再停、23:10:53 部署 `06ef50d`（用户授权执行）。

## 补记：恢复执行（09-12 23:34 起）
`tools/lc-recrawl`（SPIDER `240a71a`）+ `scripts/lc_false_invalid_export.sh`（`a81c351`）：导出 1,152,617 条 → `-rate 10` 投递 `resourcePreCheck`。
试点 1,000 条 25 min 内 498 条复活，其余为解析器判真失效（41031/41004/41012/41011）→ 恢复率约 50%，即误删集合里约一半在网盘侧本就已死。
解析器判失效部分抽 1,000 条用 FC 云端 Chrome（`tools/quark-cdp-verify`）实测：1,000/1,000 一致，业务码逐条相同。
**直连 `drive.quark.cn` 从服务器 IP 探测一律回 14020 "file not found"（含已知有效分享），不能当判据；核验要走解析链路（代理池）。**

## 终态（09-14 10:21）
1,152,617 条 32 h 投完；回库 637,886（quark 56.2%）；bnd 以新 md5 行复活（规范化链接不同）；ali 受解析器吞吐（2×20 并发 ≈1,500/h）与预检阻塞式背压（`preCheckBackpressureThreshold=2000`，ali 任务在队头拖慢全队列）限制，尾部 ≈8 h。下次大批量重爬：**按类型分文件、ali 单独限速**（≤0.3/s），避免把预检队列堵住。

## 适用边界
lc checker 与 API/SPIDER 两套旧判定实现无关（旧链路传的是分享 id，未受影响）；bnd/xunlei 零误删但 8 天零有效检测，dueBacklog 需在修复上线后消化。
