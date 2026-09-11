---
title: 生产部署流程
type: procedure
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-10T10:10:00+08:00
priority: medium
keywords: [auto模式, 权限分类器, 部署, config.yaml 宿主机改配置, fail-fast, lc-check, deploy.sh, docker, ssh, OSS 配置, 主机, supervisor, 主机选型, 负载, 重启前检查, ES, 外部依赖]
summary: SPIDER deploy.sh 的用法、服务到主机的映射方式、配置分发机制
load: on-demand
related:
  - agent-memory/knowledge/architecture-spider.md
---

# 生产部署流程

主脚本：`/home/peterq/dev/projects/1s/osec-spider-go/deploy.sh`（bash，依赖 ssh 免密 + fzf/whiptail）。
STORAGE / API 各自也有 `deploy.sh`。

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
```

## 服务 → 命令 → 主机 的映射

在 `deploy.sh` **文件末尾**用两个关联数组维护：

```bash
serviceToCmd["gateway"]="gateway"
serviceToHosts["gateway"]="osec-res1 osec-res2"
```

- `serviceToCmd` 未设置时默认等于服务名（`setDefaultCmd`）。
- ~~一个服务可以对应多个命令（空格分隔）~~ **[已废弃 2026-09-04]** 只有 `log/restart/stop/remove` 用 `cmdIdx` 选多命令，
  `deploy` 只取第一个词，所以一个 service 只挂一个命令。
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
详见 `lessons/failure-按进程数分配主机压垮restest.md`。

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

**一次只部一个服务**，起来后看日志 + 看主机负载，再部下一个。

## 部署机制

1. `buildSpider`：`CGO_ENABLED=1 go build -ldflags "-linkmode external -extldflags -static" -o spider spider.go`（静态链接）
2. `deploy`：比对本地/远程 `spider` 二进制 md5，不同才 scp 到 `/home/pplabs/enfi-spider-go/spider`（旧的改名 `spider.old`）
3. `dockerRun`：远程 `docker rm -f spider-<cmd>` → `docker pull registry.cn-hangzhou.aliyuncs.com/1second/app-env-docker:ubuntu`
   → 生成 `/tmp/run.sh` 并执行，容器名 `spider-<cmd>`，`--network host`、`--user 1000:1000`、
   挂载 `/home/pplabs/enfi-spider-go:/work`、`/dev/shm`、`/mnt`

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
**禁止**把这些值写进记忆文件、提交信息或对外输出，只引用文件路径。

## Agent 派发生产部署前：auto 模式分类器（2026-09-05 实测）

- Claude Code auto 权限模式有独立的分类器，会拒绝"派子 Agent 去 ssh 生产机 / 建表 / 建索引 / 跑 deploy.sh"这类动作，
  且 `permissions.allow` 白名单绕不过它、项目级 `.claude/settings.local.json` 的 `autoMode` 它不读。
- [用户确认 2026-09-05] 已在用户级 `~/.claude/settings.json` 的 `autoMode.environment/allow` 里描述本项目生产主机
  （osec-res1/res2/resdb/restest/resngix/jenkins）、阿里云 ES/PolarDB/OSS 为受信内部环境并允许部署类操作；
  配置后部署子 Agent 可正常派出。破坏性操作（rm -rf、force push、删索引）仍会被拦，属预期。
- 若再次被拦：先确认该配置仍在，再考虑缩小任务范围重派；不要用绕过手段。

## 2026-09-06 生命周期上线实测补充
- `scp` 到 osec-res1 只有 ~40 KB/s，60 MB 二进制要 25 分钟；**`scp -C` 压缩后 1.5 分钟**。`deploy()` 应加 `-C`。
- `dockerRun` 里 `docker rm -f` 那步 ssh 可能卡住且被 `|| true` 吞掉，表现为新容器名冲突、旧容器继续跑（服务无中断但没换版本）。
  部署后必须看 `docker inspect -f '{{.Created}}'` 的创建时间，不能只看 Up。
- 一台一台部网关时，用 `tools/queue-admin-check` 部署前后各跑一次做既有 RPC 回归，有效。
- 干净构建：主检出有用户未提交改动时，在 `./scripts/new_worktree.sh deploy/<name>` 的 worktree 里编译，用完删除。

## 2026-09-05 生命周期 P3 上线补充（STORAGE / API）

- **STORAGE / API / 爬虫的 `config.yaml` 是宿主机本地文件、不由脚本分发，各机内容可能不一致**。
  改之前：`cp -n config.yaml config.yaml.bak.<日期>`；用 `awk` 生成新文件后 `cat 新文件 > config.yaml`
  回写（保留 inode 与属主 pplabs，直接 `mv` 会把属主变 root）；再 `diff 备份 config.yaml` 确认"只多新增行"。
- **宿主机没有 python3**，yaml 合法性校验要 `scp` 回本地用 `yaml.safe_load`，校验完立刻删除本地副本（含凭据）。
- **上生产前先在本地用一份合成 config 跑一遍配置结构体的 `Resolve()`**，确认键名/缩进能被代码真正解析——
  比在生产上撞 fail-fast 便宜得多。
- **部署有 fail-fast 的版本前逐台验证外部依赖**（DNS + HTTP），别假设同服务各机配置一致：
  osec-resdb 的 `es_endpoint` 就指向已下线集群，见 `lessons/failure-resdb的ES端点指向已下线集群.md`。
- **容器 env 里的凭据不用回本地取**：新容器的 `OSS_CONFIG_URL` 直接从旧容器
  `docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' | grep ^OSS_CONFIG_URL= | cut -d= -f2-`
  取出复用，凭据不出宿主机。
- STORAGE 容器名是 `resource-storage-<cmd>`（gateway/worker），API 是 `res-api`；
  STORAGE `deploy.sh` 的 gateway 分支**只部 res2、res1 被注释**，两台都要手工部。
- `scp -C` 传 33 MB 二进制约 5~7 秒（本次网络），比 P0 的裸 `scp` 快两个数量级。
- 查网关生命周期 DB 用 `LifecycleRpc`（`tools/lc-check`，经 `ssh -N -L 18082:127.0.0.1:8082 <host>` 隧道），
  `Overview` 给三索引 + DB 行数 + 按类型统计，`QueryResource -id/-url` 给单条的 DB 元数据、ES 命中位置、
  `foundInLegacy` 与事件流 —— **不需要 MySQL 凭据**。
- 测 ES 写入速率至少取 10 分钟窗口：爬虫流量抖动很大，短窗口会读出 2.8 或 28.5 ops/s 两种完全相反的结论。

## 2026-09-05 P4 网关重部补充（第二次踩同一个坑）

- **`dockerRun` 的 `docker rm -f` 静默失败又复现了一次**：osec-res2 上那步 ssh 报
  `Connection timed out` 被 `|| true` 吞掉，接着 `docker run` 报
  `Conflict. The container name "/spider-gateway" is already in use` ——
  **二进制已经 scp 过去了，容器却还是旧的**。补救：手工
  `ssh <host> "sudo docker rm -f spider-gateway"` + `ssh <host> "bash /tmp/run.sh"`（run.sh 已在机上）。
  → 「部署后必看 `docker inspect -f '{{.Created}}'` 创建时间」这条规则今天第二次救场，别省。
- **一台一台部网关的干净做法**：在临时 worktree 里把
  `serviceToHosts["gateway"]` 临时改成单台再 `./deploy.sh gateway`，部完核验再改成另一台。
  比拆 `deploy.sh call` 逐函数调用可靠（`setOssConfig` 是靠 export 传给同一个 shell 里的 `dockerRun` 的，
  分开 `call` 会丢环境变量）。
- **worktree 里天然有 `_note`**：`_note` 是指向 `~/dev/secret/...` 的符号链接，
  `git worktree add` 出来的目录里同样可用，**不需要**从主检出复制任何配置文件（配置来自 OSS_CONFIG_URL / LOCAL_CONFIG_PATH）。
- `uploadConfigToOss` 三方比对输出 `config unchanged, skip` 就是"线上配置没动"的确证，可以直接写进报告。
- 查生产 API v2 延迟：端口是 **8083**（`api-starter`），不是 8080；8085 也回 200 但 3 ms 返回，不是查询路径。
- **`pkill -f '<模式>'` / `pgrep` 在 Bash 工具里会匹配到自己所在的 shell 命令行并把它杀掉**
  （表现为命令 exit 144、无输出）。要关隧道就先 `pgrep -af` 看清再按 pid `kill`，
  或者让模式避开自身。

## 2026-09-05 P4 第三次网关重部补充（本轮全部顺利，记录可复用做法）

- **`deploy.sh` 的两处加固已在 master（`a703e22`）并首次生产验证有效**：`deploy()` 的 `scp -C`
  （60 MB 静态二进制约 1.5 分钟）、`dockerRun()` 的 `docker rm -f` 失败重试一次仍失败即 `return 1`，
  并在末尾自动打印 `docker inspect -f '{{.Created}}'`。本轮两台都一次删成，没再出现"二进制换了容器没换"。
- **一台一台部网关**：在临时 worktree 里把 `serviceToHosts["gateway"]` 改成单台 → `./deploy.sh gateway`
  → 核验 → 改成另一台。核验清单：容器 `Created` 时间 / `RestartCount` / 5 分钟 `panic`+`fatal error` 计数 /
  `lifecycle registered into gateway rtc/grpc server` / `lc-check Overview`（`enabled` `leaderHost`）/
  `queue-admin-check` 回归 / 另一台是否出现 `become leader`（判断 leader 唯一）。
- **部署输出要过一遍打码**：`deploy()` 里的 `set -x` 会把 `OSS_CONFIG_URL`（含 ak/sk）打进 trace。
  管道加 `sed -E 's/(ak|sk|password|pwd)=[^&" ]*/\1=***/gi; s#//[^@/ ]*@#//***@#g'` 即可。
- **v2 搜索延迟抽样必须换关键词**：同一个 `kw` 打 10 次，后几次命中缓存只要 7~10 ms，均值会被拉低一半。
  用 10 个不同关键词测得 532 ms，与历史基线 533 ms 一致，才可比。
- **发邮件用 `COMMON/scripts/notify-admin.sh`（curl）**；python `urllib` 请求
  `http://cf-worker.peterq.cn/notify_admin` 会被 **403**（UA 被挡）。
- **杀后台进程一律按 pid**：`pgrep -af '<模式>'` / `ps|grep` 组成的 kill 循环会匹配到自己所在的 shell 并把它杀掉
  （exit 144）。pid 从启动时的 `$!` 或 `ss -ltnp` 取。这条规则今天又踩了一次。

## 2026-09-05 P4 第四次网关重部 + 生产 dryRun 补充

- **`go test ./services/gateway/lifecycle/` 在 worktree 里跑不起来**: `config` 包的两个 `init()`
  先要 `enfi_spider_conf` 指到一个存在的 yaml, 再要这个 yaml 里有合法的 `log_level`
  (否则 `logrus.Fatal("invalid value for -logruslvl=")`)。主检出里**没有** `config_dev.yaml`
  (代码里那个 fallback 路径是失效的)。最省事的做法: 临时写一个只有 `log_level: info` 一行的
  yaml 放 scratchpad, `enfi_spider_conf=<该文件> go test ...` 即可全绿。
  **不要**拿 `_note/config/spider.gateway.dev.yaml` 当测试配置 —— 它会把 AK/SK 打进终端。
- **`git push` 偶发 `ssh: connect to host github.com port 22: Connection timed out`**:
  纯网络抖动, `ssh -T git@github.com` 单独测是通的, 直接重试一次就成功。
  ssh config 里 github 的 ProxyCommand 是注释掉的, 不要去改它。
- **`lc-check -job <id>` 的 `progressJson` 会很长**(本次 112 KB, 含 1908 个窗口),
  终端里会被截断。取全量: `lc-check -job N | grep '^  progressJson=' | sed 's/^  progressJson=//' > x.json`
  再用 python 解析。
- **bootstrap dryRun 的窗口是分两次算的**: `progress.windows["join"]` 在 B1 开始时就有,
  `["bnd"]` 要等 db_join 扫完进入 db_bnd 才算。想拿全两套, 必须等作业跑过 db_join。
- **生产全量 dryRun 的代价**: 4434 万父文档纯 scroll 计数用了 **107.6 分钟**(≈6,870 docs/s),
  不是"几分钟"。派 dryRun 任务时按 1.5~2 小时安排, 用 `scripts/lc_bootstrap_watch.sh <id> 90 120`
  后台盯盘, 主会话每 5~10 分钟看一次 log 尾部即可。
- **`ssh osec-res1` 偶发 `Connection timed out`**(部署本身已成功): 核验命令要包一层重试循环,
  不要因为一次 ssh 抖动就判定部署失败。

## 2026-09-10 代理池监控上线：爬虫全量分批重部补充

- **只构建一次、多次部署**：`./deploy.sh deploy <svc>` 每次都 `buildSpider`；先用它部一个服务，之后用
  `./deploy.sh call deployService <svc>` 复用同一个二进制（仍会做 OSS 配置三方比对 + md5 比对 + docker 重建）。
- **主机表含 osec-resdb 的服务（`url_check`）**：resdb 跑的是 2024 年老二进制，不能重建。用 `sed` 生成去掉
  resdb 的脚本副本放 scratchpad，`bash <副本> call deployService url_check`，在仓库根目录执行即可（脚本用相对路径）。
- **ssh 瞬时超时会让 `docker rm -f` 后未重建**（脚本在 `docker pull` 阶段断掉，`set -e` 退出）：`deployService` 幂等，
  直接重跑同一命令即可，不必手工 `docker run`。
- 20 个 service / 32 容器逐个部完约 25 分钟（09:33~09:56），P4 bootstrap 无可辨识影响；restest 可用内存最低 207MB 未 OOM。
- 验证上报是否生效用 `tools/proxy-admin-check`（见 `troubleshooting-代理池总览无数据.md`），不要等前端。
