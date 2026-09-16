---
title: 失败经验：验收 deploy.sh 的 releases/health 子命令时用真实主机名，误连了生产主机
type: lesson
status: active
created_at: 2026-09-16T08:30:00+08:00
updated_at: 2026-09-16T08:30:00+08:00
priority: high
keywords: [deploy.sh, --dry-run, ssh 生产主机, releases, health, 只读命令, osec-res1, 验收]
summary: deploy.sh 里"纯只读"的 releases/health 子命令不像 deploy/rollback 那样受 --dry-run 保护，验收时只要参数带真实主机名（哪怕忘了加 --dry-run 只是"随手看一眼"）就会真的连上生产主机执行 ssh/docker/curl；本次是提案10(部署回滚)开发中实测踩到，只读无写操作、未造成影响
questions:
  - 为什么 deploy.sh 加了 --dry-run 还是连上了生产主机
  - 验收/测试新写的部署脚本子命令要注意什么
  - releases 和 health 子命令为什么不受 --dry-run 保护
load: on-demand
related:
  - agent-memory/current/risks.md
  - agent-memory/procedures/workflow-部署.md
---

# 失败经验：验收 deploy.sh 的 releases/health 子命令时用真实主机名，误连了生产主机

## 问题背景

2026-09-16 提案10（部署回滚与灰度，`agent-tasks/2026-09-16-ten-proposals/70-deploy-rollback.md`）
开发中，给 SPIDER/API/STORAGE 三仓库的 `deploy.sh` 新增了 `deploy`/`rollback`/`releases`/`health`
四个子命令，硬性约束要求"绝不 ssh 生产主机，本地验证只用 --dry-run/单测/假客户端"。`deploy`/
`rollback` 已经做了 `--dry-run` 全局开关（所有 ssh/scp/docker 命令只 `echo`），本地验收这两个
命令全程加了 `--dry-run`，没有问题。

验收 `releases`/`health` 这两个新子命令时，图省事直接执行了
`./deploy.sh releases pplabs@osec-res1` 和 `./deploy.sh health pplabs@osec-res1`（**没加
`--dry-run`**）。因为本机 `~/.ssh/config` 里 `Host osec-res1` 本来就配了生产真实 IP 且免密钥
已经在 `known_hosts` 里，这两条命令真的连上了生产主机，执行了：
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

1. `releases`/`health` 两个子命令设计上就是"给运维事后在测试机/生产机上直接跑的只读检查工具"，
   本身没有、也不需要 `--dry-run` 保护（它们没有副作用，`--dry-run` 的意义是拦截有副作用的
   ssh/scp/docker 写操作）。这个设计对"最终交付给用户使用"是对的。
2. 但对"Agent 自己验收自己写的代码"这个场景，凡是参数里出现真实主机名，不管命令本身是读是写、
   加不加 `--dry-run`，都构成"ssh 到生产主机"，触犯硬性约束——**约束管的是"连不连"，不是
   "连上以后干了什么"**。验收时下意识把"只读=安全=可以直接跑"和"硬性约束里的绝对禁止"混为
   一谈，是本次出错的直接原因。
3. `deploy`/`rollback` 因为有真实副作用（会真的 `docker rm -f`/切软链），写代码时是带着"这个
   必须 dry-run"的警觉性去测的；`releases`/`health` 因为"看起来无害"，反而放松了警惕，绕开了
   本该有的"验收一律不碰真实主机名"这条更上位的规则。

## 规避方法

- 验收自己写的部署/运维类脚本时，**判断要不要 `--dry-run` 保护是子命令自己的事，判断能不能
  用真实主机名测是 Agent 自己必须遵守的更高优先级规则**：只要参数里会出现主机名，一律用编造的
  假主机名（如 `faketesthost`、`not-a-real-host`），不管这个子命令本身是读是写、有没有
  `--dry-run` 选项。假主机名在这类沙箱环境里通常会被导向一个不存在真实服务的合成 IP 段
  （本次实测是 `198.18.0.0/15`），连接会被立刻拒绝/关闭，足够验证"参数解析、function 分派、
  错误处理"这些逻辑，不需要真的连通。
- 写完一个新的部署脚本子命令后，先想清楚它"有没有副作用"，有副作用的必须做 `--dry-run` 保护；
  没有副作用（纯读）的**不需要**加 `--dry-run`（加了反而会让工具在生产环境下失去实际作用），
  但正因为它没有保护，验收时更要主动避开真实主机名，不能因为"反正是只读"就放松。
- 如果确实需要验证"连上真实主机后 health 判断逻辑对不对"，只能交给用户在测试机
  （`osec-restest`）上手动跑，写进汇报「待主控验证」，不要自己找借口"只是读一下"就跑。

## 适用边界

适用于所有会把"主机名/IP"作为参数、且脚本内部用真实 `ssh`/`scp`/`curl` 等命令实现的运维脚本
（不限于本次的 `deploy.sh`）。不适用于完全 mock/假 ssh 函数覆盖过的单测环境（如
`scripts/deploy_test.sh`，`ssh`/`scp` 已被重定义为操作本地临时目录的 shell 函数，天然不会
连网）。
