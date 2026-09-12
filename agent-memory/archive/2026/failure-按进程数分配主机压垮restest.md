---
title: 失败经验：按 spider 进程数分配部署主机，压垮了 osec-restest
type: lesson
status: archived
created_at: 2026-09-03T17:15:00+08:00
updated_at: 2026-09-12T22:36:00+08:00
priority: high
keywords: [部署, 主机分配, 负载, osec-restest, sshd失联, deploy.sh, 进程数, 内存]
summary: 只数 spider 进程会严重低估主机真实负载——restest 还跑着 6 个非 spider 容器且内存只有 1G
load: rarely
related:
  - agent-memory/procedures/workflow-部署.md
  - agent-memory/knowledge/domain-站点-2609接入批次.md
---

# 失败经验：按进程数分配主机，把 osec-restest 压到 sshd 失联

## 问题背景

2026-09-03 上线 2609 批次的 5 个爬虫，需要决定每个部署到哪台主机。
采用的方法是 `./deploy.sh ps`（内部 `ssh <host> "ps -ef | grep spider"`）数各机的 spider 进程数，
挑进程少的机器均衡填充。

## 失败方法

按 spider 进程数得到的"负载画像"：

| 主机 | spider 进程数 | 当时的判断 |
|---|---|---|
| osec-res1 | 12 | 饱和，不加 |
| osec-res2 | 12 | 饱和，不加 |
| osec-jenkins | 4 | 空，加 1 |
| osec-resngix | 3 | 空，加 2 |
| **osec-restest** | **3** | **最空，加 2** ← 错 |

于是把 `bbs_fuxipan`(30.75 万条、4 req/s、308 个 sitemap) 和
`bbs_feikuai`(25.7 万 id 枚举、并发 8) 都放到了 osec-restest。

## 失败表现

部署完成、容器正常启动后几分钟，osec-restest 的 **ssh 完全失去响应约 20 分钟**：

```
Connection timed out during banner exchange
```

TCP 22 能连上但 sshd 完不成握手 —— 主机活着、网络通，是**资源耗尽**。
期间无法登录、无法停容器，只能起后台任务反复重连等它自己缓过来。
17:04 恢复时 `uptime` 显示 **load average: 21.84, 30.98, 26.76**（2 核机器）。

## 根本原因

`ps -ef | grep spider` **只看得见 spider 进程，看不见这台机器的其他负载**。
停掉两个爬虫后再登上去看，真相是：

```
# osec-restest 的 docker ps —— 9 个容器，只有 3 个是 spider
spider-ad_share, spider-xunlei_share, spider-devops_check_and_push_clear_queue  ← 数到的
nc-app-worker-mud-driver, osec-gardener-be, mosquitto,
agbiz-net-relay, osec-nerve-center-mud-runner, dy-dy-share                      ← 完全没数到
```

而且 **osec-restest 的内存只有 1G，其他机器都是 3G**。
停掉我加的两个爬虫之后，该机 15 分钟负载仍有 25、线程数 1045（其他机器 330~689）——
**它在我部署之前就已经严重超载**，我的两个爬虫只是压垮 sshd 的最后一根稻草。

## 正确做法

分配部署主机要看**实测 CPU 负载与内存**，不要看进程数：

```bash
ssh <host> "nproc; cat /proc/loadavg; free -g; sudo docker ps -q | wc -l"
```

2026-09-03 实测基线（全部 2 核）：

| 主机 | 负载(1/5/15) | 内存 | 容器总数 | spider |
|---|---|---|---|---|
| osec-res1 | 2.27 / 1.08 / 0.70 | 3G | 21 | 12 |
| osec-res2 | 0.71 / 1.00 / 1.03 | 3G | 19 | 12 |
| osec-jenkins | 0.13 / 0.21 / 0.28 | 3G | 8 | 5 |
| osec-resngix | 0.46 / 0.40 / 0.31 | **1G** | 7 | 5 |
| osec-restest | 10.63 / 26.60 / 25.50 | **1G** | 9 | 3 |

**反直觉但重要**：res1/res2 各跑 12 个 spider 容器，负载却只有 1~2，完全健康；
restest 只跑 3 个 spider 容器却是全场最忙的。**容器数与负载无关**。

结论：
- **osec-restest 应整机排除**，不要往上放任何新服务。
- osec-resngix 内存只有 1G，可以放但要留意内存型任务。
- osec-jenkins 最空（负载 0.13、3G 内存），是新服务的首选。

## 下次行动建议

1. 部署前一律先跑上面那条 `nproc; loadavg; free -g; docker ps -q | wc -l`。
2. **一次只部一个服务，起来后看日志 + 看主机负载，再部下一个**。
   本次两个一起放，出问题时无法区分是哪个压垮的。
3. 容器都带 `--restart always`，**主机重启不会让它们停下**。
   万一压垮主机且 ssh 不通，重启机器无济于事，必须从云控制台处理——
   所以宁可保守分配，也不要赌。
4. 部署后如果 ssh 失联，先起一个后台重连循环，连上的瞬间立刻 `docker stop`，
   不要人工反复试。

## 适用边界

适用于本项目所有 `deploy.sh` 部署决策。
特别注意：生产机上混跑着大量**非本项目**的容器（`nc-app-worker`、`osec-gardener-be`、
`agbiz-net-relay` 等），本项目的视角天然是不完整的。
