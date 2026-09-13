---
title: 上线清单：删除等不可逆操作功能必须先线上 dry run + 独立手段二次复核
type: procedure
status: active
created_at: 2026-09-13T13:59:00+08:00
updated_at: 2026-09-13T13:59:00+08:00
priority: critical
keywords: [不可逆操作, dry run, 二次复核, 删除, 上线清单, lifecycle_checker, 误删, CDP, 查库, 灰度]
questions:
  - 要上线一个会删数据/判失效/清理的功能，上线前必须做什么
  - dry run 的结果怎么复核，能不能用新功能自己的日志当依据
  - 什么时候才允许正式开启删除类功能
summary: "[用户确认 2026-09-13] 数据误删事故后的硬规则：任何删除/清理/判失效等无法撤销的功能，上线前必须先在线上跑 dry run，再用与新功能无关的独立手段（CDP 实测、直接查库/ES 等）复核变更清单，确认符合预期后才能正式开启"
load: on-demand
related:
  - agent-memory/lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md  # 促成本规则的事故
  - agent-memory/knowledge/domain-网盘有效性检测.md
  - agent-memory/procedures/workflow-带登录态的浏览器自动化.md
  - agent-memory/procedures/workflow-部署.md
---

# 上线清单：不可逆操作功能

**来源**：[用户确认 2026-09-13] 09-12 lifecycle_checker 误删 115.5 万条有效资源事故（Mongo 无数据、只能重爬恢复）之后，用户要求把下面流程定为硬规则。

## 适用范围

任何一旦执行就**无法撤销**的功能，包括但不限于：删除 ES/MySQL/Redis 数据、判失效后删索引、批量清理/归档/迁移、覆盖写、对外发通知。
新功能、改判定逻辑、换调用参数（如本次 Id→ShareId 这种"看起来没改删除代码"的改动）都算。

## 必做步骤（顺序不可调换）

1. **线上 dry run**：功能先以"只记录、不执行"模式在**生产环境**跑一轮（本地/测试环境跑通不算数，事故根因正是线上数据形态与预期不同）。产出一份**将要变更的对象清单**（id、判定依据、原始响应/业务码），落盘可查。
2. **独立手段二次复核**：从 dry run 清单里抽样（至少覆盖每种网盘/每种判定分支，并看 valid/invalid **绝对数**），用**与新功能完全无关**的方式验证：
   - 带登录态 CDP 浏览器实际打开分享链接看真实状态（`procedures/workflow-带登录态的浏览器自动化.md`）；
   - 直接查 MySQL / ES / 分表数据，或用旧链路的独立实现（API 侧检测）交叉比对；
   - **禁止**拿新功能自己的日志、自己的判定函数、或复用其代码的脚本来"复核"——同一份错误逻辑会自证正确。
3. **判据**：抽样结论与 dry run 清单一致、无系统性偏差（如某网盘全部 invalid、valid=0）、清单规模与预期同数量级，三条都满足才算通过。
4. **正式开启**：通过后再切执行模式；首日继续盯 valid/invalid 绝对数与绝对阈值告警（`invalid_ratio_absolute`），异常立即停。
5. **记录**：dry run 清单位置、抽样方法、复核结论写进对应任务/决策文件，方便事后追溯。

## 备注

- 09-12 事故的教训正是"修复上线 2 分钟"才由监控发现第二个误判源；若上线前有 dry run + CDP 抽样，两个误判源都能在删除前暴露。
- 经验正本：`lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`。
