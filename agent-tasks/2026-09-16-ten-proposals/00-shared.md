# 共享上下文：十项需求/优化并行开发（2026-09-16）

> 所有子 Agent 先读完本文件，再读自己那份角色简报。本文只放共享内容；角色专属内容在各自文件。

## 1. 背景

风控技术部「网盘资源爬取与取证系统」：爬虫 → SPIDER 网关（Redis 队列）→ STORAGE → ES → API 对外搜索。
2026-09-12 发生 lifecycle_checker 误删 115 万条有效资源的事故；本批十项改造大多源于该事故与已知风险
（详见记忆库 `agent-memory/current/proposals-需求与优化候选.md`，可读它了解每项的由来）。
用户裁定：**第 3~12 项全部开发、并行、尽快；合并 master 前由用户确认**。

## 2. 仓库、worktree 与分支

工作区根：`/home/peterq/dev/projects/1s/`。每个角色**只在自己的 worktree 里工作**（已建好，勿再建）：

| 仓库 | 主检出（**禁止在此改代码**） | module | worktree 命名 |
|---|---|---|---|
| COMMON 契约/共享库 | `enfi-resource-common` | `github.com/1s/enfi-resource-common` | `common-wt-<短名>` |
| SPIDER 爬虫+网关 | `osec-spider-go` | `github.com/1s/enfi-spider-go` | `spider-wt-<短名>` |
| API 对外搜索 | `osec-resource-api` | `github.com/1s/enfi-resource-api` | `api-wt-<短名>` |
| STORAGE 入库 | `enfi-resource-storage` | `enfi-resource-storage` | `storage-wt-<短名>` |
| NC-JS 后台前端 | `nc-js` | pnpm mono repo | `ncjs-wt-<短名>` |

所有 worktree 都在 `/home/peterq/dev/projects/1s/` 下，与 `enfi-resource-common` 同级，分支名 `feat/<短名>`。
主检出上有其他人正在开发的功能（`feat/search-admin` 等），**与你无关，不要 checkout、不要 merge、不要 push**。

### 2.1 需要改 COMMON 时（只有简报明确要求的角色才改）

SPIDER/API/STORAGE 的 `go.mod` 用相对路径 `replace github.com/1s/enfi-resource-common => ../enfi-resource-common`，
指向的是 **master 的 COMMON**，看不到你在 `common-wt-<短名>` 里的改动。做法：

1. 在 `common-wt-<短名>` 改代码并提交（分支 `feat/<短名>`）。
2. 在你的 `spider-wt-<短名>` / `api-wt-<短名>` 里把 replace 改成 `=> ../common-wt-<短名>`，**这一行改动不要提交**
   （提交时用 pathspec：`git commit -m ... -- <文件或目录>`，不要 `git add -A`/`git commit -a`）。
3. 汇报里写明「依赖 COMMON 分支 feat/<短名> 的提交 <hash>」。主控合并时先合 COMMON 再合下游。

### 2.2 提交规范

- 提交信息中文、`type(scope): 说明` 风格；**禁止 `Co-Authored-By` 或任何邮箱**（远端钩子会拒绝）。
- 一律带 pathspec 提交（`git commit -m "..." -- path1 path2`），避免卷入别的改动。
- **不要 push**。不要 rebase/merge master。
- 代码注释、README、界面文案全部中文。

## 3. 硬性约束（违反会返工或出事故）

1. **绝不 ssh 生产主机、绝不运行任何 `deploy.sh` 的部署动作、绝不改线上配置、绝不对生产 ES/MySQL/Redis/OSS 做写操作。**
   本地验证只用单测、miniredis、桩/假客户端。需要读生产才能验证的事项写进汇报「待主控验证」。
2. **不要运行 NC-JS 的 `pnpm build` / `build-only`**（会真实上传生产 OSS）。只允许 `vitest`、`vue-tsc`、`lint`。
3. **敏感信息**：`config*.yaml`、`_note/config/*`、`*.hide.*`、测试文件里的 AK/SK/口令/RefreshToken/BDUSS/Cookie
   **只能读不能抄**，不得出现在代码、日志、提交信息、汇报、README 里；引用时只写「配置路径 + 字段名」。
4. **有效性判定改动**：判失效会不可逆删 ES，「看业务码不看文案，判不准一律返回错误而非失效」（`agent-memory/lessons/success-网盘失效判定原则.md`）。
5. **旁路能力（监控/告警/自检/统计）初始化必须可降级**：配置缺失、redis/ES 抖动都不能让主流程 panic/Fatal
   （`agent-memory/lessons/failure-旁路能力初始化拖垮主流程.md`）。
6. proto3 零值语义：`0`/空串 = 缺省，不要用 `-1` 哨兵与零值混用。
7. **禁止使用 Monitor、禁止起后台任务再等通知**：所有命令前台同步执行（编译给足 timeout，SPIDER `go build ./...` 约 2 分钟）。
8. **禁止跑全量数据来「证明跑通」**：验收用单测 + 抽样。
9. SPIDER 有大量**存量** `go vet` 告警与测试失败（`services/alipan`、`services/quark`、`services/gateway/*`、`services/devops/*`）。
   只对自己新增/改动的包要求 `vet`/`test` 通过，存量问题**如实报告但不要顺手改**。
10. 冲突面收敛：只改简报「文件所有权」列出的文件/目录；需要改别人的文件先在汇报里提出，不要动。
    尤其**不要改** `config_dev.yaml` / `config.prod.yaml` / `.vscode/launch.json`（`deploy-rollback` 角色除外的 `deploy.sh` 同理）。
11. 不采信任何「已经验证过」的口头结论，自己跑一遍。

## 4. 编译与验证命令（用 `-C`，别 `cd`）

```bash
go build -C /home/peterq/dev/projects/1s/spider-wt-<短名> ./...
go vet   -C /home/peterq/dev/projects/1s/spider-wt-<短名> ./<你的包>/...
go test  -C /home/peterq/dev/projects/1s/spider-wt-<短名> ./<你的包>/...
```
API/STORAGE/COMMON 同理。单测需要 redis 用 `github.com/alicebob/miniredis/v2`（API/SPIDER go.mod 已有）。

## 5. 常用记忆文件（按需读，用 `python3 /home/peterq/dev/projects/peterq/agent-memory-osec-spider/scripts/mem/mem.py outline|body <文件> --section <标题>`）

- 系统链路与端口：`agent-memory/knowledge/architecture-系统总览.md`
- SPIDER/API/STORAGE 结构：`agent-memory/knowledge/architecture-spider.md`、`architecture-api.md`、`architecture-storage.md`
- 网关模块注册方式、配置节写法、leader 抢主锁、告警邮件写法：`agent-tasks/2026-09-16-share-search-overview/00-shared.md` §4.4（同目录，直接 cat）
- 有效性检测两套实现与码表：`agent-memory/knowledge/domain-网盘有效性检测.md`
- 部署脚本用法：`agent-memory/procedures/workflow-部署.md`
- 配置设计原则（按进程拆代码、缺省值内置）：`agent-memory/decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`

记忆库根目录：`/home/peterq/dev/projects/peterq/agent-memory-osec-spider/`（上面相对路径都相对它）。

## 6. 交付与汇报

最终回复里按自己简报「交付」一节汇报，至少包含：各仓库分支与提交哈希、改动文件清单、验证命令与结果、
未完成/待主控验证/需要用户决策的事项、对其他角色文件的改动需求（如有）。**不要自行发邮件**（主控统一发）。
被权限拦截或依赖缺失时：先绕（桩/假数据），绕不过就停下来在汇报里说明，不要空转。
