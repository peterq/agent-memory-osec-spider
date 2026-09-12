---
title: 生产部署流程
type: procedure
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T22:36:00+08:00
priority: medium
keywords: [auto模式, 权限分类器, 部署, config.yaml 宿主机改配置, fail-fast, lc-check, deploy.sh, docker, ssh, OSS 配置, 主机, supervisor, 主机选型, 负载, 重启前检查, ES, 外部依赖]
summary: SPIDER deploy.sh 的常规用法、服务到主机的映射方式、判断线上现役服务的唯一判据、新服务选主机方法、配置分发机制与安全提醒；历次上线（生命周期/网关重部/代理池等）的一次性踩坑记录移至 workflow-部署-历史补充.md
questions:
  - 部署 / 上线怎么操作，日志在哪看
  - 新服务该放哪台机器
  - 队列 v2 上线收尾脚本是哪个
load: on-demand
related:
  - agent-memory/knowledge/architecture-spider.md
  - agent-memory/procedures/workflow-部署-历史补充.md
---

# 生产部署流程

主脚本：`/home/peterq/dev/projects/1s/osec-spider-go/deploy.sh`（bash，依赖 ssh 免密 + fzf/whiptail）。
STORAGE / API 各自也有 `deploy.sh`。历次上线的一次性踩坑记录（生命周期上线、网关多次重部、代理池监控上线等）
已抽到 `workflow-部署-历史补充.md`（load rarely），本文件只留常规流程与仍普遍适用的判据/提醒。

## 用法

```bash
./deploy.sh <service>            # 编译 + 部署该服务到它的所有主机
./deploy.sh deploy <service|all> # 同上（all 会逐个服务部署）
./deploy.sh ps                   # 查看所有主机上的 spider 进程
./deploy.sh storage              # 查看所有主机上的 storage 进程
./deploy.sh log     <service> [hostIdx] [cmdIdx]
./deploy.sh restart <service> [hostIdx] [cmdIdx]
./deploy.sh stop|remove <service> [hostIdx] [cmdIdx]
./deploy.sh supervisor <cmd> <host>
./deploy.sh call <函数名> [参数...]   # 直接调脚本内的函数，如 catConf / deployGrafana
./deploy.sh call redeployHost <service> <host>  # 单机补救：ssh 抖动留下"容器已删未重建"时用（2026-09-12 res2 实测）
```

- **半完成态补救不要用 `call dockerRun`**：`deployService` 路径里 `setOssConfig` 先 `export OSS_CONFIG_URL`，直接 `call dockerRun`
  跳过了这一步，容器拿到 `-e X=X` 会一直 `Restarting`；`redeployHost` 就是 setOssConfig + dockerRun。ssh 超时后先
  `ssh <host> 'sudo docker ps -a --filter name=spider-<cmd>'` 看状态再补救。

## 服务 → 命令 → 主机 的映射

在 `deploy.sh` **文件末尾**用两个关联数组维护：

```bash
serviceToCmd["gateway"]="gateway"
serviceToHosts["gateway"]="osec-res1 osec-res2"
```

- `serviceToCmd` 未设置时默认等于服务名（`setDefaultCmd`）。
- 只有 `log/restart/stop/remove` 用 `cmdIdx` 选多命令，`deploy` 只取第一个词，一个 service 只挂一个命令。
- 新增服务：在末尾追加这两行即可。

主机清单：`osec-res1`、`osec-res2`、`osec-resdb`、`osec-restest`、`osec-resngix`、`osec-jenkins`（ssh 用户 `pplabs`）。

## 如何确认线上现役服务（用户确认的唯一可靠方法）

**不要**只看 `deploy.sh` 末尾的 `serviceToHosts`——里面混有历史配置和注释掉的主机。
以进程为准：

```bash
./deploy.sh ps        # 内部调用 showSpiderProcess, ssh 到全部 6 台主机 ps 出 spider 进程
./deploy.sh storage   # 同理, 列出 storage 进程
```

`showSpiderProcess` 只做 `ssh <host> "ps -ef | grep spider"`，是只读操作，但会连生产机器。

[实测 2026-09-03] 两个方向的偏差都真实存在，所以这条规则不是保守而是必要：

- **表里有、线上没有**：`aiyoweia` / `repanso` / `yunso_net` 三个服务在 `serviceToHosts` 里挂着主机，
  线上零进程（这批爬虫代码已随 `decisions/decision-2026-09-03-清理下线爬虫代码.md` 删除，条目也已移除）。
- **线上有、代码里没有**：`osec-resdb` 跑着 `share_download_push_resolve_alipan_241226` 和
  `share_download_push_resolve_qb-250225`，这两个命令在 `spider.go` 里早已不存在，
  是老二进制没换。**这类容器一旦重新部署就起不来**，动它们之前先确认还要不要跑。
- `deploy.sh` 的 `url_clear` 指向的 `devops_clear_expire_queue` 同样在 `spider.go` 里不存在。

## 新服务怎么选主机（**别用进程数**）

```bash
ssh <host> "nproc; cat /proc/loadavg; free -g; sudo docker ps -q | wc -l"
```

**只数 `ps -ef | grep spider` 会严重低估负载**——生产机上混跑着大量非本项目的容器。
2026-09-03 就是这么把 osec-restest 压到 sshd 失联 20 分钟的，
详见 `archive/2026/failure-按进程数分配主机压垮restest.md`。

实测基线（2026-09-03，全部 2 核）：

| 主机 | 负载(1/5/15) | 内存 | 容器总数 | spider | 结论 |
|---|---|---|---|---|---|
| osec-res1 | 2.27/1.08/0.70 | 3G | 21 | 12 | 健康，有余量 |
| osec-res2 | 0.71/1.00/1.03 | 3G | 19 | 12 | 健康，有余量 |
| osec-jenkins | 0.13/0.21/0.28 | 3G | 8 | 5 | **最空，首选** |
| osec-resngix | 0.46/0.40/0.31 | **1G** | 7 | 5 | 可用，内存紧 |
| osec-restest | 10.63/26.60/25.50 | **1G** | 9 | 3 | ⛔ **整机排除** |
| osec-resdb | — | — | — | — | ssh 密钥被拒，连不上 |

容器数与负载无关：res1/res2 各 12 个 spider 容器负载才 1~2，restest 只有 3 个却是全场最忙。

**一次只部一个服务**，起来后看日志 + 看主机负载，再部下一个；分批/逐台部署的具体做法见历史补充文件。

## 部署机制

1. `buildSpider`：`CGO_ENABLED=1 go build -ldflags "-linkmode external -extldflags -static" -o spider spider.go`（静态链接）
2. `deploy`：比对本地/远程 `spider` 二进制 md5，不同才 `scp -C`（压缩，避免早期裸 scp 60MB 需 25 分钟的问题）到
   `/home/pplabs/enfi-spider-go/spider`（旧的改名 `spider.old`）
3. `dockerRun`：远程 `docker rm -f spider-<cmd>`（失败重试一次仍失败即 `return 1`，避免二进制换了容器没换的静默失败）
   → `docker pull registry.cn-hangzhou.aliyuncs.com/1second/app-env-docker:ubuntu`
   → 生成 `/tmp/run.sh` 并执行，容器名 `spider-<cmd>`，`--network host`、`--user 1000:1000`、
   挂载 `/home/pplabs/enfi-spider-go:/work`、`/dev/shm`、`/mnt`，末尾自动打印 `docker inspect -f '{{.Created}}'`
   **部署后必须核对该创建时间，不能只看 Up**（`a703e22` 起脚本已加固，历次踩坑见历史补充文件）。

## 配置分发

- [已废弃 2026-09-09] ~~gateway 服务部署前会执行 `uploadConfigToOss _note/config/spider.gateway.prod.yaml …`~~ —— 现在**所有服务共用一份** `_note/config/spider.prod.yaml` → `res/spider.prod.yaml`，`deployService` 不再按命令选文件；进程级隔离在代码层（`config/<角色>`），见 `decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`
- 上传前做三方比对：本地 vs OSS 当前 vs 上次上传副本（`oss.last.<name>`），
  若 OSS 版本与上次上传不一致 → 报错退出（说明有人在外部改过），**不要强推**
- 容器通过环境变量 `OSS_CONFIG_URL` 拉配置（`setOssConfig` 拼装 endpoint/bucket/ak/sk/path）
- 依赖本机 `ossutil` 命令

## 重启/重新部署前：先验证配置里的外部依赖（2026-09-04 血泪教训）

线上进程可能几个月不重启，期间 ES/MySQL/Redis 集群更换不会暴露，一重启就 panic 且**无法回滚**
（旧二进制连的也是死地址）。部署 gateway 这类有状态服务前，在目标主机上逐项验证：

```bash
ssh osec-res1 "getent hosts <es_addr 主机名>; curl -s -m 8 -o /dev/null -w '%{http_code}\n' '<es_addr>'"
# 交叉核对: STORAGE 线上配置里的 ES 地址是可靠来源
ssh osec-res1 "grep -o 'es-cn-[a-z0-9]*\.[a-z.]*elasticsearch\.aliyuncs\.com' /home/pplabs/enfi-resource-storage/config.yaml | sort -u"
# 索引/别名是否存在(用 storage 的 endpoint, 凭据不回显)
ssh osec-res1 'url=$(grep es_endpoint /home/pplabs/enfi-resource-storage/config.yaml | head -1 | sed -E "s#.*\"(http[^\"]*)\".*#\1#"); curl -s "${url%/}/_cat/aliases?h=alias,index"'
```

`_note/config/spider.prod.yaml`（唯一的配置源；旧的 `spider.gateway.prod.yaml` 已于 2026-09-09 合并进去并留档 `.merged-20260909.bak`）在符号链接目录里、不受 git 管理且含凭据，主会话读写会被安全策略拦截，需用户手改；键路径级搬运可用 `scripts/config_v2_merge_by_service.py` 这类不打印值的脚本。
详见 `lessons/failure-网关重启暴露ES集群已更换.md`。

- **多命令条目不生效**：`deployService` 只部署 `serviceToCmd` 的第一个词，一个 service 只能挂一个命令
  （2026-09-04 已把 `v2bnd` 拆成 `v2bndInputPwd`/`v2bndLoadShare` 两条）。
- **改名后的旧容器要手动删**：`dockerRun` 只 `rm -f` 同名容器，命令改名（如 `quark_share`→`v2quarkLoadShare`）后旧容器会继续跑。

## 安全提醒

`deploy.sh`、`config_dev.yaml`、`config.prod.yaml`、`_note/config/*` 内含明文
阿里云 AK/SK、S3 凭证、ES 账号密码、MySQL 口令、Redis 密码。
**禁止**把这些值写进记忆文件、提交信息或对外输出，只引用文件路径；`set -x`/`deploy()` 打印的 trace
里可能带 `OSS_CONFIG_URL`（含 ak/sk），管道输出务必过一遍打码（`sed -E 's/(ak|sk|password|pwd)=[^&" ]*/\1=***/gi'`）。

## Agent 派发生产部署前：auto 模式分类器（2026-09-05 实测，仍是当前机制）

- Claude Code auto 权限模式有独立的分类器，会拒绝"派子 Agent 去 ssh 生产机 / 建表 / 建索引 / 跑 deploy.sh"这类动作，
  且 `permissions.allow` 白名单绕不过它、项目级 `.claude/settings.local.json` 的 `autoMode` 它不读。
- [用户确认 2026-09-05] 已在用户级 `~/.claude/settings.json` 的 `autoMode.environment/allow` 里描述本项目生产主机
  （osec-res1/res2/resdb/restest/resngix/jenkins）、阿里云 ES/PolarDB/OSS 为受信内部环境并允许部署类操作；
  配置后部署子 Agent 可正常派出。破坏性操作（rm -rf、force push、删索引）仍会被拦，属预期。
- 若再次被拦：先确认该配置仍在，再考虑缩小任务范围重派；不要用绕过手段。
</content>

## 代码位置

- `osec-spider-go/scripts/queue_v2_cutover_finish.sh`（队列 v2 上线收尾，文档同名 .md）
