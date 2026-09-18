---
title: 决策：合并 feat/sweep-guard-a/b 时冲突不套用"两边全保留"字面规则
type: decision
status: active
created_at: 2026-09-04T15:30:00+08:00
updated_at: 2026-09-18T10:50:00+08:00
priority: medium
keywords:
  - sweep-guard
  - 全量扫描守卫
  - merge 冲突
  - keepalive
  - 保活语义
  - runRound
summary: 合并遗留分支时，master 已修正的旧逻辑不应因"冲突两边都保留"而被恢复，需先判断冲突是否为真实的两个功能重叠
load: rarely
related:
  - agent-memory/lessons/success-爬虫保活语义.md
  - agent-memory/current/tasks.md
---

# 决策：合并 feat/sweep-guard-a/b 时冲突不套用"两边全保留"字面规则

## 背景

`feat/sweep-guard-a`（kkpans/dyyjmax/kuakes）与 `feat/sweep-guard-b`（fuxipan/misoso）
是"bbs 爬虫启动不再触发全站扫描"的落地代码，基于较老的 master 分叉。用户要求合并时
"冲突一律两边全保留、按字母序，绝不丢弃任一方逻辑"。

## 要解决的问题

`feat/sweep-guard-a` 合并时，`kkpan.com.go`/`bbs.dyyjmax.org.go`/`kuakes.com.go` 三个文件
在 `runRound()` 末尾都产生冲突：分支分叉时的旧 master 在 `p.onRoundSuccess(mode)` 后紧跟
`p.alive()`；但当前 master 在此期间已经落地
[用户确认 2026-09-03] 的保活语义决策（见 `lessons/success-爬虫保活语义.md`）——
把 `p.alive()` 从"轮次成功就续期"改成"只在 `handleItem` 里 `CommitResLink` 真正提交
成功时续期"，并把旧的 `runRound()` 末尾调用删掉了。

如果机械套用"两边全保留"，就会把已删除的 `p.alive()` 重新加回 `runRound()` 末尾，
导致每个"轮次成功但零新增"（站点长期只返回老链接、全部被去重）的轮次也会续期保活，
**原地复活用户前一天刚确认修复的 bug**。

## 备选方案

### 方案 A：字面执行"两边全保留"

优点：机械、不需要额外判断，严格听指令。

缺点：会在 3 个文件里重新引入已被验证为错误的保活语义，且这不是"两个独立功能的
真实冲突"——只是分支基于旧代码、恰好在同一行文本产生 diff 冲突，语义上根本不对等。

### 方案 B：识别"文本冲突"与"语义冲突"的区别，只保留双方各自的真实新增逻辑

优点：master 一侧的改动是"删除旧逻辑 + 无新增"（纯粹的 bug 修正），分支一侧的改动是
"新增 4 个全量守卫函数 + 把 `runRound` 返回值从 void 改成 error"。二者本来就不冲突，
之所以在 diff 上重叠只是因为都改了同一段代码附近。保留 master 对 `p.alive()` 位置的
修正，同时把分支新增的守卫函数与返回值改动完整保留，双方"实际功能"都没有丢。

缺点：需要额外判断，不是无脑操作；如果判断错误，可能真的丢掉一方逻辑。

## 最终决策

采用方案 B：3 处冲突都不恢复 `runRound()` 末尾的 `p.alive()`，改为在原位置留注释
说明原因并指向 `lessons/success-爬虫保活语义.md`；同时完整保留 `fullSweepLastDoneKey`/
`getFullSweepLastDone`/`setFullSweepLastDone`/`fullSweepStartupSkip` 四个新函数、
`runRound` 返回 `error` 的改动及其调用点。

## 决策原因

- "两边全保留"这条指令的意图是"不要在合并遗留分支时，把用户已经确认的功能悄悄
  丢掉"，而不是"machine 冲突标记出现的每一行文本都要出现在结果里"。
- 保留 `p.alive()` 不是保留了 `feat/sweep-guard-a` 的"逻辑"——那只是它分叉时继承的
  旧代码，不是这个分支要新增的功能；这个分支真正要新增的是全量扫描守卫，与
  `p.alive()` 位置无关，两者可以同时成立且互不影响。
- agent-memory 里有明确的 `[用户确认 2026-09-03]` 记录可交叉验证，不是凭空猜测。

## 影响

- `kkpan.com.go`/`bbs.dyyjmax.org.go`/`kuakes.com.go` 三个文件的 `runRound()`
  末尾都留有解释性注释，指向保活语义决策，避免后续 Agent 看到"少了一行 `p.alive()`"
  又想当然加回去。
- `feat/sweep-guard-b` 合并时三个文件（含 `feikuai.tv.go`）均无冲突，自动合并，
  未触发此问题（因为 master 在这几处的相应位置本来就已经是"只在 handleItem 里
  alive()"的最终状态，分支没有再动这行）。

## 复盘条件

以后再遇到"合并遗留分支，用户要求冲突两边全保留"时：先判断冲突是"master 删除了
分支继承的旧代码"还是"master 与分支各自新增了不同东西"；前者应优先看 master 侧
改动是否有 agent-memory 决策/lesson 支撑，有则遵循 master、不逆向恢复旧逻辑，
并在报告里明确说明这一处偏离了"字面两边全保留"、给出依据，让用户可以否决。

## 当前状态

已执行，master 已合并两个分支并通过 `go build/vet/test` 验收，未 push。
