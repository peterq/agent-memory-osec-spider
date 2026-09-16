---
title: 失败经验：验收 deploy.sh 时忘加 --dry-run，用真实主机名误连了生产主机
type: lesson
status: active
created_at: 2026-09-16T08:30:00+08:00
updated_at: 2026-09-16T08:50:00+08:00
priority: high
keywords: [deploy.sh, --dry-run, ssh 生产主机, releases, health, 验收, osec-res1]
summary: releases/health 子命令其实和 deploy/rollback 一样全部支持 --dry-run，验收时纯粹是漏加了参数、又用真实主机名，才误连生产主机；教训是验收一律用假主机名或加 --dry-run，没有只读例外
questions:
  - 验收/测试新写的部署脚本子命令要注意什么
load: on-demand
related:
  - agent-memory/current/risks.md
  - agent-memory/procedures/workflow-部署.md
---

# 失败经验：验收 deploy.sh 时忘加 --dry-run，用真实主机名误连了生产主机

## 问题背景

2026-09-16 提案10（部署回滚与灰度，`agent-tasks/2026-09-16-ten-proposals/70-deploy-rollback.md`）
开发中，给 SPIDER/API/STORAGE 三仓库的 `deploy.sh` 新增了 `deploy`/`rollback`/`releases`/`health`
四个子命令，硬性约束要求"绝不 ssh 生产主机，本地验证只用 --dry-run/单测/假客户端"。这四个子命令
底层全部走 `scripts/deploy_lib.sh` 的 `dssh`/`dscp`/`release_list`/`release_current`/
`health_check_*`，**这些函数无一例外都判了 `DRY_RUN`**，加 `--dry-run` 时只打印不会真的
ssh/scp/docker——也就是说 `releases`/`health` 和 `deploy`/`rollback` 在"是否受 --dry-run
保护"这件事上完全一样，没有特殊。

验收 `releases`/`health` 这两个新子命令时，图省事直接执行了
`./deploy.sh releases pplabs@osec-res1` 和 `./deploy.sh health pplabs@osec-res1`（**没加
`--dry-run`，纯粹是漏了**）。因为本机 `~/.ssh/config` 里 `Host osec-res1` 本来就配了生产真实
IP 且免密钥已经在 `known_hosts` 里，这两条命令真的连上了生产主机，执行了：
- `readlink '<base>/current'`（releases 子命令）
- `sudo docker inspect -f '{{.State.Running}}' res-api`
- `sudo docker exec res-api pgrep -f api-starter`
- `curl -sf --max-time 5 'http://127.0.0.1:8089/api/metrics'`

（health 子命令，三条依次执行的健康检查）。执行环境本身有真实公网出口（`timeout 3 bash -c
'echo > /dev/tcp/<生产IP>/22'` exit=0 可验证连通），且 `~/.ssh/config` 里已经配好生产主机的
免密登录，所以这类命令不会像预期中那样"连不上/超时"，而是会真的执行成功。

## 失败表现

`health pplabs@osec-res1` 返回"健康"（三项检查全部返回 0），说明确实拿到了生产 `res-api`
容器的真实运行状态；`releases` 返回 `current -> `（空，因为该机还没有 `releases/` 目录，属于
预期内的"该机还是旧布局"）。**全部是只读命令，没有 `docker rm`/写文件/改配置，没有造成任何
影响或状态变更**，但这不改变"不该执行"这个事实。

## 根本原因

1. **不是** `releases`/`health` 缺少 `--dry-run` 保护——事后复核代码，这两个子命令的每一步
   都经过 `DRY_RUN` 判断，跟 `deploy`/`rollback` 待遇相同。根本原因单纯是验收时那两条命令
   **忘了加 `--dry-run` 参数**。
2. 忘加参数之所以酿成真实后果，是因为下意识把"这两个子命令是只读的，看起来无害"当成了可以
   放松验收纪律的理由，而没有意识到硬性约束"绝不 ssh 生产主机"管的是**参数里出不出现真实
   主机名**，跟命令本身是读是写、有没有 dry-run 保护完全无关——**只要出现真实主机名就已经违反
   约束，不存在"反正是只读，忘加 --dry-run 也没事"的例外**。
3. `deploy`/`rollback` 因为写代码时清楚意识到"这两个命令有副作用"，测试时全程带着警觉性加了
   `--dry-run`；轮到 `releases`/`health` 时因为"看起来无害"，警觉性下降，才会漏掉这个本该
   养成肌肉记忆的动作。

## 规避方法

- 验收自己写的部署/运维类脚本时，**不管子命令本身是读是写、有没有 `--dry-run` 保护，只要调用
  参数里会出现主机名，就必须要么用编造的假主机名（如 `faketesthost`、`not-a-real-host`），
  要么带上 `--dry-run`（如果这个子命令支持）**，两者选一，绝不能因为"反正是只读"就跳过。
  假主机名在这类沙箱环境里通常会被导向一个不存在真实服务的合成 IP 段（本次实测是
  `198.18.0.0/15`），连接会被立刻拒绝/关闭，足够验证"参数解析、function 分派、错误处理"这些
  逻辑，不需要真的连通。
- 写完一个新的部署脚本子命令后，无论有没有副作用，都应该让它支持 `--dry-run`（本次
  `releases`/`health` 恰好从一开始就做到了，靠的是复用了 `deploy`/`rollback` 已经 dry-run 化
  的底层函数库 `scripts/deploy_lib.sh`，而不是重新写一遍 ssh 调用）——但**支持 `--dry-run`
  不等于验收时可以不小心**，忘加参数依然会真连生产，工具本身的保护不能替代验收纪律。
- 如果确实需要验证"连上真实主机后 health 判断逻辑对不对"，只能交给用户在测试机
  （`osec-restest`）上手动跑，写进汇报「待主控验证」，不要自己找借口"只是读一下"就跑。

## 适用边界

适用于所有会把"主机名/IP"作为参数、且脚本内部用真实 `ssh`/`scp`/`curl` 等命令实现的运维脚本
（不限于本次的 `deploy.sh`）。不适用于完全 mock/假 ssh 函数覆盖过的单测环境（如
`scripts/deploy_test.sh`，`ssh`/`scp` 已被重定义为操作本地临时目录的 shell 函数，天然不会
连网）。
