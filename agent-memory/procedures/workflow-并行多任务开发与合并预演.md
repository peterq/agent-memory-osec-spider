---
title: 工作流：多条独立改造并行开发、逐条验收、合并预演、用户确认后合并
type: procedure
status: active
created_at: 2026-09-16T18:30:00+08:00
updated_at: 2026-09-16T18:30:00+08:00
priority: high
keywords: [并行开发, worktree, 合并预演, integration_check, new_worktree_all, 验收, 合并确认]
questions:
  - 用户让我并行开发多项需求、合并前确认，标准流程是什么
  - 合并前怎么提前发现冲突并验证编译
summary: 简报落盘 → new_worktree_all 建跨仓库 worktree → 并行派单 → 逐线验收/返工 → integration_check 合并预演 + 断网 CI → 合并清单邮件等确认 → 合并 → 清理
load: on-demand
related:
  - agent-memory/lessons/patterns-并行多角色开发的验收与集成.md
  - agent-memory/procedures/workflow-子agent任务简报.md
  - agent-memory/procedures/workflow-任务进度邮件汇报.md
---

# 并行多任务开发与合并预演

脚本在记忆仓库 `scripts/dev/`（说明见同目录 README.md）。示范目录：`agent-tasks/2026-09-16-ten-proposals/`。

## 1. 准备（主控）
1. 每条线一份 `10-<短名>.md`，共享约束放 `00-shared.md`；**文件所有权**要列全（含测试、denylist、脚本产物）；会拦截/删除的能力要求 `dry_run`；量化完成标准（N/N）。
2. `scripts/dev/new_worktree_all.sh feat/<短名> <短名> common spider api storage [ncjs]`——worktree 与 COMMON 同级，SPIDER 复用其自带脚本补齐 gitignore 源码；nc-js 基线是 `main`。
3. 发「启动」邮件（`scripts/mail/notify.py -l progress`）。

## 2. 派单与验收
- 派单 prompt 只给两个文件路径；模型 sonnet；后台运行；改 COMMON 的线在汇报里给 COMMON hash。
- 每条线交付即派验收 Agent（读 00/10/90 三个文件），prompt 里列该线的「重点核对」；验收命令要求 `unshare -rn` 断网。
- 返工用 SendMessage 让原 Agent 继续（上下文还在），不要新起。
- 每条结果记进 `99-notes.md`（pathspec 提交 `-- agent-tasks`，因为记忆仓库可能有别的会话在提交）。
- 异常（误连生产、返工）立即 `-l warn` 邮件。

## 3. 合并预演
```bash
S=scripts/dev/integration_check.sh
$S common ten-proposals feat/a feat/b ...      # 先 COMMON
$S spider ten-proposals feat/a feat/c ...      # 下游 go.mod replace 自动临时指向 common-wt-<名>(以 temp 提交形式)
```
冲突分支会被 abort 并列出文件；在 `<repo>-wt-<名>` 里手工 `git merge` 该分支解决（「各加一段」型用两段并存），编译后提交。返工分支有新提交后再 merge 一次。
最后四仓库 `unshare -rn ... bash scripts/ci.sh` 全绿。

## 4. 确认与合并
1. 写 `95-merge-plan.md`：集成分支 HEAD、各线最终 hash、合并步骤、上线前置项、已知残留；`-l done` 邮件等用户确认。
2. 用户确认后：COMMON master ← 集成分支；下游先撤销 `temp(integration)` 的 go.mod 提交再合；nc-js `main` ← 分支；各仓库再跑一次 ci.sh；push 由用户决定。
3. 清理：`git merge-base --is-ancestor` 确认后删 worktree 与分支。

## 5. 记忆收尾
子 Agent 不写记忆库；主控最后统一提炼 lessons/procedures、更新总览 §2、`index --write` + `lint`。
