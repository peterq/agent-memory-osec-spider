---
title: 需求与优化候选清单（2026-09-16 提出，待用户挑选）
type: task
status: draft
created_at: 2026-09-16T10:30:00+08:00
updated_at: 2026-09-16T10:30:00+08:00
priority: medium
keywords: [需求候选, 优化提案, 取证包, 软删除, 熔断, 密钥治理, CI]
questions:
  - 项目下一步有哪些值得做的需求或优化
  - 取证证据链、软删除、删除熔断这些提案的依据是什么
summary: Agent 基于事故/风险/待办提出的 12 条候选需求与优化（取证包、软删可回滚、删除熔断、checker 统一、CI、密钥治理、部署回滚等），每条附依据与落点；用户未拍板，仅供挑选
load: on-demand
related:
  - agent-memory/current/risks.md
  - agent-memory/current/tasks.md
  - agent-memory/lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md
---

# 需求与优化候选（[推断]，未经用户确认）

依据来源：R9 误删事故、`current/risks.md` R2~R8、`current/tasks.md` 待办、4 仓库均无 CI、API/SPIDER 两套 checker、`api_v3.go` 硬编码。

## A. 取证与数据安全（最贴合项目目标）

1. **取证包**：爬取/有效性检测时把原始响应 JSON、抓取时间、来源页 URL、代理出口、可选截图打包存 OSS，`Resource.meta` 记 key。现只存元数据，追责缺证据链；也可作恢复源。
2. **软删 + 延迟物理删 + 删除审计**：所有删索引路径改 tombstone（lc 分表 `status` 即可承载），N 天后物理删；审计表记录 who/why/count，可一键回滚。R9 恢复只到 55% 的根因是无回滚源。
3. **删除熔断器**：checker/clear_expire/url_check 统一按窗口 invalid 绝对数与比例双阈值自动停机+告警（`checklist-不可逆操作上线.md` 靠人执行，要做进代码）。

## B. 稳定性与正确性

4. **有效性检测统一为一套**：下沉 COMMON 或 API 调网关 RPC；码表集中（quark 41031 两处待补；bnd/xunlei 仍文案匹配）。
5. **启动自检与依赖降级**：网关 `initEs()` 连不上 panic；API/resdb 配置指向过期 ES 集群。启动时校验集群名/别名并重试+告警，配置集中校验。
6. **账号池与站点健康告警**：转存链路账号全失效无告警空转；funletu TLS 长期失败、三个 keyword 站 0 成功。加成功率看板、失效自动出队、下线候选自动提示。
7. **队列 v2 可观测性补齐**：ListTask/队列长度 RPC、dueBacklog 指标导出到 ARMS，绝对阈值告警。

## C. 工程效率

8. **CI**：4 仓库无 CI。build+vet+安全单测；生产直连测试用 build tag 隔离（R3）；COMMON proto 生成全自动（Makefile 过期、`go_package` 仍 PPIO）。
9. **密钥治理**：R2/R7 明文 AK/SK/RefreshToken 迁 env/`.hide.json`，轮换，pre-commit 加 gitleaks。
10. **部署回滚与灰度**：`deploy.sh` 保留最近 N 版 + `rollback` 子命令；双机网关逐台+健康检查。
11. **爬虫通用骨架**：6 个 bbs_* 爬虫各自实现全量/增量/去重/限速；抽公共骨架，顺带解决「启动即全站扫描」P0。

## D. 搜索与接口

12. **搜索回归集与开关配置化**：固定 50 关键词 golden set 做回归；`api_v3.go` 匿名限期日期、forbidden 词表、canary 比例等硬编码改配置；`search_canary` 泛化为通用 feature flag。
