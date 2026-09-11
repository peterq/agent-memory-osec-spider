---
title: 当前风险与阻塞
type: risk
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-11T17:50:00+08:00
priority: high
keywords: [风险, 阻塞, 密钥, 生产, 测试, 依赖升级]
summary: 影响开发与运维安全的已知风险点
load: on-demand
related:
  - agent-memory/current/tasks.md
---

# 当前风险与阻塞

## 2026-09-11 观测侧误操作致 ES 节点重启（已恢复，需防再犯）

- [事实] 子 Agent 在 legacy 索引跑 `has_child` 计数循环导致 data-i-2 重启、集群 red 27 分钟。已在 `agent-tasks/…/00-shared.md` 加入 ES 只读白名单硬约束；patterns #94。
- [推断] 任何跨父子的 ES 查询在 10 亿级索引上都可能触发；后续所有子 Agent 简报都应带该白名单。

## R7 仓库测试文件硬编码真实网盘凭据（2026-09-08 发现）

- [事实] `services/gateway/download_scheduler/pan_download/alipan_download/alipan_dl_test.go`、`bnd_download/bnd_dl_test.go` 直接把真实 RefreshToken/BDUSS 写在源码里（历史提交已明文入库，git 历史可查）。
- 处置建议：轮换这些账号凭据；测试改读 `.hide.json`（gitignore，参照 `bndAccounts.hide.json` 模式）。与 R2（配置文件含明文密钥）同类。

## 🔴 R6 repair 定时作业与 bootstrap 无互斥，会误标未复制行（2026-09-06 现场发生）

- [事实] `repair.go` 每天 04:00 排队 `repair`，`repairDbToEs` 把 DB 有 ES 无的 status=1 行 `MarkDeleted`；bootstrap 建库先于复制完成，中间态行会被批量误标。09-06 07:22 id=8 被 pause 后 id=9 立刻开跑，≈3,000 行/分钟。
- [事实] `jobRunner.runJob` 同步执行、`pollOnce` 串行：一个作业在跑会独占调度循环，其它 running/pending 作业不推进（id=8 resume 后未动）。
- [事实] auto 模式分类器会拦 `lc-check -control-job <id> -action pause`（部署类 autoMode 放行不覆盖它）。[用户确认 2026-09-06] 已在 COMMON 项目级 `.claude/settings.json` `permissions.allow` 加 `Bash(go run ./tools/*)`/`Bash(ssh -N -L *)`/`Bash(./deploy.sh *)`，实测 `go run ./tools/lc-check … -control-job 9 -action pause` 不再被拦（命令必须以该前缀开头，cwd 在 SPIDER）。修正此前"permissions.allow 绕不过分类器"的结论：**精确前缀的 allow 规则有效**，之前无效是因为规则未覆盖到具体命令。
- 规避：全量 bootstrap 期间不要让任何非 bootstrap 作业运行（pause 前先看 `lc-check -jobs` 的 activeJob/pending 列表）；治本改 `repairDbToEs` 加 bootstrap 互斥；巡检开局必须看 activeJob 列表而非只盯目标作业。

## ~~R1 三个仓库无法本地编译~~（已解决 2026-09-02）

`PPIO → 1s` 重命名收尾后，四个仓库 `go build ./...` 全部通过。保留条目以便回溯。

## R2 配置文件含明文密钥

`config_dev.yaml` / `config.prod.yaml` / `deploy.sh` / `_note/config/*` 中有阿里云 AK/SK、
AWS S3 凭证、Elasticsearch 账号密码、MySQL/Redis 口令，且已进版本库。
**影响**：任何粘贴、日志输出、记忆写入都可能扩散泄露。
**处理**：只引用路径不引用值；如需展示配置结构，手工脱敏。

## R3 存在直连生产环境的测试文件

如 SPIDER `services/gateway/spider_dao/spider_dao_prod_test.go`。
另外 `devops_utils.ConnectProdSpiderGw()` 有个"当天日期口令"保护
（`UseProdSpiderGw` 必须等于 `time.Now().Format("0102")`，否则 panic）。
**影响**：`go test ./...` 可能真的打到生产 DB/ES。
**处理**：只跑明确指定的测试包，不要全量跑。

## R4 一次性运维脚本积累

SPIDER `services/devops/` 下按时间分了 `2408/2409/2511/26/...` 多个目录，
且 `spider.go` 的命令表中挂着已完成的一次性任务（如 `share_download_push_resolve_ali_250918`）。
部分包（如 `devops_res_reindex`）根本没挂进命令表，属于半成品。
**影响**：容易误判某命令仍在使用；`deploy.sh` 里也有被注释掉的历史主机配置。
**处理**：判断某服务是否在跑，**以进程为准**——`./deploy.sh ps`（spider）/ `./deploy.sh storage`，
不要只看 `deploy.sh` 末尾的 `serviceToHosts`。详见 `procedures/workflow-部署.md`。

## R5 `deploy.sh` 无灰度、直接替换二进制

`deploy` 只比对 md5 后 scp 覆盖，`dockerRun` 先 `docker rm -f` 再起新容器，中间有服务中断窗口。
**处理**：部署前确认该服务是否可短暂中断；gateway 有两台（res1/res2），可逐台执行。

## R6 STORAGE 依赖版本被 `go mod tidy` 顺带升级（新增）

见 `current/tasks.md` P1。编译通过不代表运行时行为不变，下次上线前需回归。
