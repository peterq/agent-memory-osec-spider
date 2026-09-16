---
title: 模式：一次派 9 个开发子 Agent 并行改造时，验收与集成怎么做才不翻车
type: lesson
status: active
created_at: 2026-09-16T18:30:00+08:00
updated_at: 2026-09-16T18:30:00+08:00
priority: high
keywords: [并行开发, 子agent, 验收, 集成预演, unshare, 断网测试, 假主机名, 按值反查, worktree]
questions:
  - 多个子 Agent 并行改多个仓库时怎么提前发现冲突、怎么保证测试不连生产
  - 验收 Agent 最常抓到开发 Agent 哪些漏项
summary: 9 条线 5 仓库并行改造的复盘：断网跑测试、假主机名、逐线验收、合并预演；验收抓到的典型漏项（漏传字段、按字段名盘点漏值、缺 dry-run、只迁一半）
load: on-demand
related:
  - agent-memory/procedures/workflow-并行多任务开发与合并预演.md
  - agent-memory/procedures/workflow-子agent任务简报.md
  - agent-memory/lessons/failure-验收部署脚本时误连生产主机.md
---

# 并行多角色开发的验收与集成

## 问题

用户一句「其余 10 项全部开发、并行、尽快、合并前确认」，涉及 5 个仓库、9 条开发线。风险不在写代码，而在：
子 Agent 测试时误连生产、分支间文本冲突、每条线"看起来完成了"但有系统性漏项、合并时才发现编译不过。

## 有效做法（本次验证）

1. **每条线一套跨仓库 worktree + 独立分支**，主控用 `scripts/dev/new_worktree_all.sh` 一次建齐；改 COMMON 的线在下游 worktree 里把 go.mod replace 临时指向自己的 COMMON worktree，**这行不提交**（pathspec 提交）。
2. **测试一律断网跑**：`unshare -rn bash -c 'ip link set lo up; cd <wt> && bash scripts/ci.sh'`。本机 docker 里的 redis 在新 namespace 里不可达，依赖它的用例会 skip，这是可接受代价。**不要**用「跑 `go test ./...` 看哪些连接失败」来找漏网测试——那等于真的连生产。
3. **测试命令里绝不出现真实主机名**（`osec-res1` 等 ssh config 免密直连生产），只读命令也会真连上去；用 `faketesthost` 或 `--dry-run`。
4. **每条线交付后立即派独立验收 Agent**（同为 sonnet），给它「重点核对」清单而非泛泛「验收」。本次 9 条线验收抓到 4 条需返工，都是开发 Agent 自报"全绿"的。
5. **合并预演**：所有线交付后用 `scripts/dev/integration_check.sh` 在临时集成分支按预定顺序合并、记录冲突、编译。本次 COMMON/SPIDER 零冲突，API/STORAGE 只有「各加一段」型冲突（config 结构体字段、README 小节、import 块），用「两段并存」机械解决。返工分支有新提交后只需再 merge 一次。
6. **合并前不要 amend 已经 merge 进集成分支的提交**——再 merge 时会冲突；追加新提交即可。

## 验收抓到的典型漏项（下次派单时写进简报预防）

| 漏项 | 案例 | 预防 |
|---|---|---|
| 系统性漏传字段 | 6 站迁移骨架，4 站漏传 `MinRequestInterval`，全局限速静默关闭 | 要求把「配置→引擎参数」抽成纯函数 + 逐站断言测试；简报给「必填字段核对表」 |
| 按字段名盘点漏值 | 密钥治理按 `AccessKeySecret|password:` grep，漏掉 `ak=...&sk=` 查询串与 JS 赋值写法 5 处（2 处生产代码） | 盘点后**按每个已知敏感值 `git grep -F` 反查**四仓库，计数为 0 才算完 |
| 缺演练模式 | 删除熔断器首版没有 dry-run，不满足「不可逆操作先线上观察」清单 | 凡是会拦截/删除/停机的新能力，简报直接要求 `dry_run` 开关 |
| 只迁一半 | 爬虫骨架首版只迁 2/6 站就交付 | 简报里写清「N/N 才算完成」，允许保留原实现的条件要具体 |
| 文档与代码不符 | deploy.sh 文档说 releases/health 不受 --dry-run 保护，代码其实受保护 | 验收要求「文档陈述逐条对代码」 |
| 端口/地址写死 | STORAGE metrics 端口常量 | 配置原则：缺省内置、字段可配 |

## 适用边界

- 适合「多条互相独立、只在少数公共文件（config 结构体、README、注册入口）交汇」的改造；强耦合重构仍按 `patterns-并行重构的分阶段切分.md` 三阶段做。
- 共享记忆库被多 Agent 并行写会把 `01-index.md` 撑爆；**子 Agent 只写 `agent-tasks/`，长期知识由主控收尾时统一提炼**（本次 4 个子 Agent 自行写了记忆文件，索引一度 20323 字）。
