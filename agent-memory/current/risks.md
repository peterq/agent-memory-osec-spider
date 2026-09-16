---
title: 当前风险与阻塞
type: risk
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-16T12:20:00+08:00
priority: high
keywords: [lifecycle_checker误删, 风险, 阻塞, 密钥, AK/SK, 生产, 测试, 依赖升级, 队列v2, 无回滚, 上线收尾]
summary: 影响开发与运维安全的已知风险点；最高 R9 lifecycle_checker 误删 115.6 万资源（修复已上线、恢复待决策）
questions:
  - 密钥、安全相关的风险在哪看
load: on-demand
related:
  - agent-memory/current/tasks.md
---

# 当前风险与阻塞

## 🟡 R9 lifecycle_checker 误判事故：115.6 万条误删，重爬已恢复 63.8 万（≈55%，其余网盘侧本就失效）；ali 尾部 ≈1.2 万排队中（2026-09-14 10:21）

- 根因 `task.Id`(md5) 误当分享 id（`b888846`）+ bnd「违规」tooltip 文案误判（`06ef50d`），均已部署到 checker；网关侧 url_check 共用 valid 包，下次发版带上。
- 已删 quark 1,115,264 / ali-share 40,007 / bnd 930；旧索引 `resource` 同步被删（v2 搜索也少这些）；`invalid_link_*` 已写入，阻止爬虫重新入库。
- 恢复只能重爬（Mongo 无数据）；方案见 `lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`、SPIDER rollout §15。
- 连带：**A' 存量复检、任何 `-trigger-check` 投递必须等修复版上线**；bnd/xunlei 8 天零有效检测，`dueBacklog` 52.8 万待消化。

## 2026-09-11 观测侧误操作致 ES 节点重启（已恢复，需防再犯）

- [事实] 子 Agent 在 legacy 索引跑 `has_child` 计数循环导致 data-i-2 重启、集群 red 27 分钟。已在 `agent-tasks/…/00-shared.md` 加入 ES 只读白名单硬约束；patterns #94。
- [推断] 任何跨父子的 ES 查询在 10 亿级索引上都可能触发；后续所有子 Agent 简报都应带该白名单。

## R7 仓库测试文件硬编码真实网盘凭据（2026-09-08 发现，2026-09-16 已在 `feat/secrets` 分支修复，未合并 master）

- [事实] `services/gateway/download_scheduler/pan_download/alipan_download/alipan_dl_test.go`、`bnd_download/bnd_dl_test.go` 直接把真实 RefreshToken/BDUSS 写在源码里（历史提交已明文入库，git 历史可查）。
- [2026-09-16 进展] secrets 角色（提案9）四仓库 `feat/secrets` 分支已修复**当前源码里**发现的全部硬编码真实凭据(共约 21 处，含 SPIDER 的 OSS AK/SK×6、bnd/alipan/quark 网盘账号凭据、生产 Redis 密码、Grafana 密码、蜻蜓代理过期 token、COMMON 的 ARMS Prometheus JWT、`tools/devops_note/esRun.mjs` 的 ES 密码)：测试统一改读本地 `*.hide.json`(配 `*.example.json` 占位模板)或环境变量，缺失时 `t.Skip`/报明确错误而非 panic；四仓库新增 `.gitleaks.toml` + `.github/workflows/secrets.yml`(只扫 PR diff) + `scripts/pre-commit-secrets.sh`。**只清了当前工作区，未改写 git 历史、未轮换任何凭据**——历史提交里这些值仍可查，轮换清单见提交里的汇报（未收敛进本记忆库，避免明文扩散；需要时找主控要那次汇报）。
- [2026-09-16 验收返工] 首轮只按字段名 grep 漏了 6 处（`ak=xxx&sk=xxx` 这种 query-string DSL 写法、`.mjs` 里的 JS 变量声明），验收方按"已知敏感值反查"（逐个 `git grep -F`）二次核验后补齐，经验见 `procedures/workflow-密钥治理约定.md`「§4 一次性排查到的、有代表性的坑」。**⚠️ 部署前置项**：`download2oss.go` 部署的 FC 函数 `resource_download_fc` 必须在**阿里云函数计算控制台**单独配置 `OSS_ACCESS_KEY_ID`/`OSS_ACCESS_KEY_SECRET`（`deploy.sh` 管不到 FC 函数这一层，容易漏配），详见 SPIDER `PRD/config-v2/README.md` §7。gitleaks 自定义规则(`[[rules]]`)跟本仓库 `.gitleaks.toml` 已有的 `[extend]` 一起用会静默失效，改用 `scripts/pre-commit-secrets.sh` 里的结构化 grep 兜底，详见同一份 procedures 文件。
- [事实,待处理] SPIDER `services/gateway/download_scheduler/download_edge_script/download.es`(CDN 边缘脚本) 与 `download_scheduler_util/res_dl_scheduler.go` 共用一个硬编码 AES 密钥/IV 做下载链接加解密，两端必须保持一致，**未处理**（改一侧会破坏线上功能，需协调发布，不是"改代码就完事"）。
- 处置建议：轮换上述真实账号/密码类凭据（`feat/secrets` 分支不做轮换）；`download.es`/`res_dl_scheduler.go` 的共享 AES key 如需下线需同时改 CDN 边缘脚本与 Go 侧并协调发布窗口。与 R2（配置文件含明文密钥）同类。

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
**这是硬性禁令**（禁止写入记忆文件/任务简报/对外输出），同条列在 `02-user-preferences.md`「已确认的硬性要求」第 10 条。
[2026-09-16 进展] `feat/secrets` 分支用 gitleaks 现状扫描确认 `config.yaml`(API)/`config_dev.yaml`(STORAGE)
里仍有明文 AK/SK，按约定**本次不改**（改了要重新分发配置+重启）；新增了可选迁移路径——四仓库
`config/` 加载代码支持把 yaml 字段整段写成 `"${VAR_NAME}"` 占位符，运行时从同名环境变量覆盖，
用法见 SPIDER `PRD/config-v2/README.md` §5/§6、API/STORAGE 各自 `README.md`。

## R3 存在直连生产环境的测试文件（2026-09-16 已在 `feat/ci` 分支缓解，未合并 master）

`services/gateway/spider_dao/spider_dao_prod_test.go` 已不存在（合并进了
`spider_dao_test.go`，`useProdDb` 硬编码 `false` + 当天日期口令兜底，默认安全）。
`ConnectProdSpiderGw`/`UseProdSpiderGw`、`UseProdDb`（同样的"当天日期口令"套路）、
`InitProdEs`、`PROD_DB` 环境变量、硬编码生产网关 IP/云凭据等，四仓库合计 20+ 个
`_test.go` 文件仍会真连生产或外网，ci 角色已排查并统一在文件第一行加 `//go:build live`，
`go test ./...` 默认不带该 tag、不会触发（清单见 `agent-memory/procedures/workflow-本地构建与验证.md`
「CI」一节，逐文件列表见 `feat/ci` 各仓库提交）。
**现状**：缓解措施在 `feat/ci` 分支，四仓库均未合并 master 前，主检出（master）上这些测试
仍无标签保护，**仍需**「只跑明确指定的测试包，不要全量跑 `go test ./...`」。
**影响**：合并前 `go test ./...` 可能真的打到生产 DB/ES/网关或联网打第三方接口。
**处理**：合并 `feat/ci` 后此风险基本消除（新增测试若引入连生产逻辑，仍需人工记得加标签，
CI 本身不会自动检测漏加标签）；合并前维持"只跑明确指定的测试包"。

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
[2026-09-16 进展] 提案10已在三仓库 `feat/deploy-rollback` 分支（`spider/api/storage-wt-deploy-rollback`
worktree）实现 releases/current 发布目录+`rollback`+部署后健康检查+多机逐台灰度，方案与用法见各仓库
`scripts/deploy.md`。中断窗口本身（`docker rm -f` 后到新容器起来之间）未消除，
新增的是"起错了/起不来能自动回滚+不再需要人工判断上一版是谁"。
[2026-09-16 12:07 进展] 新机制已随十项提案合入 master，并在 osec-jenkins/res2/res1 三机上**首次真实执行**（部署 5 个新站爬虫，未经 restest 演练，健康检查全过）；三机顶层旧 `spider`/`spider.old` 保留，存量容器仍用旧布局运行。
⚠️ 新增注意：`current` 软链是**按主机共享**的——同一台机上每次部署任何 service 都会把 `current` 切到最新发布；已运行容器不受影响，但**容器重启时会加载当时的 `current`**，因此某个 service 的 `rollback` 会连带影响同机其它用 `./current/spider` 起的容器（重启后）。多 service 同机时回滚要一起看。

## R6 STORAGE 依赖版本被 `go mod tidy` 顺带升级（新增）

见 `current/tasks.md` P1。编译通过不代表运行时行为不变，下次上线前需回归。

## R8 队列 v2 上线收尾无回滚路径

- [事实] 队列 v2 的网关与全部消费者已上线在跑，剩余收尾是**人工**动作：删 jenkins 旧容器、
  杀 2 个 2023 年的裸进程、复核、旧队列存量迁移，脚本 `osec-spider-go/scripts/queue_v2_cutover_finish.sh`。
- [风险] **这批收尾动作没有回滚路径**：删掉/杀掉的旧消费者无法原样恢复，存量迁移也不可逆。
  动手前必须确认新链路已稳定消费，并逐步执行、每步留观察窗口。
- 状态与清单以 `current/tasks.md`「队列 v2 上线收尾」为准；方案见 `decisions/decision-2026-09-04-队列v2统一走网关.md`。
