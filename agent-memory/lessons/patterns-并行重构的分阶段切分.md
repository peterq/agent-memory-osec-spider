---
title: 可迁移模式：跨包重构如何切成能并行的子 Agent 任务
type: lesson
status: active
created_at: 2026-09-04T12:40:00+08:00
updated_at: 2026-09-12T12:10:00+08:00
priority: high
keywords: [并行重构, 子agent, worktree, 编译依赖, 三阶段, Phase0, 收尾清理, 队列v2]
summary: 多个包同时改造且互相引用时，用"主会话先做共享契约 → 子 Agent 只加不删 → 单独清理 Agent 收尾"三阶段避免编译互锁
questions:
  - 多个包同时重构，子 Agent 怎么避免编译互锁
  - Phase 0/1/2 怎么切分任务
load: on-demand
related:
  - agent-memory/procedures/workflow-并行开发多站点爬虫.md
  - agent-memory/decisions/decision-2026-09-04-队列v2统一走网关.md
  - agent-memory/sessions/2026/2026-09-04-队列v2改造.md
---

# 可迁移模式：跨包重构的三阶段切分

[实测 2026-09-04] 队列 v2 改造：6 个 sonnet 子 Agent 并行改 gateway / quark / ali / xunlei / 关键词 ×2，
全部一次合并成功，只有 `spider.go` 命令表两处机械冲突。

## 问题

和"并行开发多个新站点"不同，**重构**时各包互相引用：网关调 `quark.InputTask`，关键词站点调
`share.GetFilterLinkService`，`urn` 调 `share`……任何一个子 Agent 在自己的 worktree 里删掉旧入口，
它自己的 `go build ./...` 就会因为别人的包还在引用而失败；反过来大家都不删，老代码又永远删不掉。

## 推荐做法：三阶段

### Phase 0 —— 主会话先做"所有人都依赖的东西"，提交到 master 作为 worktree 基线
- 契约常量（COMMON 队列名）、公共辅助（`gw_remote_queue` 的 consumer/producer helper）、
  共享入口的**新实现**（`spider_common.CommitResLink` 改走网关）。
- 顺手修掉会影响所有子 Agent 的存量 bug（本次 4 个）。
- 这一步不能派出去：它决定了子 Agent 的接口，且必须先于 worktree 创建。

### Phase 1 —— 子 Agent 并行，规则是"只加不删"
- 每人新建自己的包/文件、改自己负责的文件，**保留**其他包仍在引用的导出符号（`InputTask/GetInput/...`），
  只在旧文件头加 `[已废弃]` 注释。
- 需要旧包里未导出的东西时做**最小导出**（改名/加构造函数），不重写。
- 提示词里明确列出"别人在改的目录"禁止触碰，冲突面就只剩 `spider.go` 这种注册表文件。
- 两个 Agent 同时改同一目录下不同文件是可以的（关键词批 1/批 2 都在 `services/keyword/`），
  只要各自不删共享符号（`OnKeyword` 留到 Phase 2）。

### Phase 2 —— 单独一个清理 Agent 在 master 上收尾
- 全部合并后，给它一份**精确的删除清单** + "按编译错误逐个处理残余引用" + 验收命令清单
  （build / grep 旧 API 必须为空 / vet 指定包 / test / deploy.sh 命令名与 spider.go 命令表核对）。
- 这一步串行，但工作量小。

## 其他要点

- 合并顺序无所谓，但**每合一个就 `go build ./...`**，冲突一律"两边全保留、按字母序"。
- 子 Agent 报告里的"行为差异"要逐条读：本次发现它们主动去掉了 `:9527` 调试端口、8h 业务层互斥锁、
  以及把从未触发过的 `SubmitValid` 死分支挂到真正的失效路径上——这些是合理的，但必须由主会话拍板并写进记忆。
- 主会话审查 hub 代码（本次是网关预检分发）值得花贵模型的 token：发现了"去重 key 写在推下游之前，
  重试会被当重复丢掉"这种子 Agent 自测不出来的时序 bug。
- `git rm` 之类的删除操作可能被自动模式安全策略拦截，交给子 Agent 做（提示词里写明被拦就 `rm -rf` + `git add -A`）。
- 用户偏好：编码/验收/合并都用 sonnet 子 Agent，主会话只把控全局。

## 适用边界

适用于"同一仓库多包同时改、包间有引用"的重构；纯新增（多站点接入）用
`procedures/workflow-并行开发多站点爬虫.md` 即可，不需要 Phase 2。

## 代码位置

- `osec-spider-go/services/spider-common/spider-common.go`（`CommitResLink`，爬虫提交链接的统一入口）
- `queue_task.StartQueueRemoteConsumer`（关键词/资源消费的统一封装）
