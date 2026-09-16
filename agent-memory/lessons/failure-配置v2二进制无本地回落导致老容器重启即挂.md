---
title: 失败经验：配置 v2 二进制无本地回落，换宿主机 spider 文件后未重部的老容器重启即 crash-loop
type: lesson
status: active
created_at: 2026-09-08T15:10:00+08:00
updated_at: 2026-09-09T11:05:00+08:00
priority: high
keywords: [配置 v2, OSS_CONFIG_URL, config.yaml, 回落, crash-loop, deploy.sh, set -e, 半完成态, url_check, dl_download]
summary: v2 二进制只认 OSS_CONFIG_URL/LOCAL_CONFIG_PATH 不读宿主机旧配置，老容器重启即挂；需本地回落
load: on-demand
related:
  - agent-memory/lessons/patterns-长周期生产巡检.md
  - agent-memory/current/tasks.md
---

# 失败经验：配置 v2 无本地回落

## 问题背景

2026-09-08 配置 v2 第二阶段分批把 27 个容器切到 OSS 统一配置，跳过了 resdb 上的服务与 url_check。终态 `./deploy.sh ps` 发现 osec-jenkins 的 `spider-devops_check_and_push_clear_queue`（url_check）crash-loop 95 次：`未指定配置来源: 生产请由 deploy.sh 注入 OSS_CONFIG_URL`。

## 根本原因（[事实]）

- v2 `config/config.go` 加载顺序只有 `OSS_CONFIG_URL` → `LOCAL_CONFIG_PATH` → panic，**没有"读宿主机 config.yaml"的回落**。
- `deploy.sh` 的 `deployService` 会先 `mv spider spider.old` 再放新二进制：**同一宿主机上所有容器共用这个文件**，未重部的老容器只是靠已打开的旧 inode 在跑，一旦 docker 重启它就用新二进制 + 无 `OSS_CONFIG_URL` 启动 → 永久 crash-loop。
- 手册 §2.7"回滚窗口内旧二进制读宿主机 config.yaml"的假设对**未重部**的容器不成立。

## 影响面

- 已挂：jenkins url_check。
- 定时炸弹（仍在跑，下次重启即挂）：res1 `share_download_download`（dl_download）、resngix/restest 的 url_check、jenkins `xunlei_share`（遗留）。
- resdb 三个容器安全（该机二进制未被替换）。

## 规避

- 切 v2 时**同机所有容器必须一次切完**（或给不切的容器也注入 `OSS_CONFIG_URL`），不能按服务粒度部分切换。
- 二进制层面建议补一个显式回落：`LOCAL_CONFIG_PATH` 缺省尝试宿主机挂载的 `config.yaml`（带 WARN），避免"文件一换全机埋雷"。
- 部署后逐台 `docker ps -a` 看 restarts，而不只看 `deploy.sh ps`（抓不到重启中的进程）。

## 连带教训

- `deploy.sh` 顶部 `set -e` + ssh 抖动 → 在 `docker rm -f` 之后中断，容器**已删未重建**（本轮 2 次）；重跑一次即恢复，但每批后必须逐个 inspect。
- res1/res2 的 `spider.old` 是网关回滚位，被后续同机批次 `mv` 覆盖前需备份（本轮备份为 `spider.hotfix-p4-rollback.bak`）。
- 启动日志明文打印带凭据的 OSS 预签名 URL 与 ali_log ak/sk，需打码（待修）。

## 处置结果（2026-09-08 15:27~15:56，[事实]）

用户放行后逐台重建，全部完成：

| 主机 | 容器 | 新容器 id | 结果 |
|---|---|---|---|
| osec-jenkins | `devops_check_and_push_clear_queue` | `90ca41386ddf` | restarts=0，正常 |
| osec-resngix | `devops_check_and_push_clear_queue` | `b4523e936113` | restarts=0，正常 |
| osec-restest | `devops_check_and_push_clear_queue` | `4c4c9128c9d4` | restarts=0，正常 |
| osec-res1 | `share_download_download` | `1dce1069317b` | restarts=0，正常 |
| osec-jenkins | `xunlei_share`（废弃） | — | `docker rm -f` 删除，不重建 |

终态：五台已切机 36 个运行中容器**全部带 `OSS_CONFIG_URL`**；osec-resdb 3 个容器未动（旧二进制 + config.yaml，正常）。

### 可复用：**单主机**部署路径（deploy.sh 没有现成的按主机部署入口）

`deployService` 会对 `serviceToHosts` 里**所有**主机部署（url_check 的列表含 resdb，不能直接
`./deploy.sh deploy url_check`）。正确做法是在一个 bash 进程里复用脚本自身的函数：

```bash
cd osec-spider-go
bash -c 'set -e; source ./deploy.sh call true >/dev/null 2>&1; \
         setOssConfig "$CONFIG_OSS_KEY"; \
         dockerRun <host> <cmd>' \
  2>&1 | sed -E 's#(OSS_CONFIG_URL=|https?://)[^[:space:]"]*#<MASKED>#g'
ssh <host> "rm -f /tmp/run.sh"   # dockerRun 下发的临时脚本含预签名 URL，用完要删
```

- `source ./deploy.sh call true` 只是让底部的 `main` 走 `call` 分支执行内建 `true`，**不触发任何部署**，
  同时把全部函数与 `serviceToCmd/serviceToHosts` 带进当前 shell。
- 跳过了 `deploy`（scp 二进制）：先用 `md5sum` 核对目标机 `/home/pplabs/enfi-spider-go/spider`
  与本地一致即可，本轮五台均为 `c405efb1…`（resdb 为旧版 `5b5c3a4d…`）。
- 也跳过 `uploadConfigToOss`：**它在"本地与 OSS 不一致"时会真的上传**，只想核对时改用
  `md5sum _note/config/spider.prod.yaml _note/config/oss.last.spider.prod.yaml`。
- 重建产物与 deploy.sh 一致（对照同机已切 v2 的 `spider-proxy` 验证）：老容器少 `-v /mnt:/mnt`、
  env 是占位的 `X`，新容器为 `OSS_CONFIG_URL`。

### 输出脱敏（重要）

`dockerRun` 内的 `set -ex` 与容器启动日志都会**明文打印**预签名 URL，`ali-log.go:49` 那行还会打印
日志服务 ak/sk。看日志一律加：

```bash
| grep -av 'ali log start' | sed -E 's#(OSS_CONFIG_URL=|https?://|oss://)[^[:space:]"]*#<MASKED>#g'
```

（本轮有一次未过滤 `ali log start` 行，凭据被打进了会话输出。二进制侧打码仍待修。）

### 判据补充

`devops_check_and_push_clear_queue` 日志里的 `valid/invalid` 是**进程启动以来的累计值**
（`atomic.AddInt64`，无重置，见 `services/devops/clear_expire/check_expire.go`）。老容器连续跑 5 天也只有
个位数，说明 `checkExpire:*` 队列基本已空（职能被 `lifecycle_checker` 取代），**新容器长时间全 0 属正常**，
判活改看：`配置加载完成, 来源: OSS 私有桶` + `redis[db1]` + 5 秒一次的循环 + `docker stats` CPU 3~6%（与老容器同量级）。

### 仍未处理的同类隐患

- res1/res2 上 3 个 2023~2024 年即已退出的历史容器（`keyword_yunso_net` / `share_download_download` /
  `keyword_repanso`）重启策略仍是 `always`：**docker daemon 一旦重启就会被拉起并 crash-loop**，建议 `docker rm`。
- res1/res2 各 1 个 2023 年遗留裸进程（`keyword_upyunso` / `keyword_funletu`），属队列 v2 收尾待办。

## 续：编译通过不等于能启动（2026-09-09 第二次部署中止）

- [事实] master `4f5f528`（config 按进程拆代码）默认构建的二进制在 `init()` 里同时以两种角色 `Get()`，启动即 panic；`deploy.sh buildSpider` 单文件构建静默产出残缺二进制（只剩 `config_show`）。`go build ./...`、单测、`check_config_isolation.sh`（只编译）全部通过。
- 教训：**部署前必须运行一次产物**（`./spider` 列命令、体积与上一版对比、目标子命令 `--help`）；重构入口/构建方式后要同步改 `deploy.sh`；门禁要包含冒烟运行。发现方式是二进制体积 24.8MB vs 60.6MB 的反常差。
