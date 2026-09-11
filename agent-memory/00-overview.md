---
title: 项目总览
type: overview
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T02:40:00+08:00
priority: critical
keywords:
  - 网盘资源爬取
  - 版权取证
  - COMMON
  - SPIDER
  - STORAGE
  - API
  - NC-JS
summary: 风控网盘资源取证系统的最小可用上下文：五仓库职责、数据链路、当前状态与阻塞
load: always
related:
  - agent-memory/01-index.md
  - agent-memory/03-project-context.md
  - agent-memory/knowledge/architecture-系统总览.md
---

# 项目总览

## 1. 项目身份

- 项目名称：风控技术部 —— 网盘资源爬取与取证系统
- 项目类型：Go 多仓库后端系统（爬虫 + 存储 + 查询 API + 公共库）+ 一个前端 mono repo（后台管理页 NC-JS）
- 项目目标：爬取网络上的网盘分享资源，沉淀为可检索的证据，用于后续版权侵犯追责
- 当前阶段：长期运行中的存量系统；2609 批次接入的 6 个站点爬虫
  （`bbs_kkpans` / `bbs_dyyjmax` / `bbs_fuxipan` / `bbs_feikuai` / `bbs_kuakes` / `bbs_misoso`）
  **已全部部署上线并在跑**（2026-09-03 `./deploy.sh ps` 实测）；
  第 7 个 `haisou.cc` **上线失败已下线**（站点端点级拦截 + 产出上限过低，见下）
- 项目边界：资源发现、入库、检索，以及配套的内部后台管理页；不做对外产品前端，不做法务流程
- 主要交付物：4 个 Go 服务/库仓库 + 部署脚本 + ES 索引数据

## 2. 当前状态

- **已完成（2026-09-10 上午）：代理池监控上线闭环**——「代理池总览」全 0 排查定位为上报侧未部署；`proxy` + 20 个爬虫 service 重部后 5 分钟窗口即有 20 个场景数据。新增只读巡检 `tools/proxy-admin-check`（经隧道直连网关 RPC）。→ `procedures/troubleshooting-代理池总览无数据.md`
- **已完成（2026-09-09 凌晨，SPIDER `4f5f528`→`883daeb`，**网关已于 09-09 11:53/12:04 部署生效，爬虫容器 + proxy 服务已于 09-10 09:30~09:56 全部重部**）：配置按进程拆代码（用户纠正 09-08 的误解）**——
  `config` 根包只留 section 类型 + `Common`，**删除 `config.Config`/`Get()`/`init()` 加载**；
  角色包 `config/{gateway,crawler,proxyprov,lifecyclechecker,doccrawler,devops,downloader}`
  各自惰性 `Get()`，进程内只允许一种角色；`spider.go` 拆三份带构建 tag，
  `scripts/check_config_isolation.sh` 用 `-tags gateway_only/crawler_only` 做编译期隔离检查；
  配置文件**保持一份**，`deploy.sh` 回退单文件，本地 `_note` 两份已用
  `scripts/config_v2_merge_by_service.py` 合回。hub 由主控完成，约 80 处调用点由 sonnet 子 Agent 迁移，主控独立复核后合并。
  → `decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`、`lessons/failure-把拆配置理解成拆文件.md`
- **已完成（2026-09-08 夜，五仓库已 push，未部署）：并行四任务**——
  ① **告警加入后台**（告警历史落 redis + 触发时从 SLS 抓的现场日志 + 邮件带日志片段）
  与**队列失败率告警按队列可配**，默认由 10min/50% 改为 **1h/60%**；失败率统计从
  "每次现查 SLS"改成 **redis 分钟桶**（SLS `search` 的 limit 硬夹 200，1 小时窗口必然扫不全）。
  ② **代理池监控纳入后台**：`proxy-client` 只加 hook（`RegisterHook`/`Scene`/可选
  `ClassifyResult`，不引入 redis/prometheus/config），上报逻辑全在独立包
  `illuminate/proxy-monitor`（分钟桶 + 延迟直方图 + HLL 去重），网关侧
  `services/gateway/proxy_admin` 只读聚合；29 个 `ProxyClient` 实例化点各加一行 `Scene:`。
  ③ **资源链接爬取路径追踪** `TraceResLink`：无 trace id，用分享 id 全文检索跨阶段串联，
  各阶段补 `link_key` 顶层字段；顺带补齐 bnd 消费者零日志、重复提交静默、入库结果不进 SLS
  三个长期埋点缺口。
  ④ **文档爬虫上云**：COMMON 新增独立嵌套 module `fc-chrome/`（支持按 URL 装扩展/油猴脚本、
  内置 Tampermonkey、`--headless=new`）+ SPIDER 新进程 `doc_crawler` + userscripts 云端 target。
  **云端脚本不连 gRPC/WebRTC**，只解析 + `console.log` 约定协议回传，提交与上报由 doc-crawler
  走标准 gRPC。
  提交：SPIDER `d6a4d54` / COMMON `5e5cdc1` / NC-JS `ab7753d` / API `9518bac` / userscripts `fdc884a`。
  详见 `sessions/2026/2026-09-08-并行四任务监控与文档爬虫上云.md`、
  `lessons/failure-旁路能力初始化拖垮主流程.md`、`current/tasks.md`「并行四任务」的上线待办。
- **已完成（2026-09-08）：后台登录改为 GitHub OAuth（限 1second 组织成员）**——
  三仓库已合并 push（SPIDER `41832ca` / NC-JS `5808d42` / COMMON `ac5cfc5`），**未部署**。
  核心设计：OAuth code 交换放网关 Go 侧（网关机可直连 GitHub，不需要中转）、
  prod/dev 两个 OAuth App、`client_id` 由网关握手 403 时下发（前端一份代码两套环境）、
  保留 `allow_rtc_token` 作为可关闭兜底（生产 false）。两轮真实浏览器联调（桩网关
  `tools/stubgw` + 调试 Chrome）各抓到一个阻断级问题并修复：① 握手 403 回包的
  `needLogin/githubClientId` 等字段被 RTC 传输层 `cancelAllPendingCalls` 物理丢弃，
  必须走专门回调而非 RPC 错误通道；② 登录失败原因被下一次无 code 的重试用通用
  "未登录"覆盖。**未部署待办**：用户需把含 client_secret 的配置贴进
  `_note/config/spider.prod.yaml`（Agent 不能碰）；网关部署仍受 P4 bootstrap
  阻塞（不要从 master 构建网关）；前端两个连网关的子应用需各自发布；
  **上线顺序必须"先网关后前端"**，否则新旧不匹配会导致登录/鉴权异常。
  详见 `sessions/2026/2026-09-08-后台登录改为github授权.md`、
  `decisions/decision-2026-09-08-后台登录改为github-oauth.md`、
  `lessons/failure-握手回包附加字段被传输层丢弃.md`。
- **已完成（2026-09-08）：res_lc_* 数据纳入管理后台**（用户需求"全都要 + 只读 + 并行 agent 开发"）——
  后台 lifecycle 模块新增 4 个纯只读能力：`ListResources`（分表列表，多条件筛选分页）/
  `TableStats`（分表统计看板）/ `ListEvents`（res_lc_event 流水）/ `TableDiagnostics`
  （67 表体检 + DB↔ES 对拍，只报告不执行 DDL），前端对应 4 个页面。
  Opus 验收 A~E 全过（含恶意 `orderBy` 实测白名单拦截），已合并并 push：
  COMMON `35eb8fd` / SPIDER `0b35940` / NC-JS `8aed2fd`。
  **已于 2026-09-08 随配置 v2 上线**（网关 12:01 切 master，前端 15:27 发布并 CDP 实测通过）。
  详见 `sessions/2026/2026-09-08-res_lc数据纳入后台.md`、
  `lessons/failure-proto3零值与负一哨兵冲突.md`、任务简报 `agent-tasks/2026-09-08-lifecycle-admin-data/`。
  顺带修正：8 个 proto 的 `go_package` 仍是 `github.com/PPIO/...` 老路径（重跑 `gen.sh` 会把失效
  import 写回生成代码）、前端 `protc_gen.sh` 缺 `node_modules/.bin` 的 PATH，均已修。
- 当前正在处理（2026-09-09 12:30）：
  **① P4 全量 bootstrap 作业 `id=8` 生产运行中**：09-05 23:01 启动，copy_child 进度 ≈60%（09-09 10:13，7.26 亿 / 12.0 亿）；无效重跑 06:55 后随窗口越过 2025-07 段自然消失，修复 `97541e9` 已提交，**用户决定 10:20 立即重部网关（短缺修复 + config 重构 `4f5f528` + log_store + 打码 + 其它会话功能），10:45 重新授权后 10:55 因 master `4f5f528` 默认构建启动即 panic + `deploy.sh` 单文件构建残缺**再次中止（生产零改动）**；已修（`883daeb`：惰性注册、去 build tag、deploy.sh 包构建、门禁冒烟），11:45 重开重部窗口，**12:04 双机重部完成**（res1 `93d1fb726816` 11:53 / res2 `600e1a8c2738` 12:04=leader，md5 `bdd0c722…`，回滚位 `spider.old`=`6cf6157`；12:13 resume、12:17 守护重启 pid `2967491`，中断 ≈36 分钟，0 panic、热更新参数未变）；第 19 轮（12:26~17:15）整轮在自动重跑 61 条旧 failedSlices 大窗口（记入 `shortfallSlices` 57 条、缺 2.24%），第 20 轮 17:50 越过重跑段；**09-11 05:16 作业 id=8 终结为 `failed`（verify 阶段 res_short_202609 DB/ES 差额 0.107% > 0.1%，差 2,957 条，别名未切换、线上无影响）**，copy_child 跑满 1620/1620、shortfallSlices 89；守护自行退出。**✅ 09-11 10:25:55 id=8 `done`**（用户决策 cancel id=4 → repair id=10 2h55m 修正 4,508/去重 57,414 → 复核 cur 0.0067%/long 0.0030% → retry 25 秒过；B6 自动 repair id=11 运行中）；rollout §12 完整（SPIDER `de9c08c`）；**shortfall 89 条实为 longBoundary 漂移导致父留 cur（零丢失），已于 09-12 02:17 用 mover 归位 102,601 父（终态对拍 0.001% 级，参数已复原）；`copyMode=ids` 禁用**；遗留 2 个 `:cur` 窗口 21,451 子待决策；5 个代码提交未部署；**P4 完成，下一步 P5 灰度（调用方切 v3）**；新代码使 `failedSlices` 61→0（预期）、`shortfallSlices` 开始计数；**第 19 轮巡检（12:30 起）由新会话主控派 Opus 接管，简报 `agent-tasks/2026-09-09-p4-bootstrap-patrol/`**；新会话交接文档 SPIDER `_note/handoff-2026-09-09-p4-bootstrap-config-v2.md`**；**校准 09-11 10:00 ~ 18:00**。18:44~19:21 因 `es_curl.sh` 解析 v2 格式失败守护失能 37 分钟（已修，见 patterns 第 56 条）。
  外部动态 rps 守护 `scripts/lc_adaptive_rps.sh`（peak/max 18000，用户算法：10 分钟慢请求占比 <40% 加档 / >50% 减半并 pause 2 分钟；全局预算）在本机运行，PID/状态见 `current/tasks.md`；Opus 巡检 Agent 每 5 小时一轮，经验沉淀在 `lessons/patterns-长周期生产巡检.md`（98 条）。
  历经：四层缺陷热修（`fb26e82`）、repair 误标事故与回滚（147,424 行，`e44b702` 互斥热修）、v2 延迟真熔断与动态守护、childCountOk 对称差白跑（`ca92fb3`）。决策记录见 `decisions/decision-2026-09-06-*`，失败经验见 `lessons/failure-*`。
  **② 配置 v2 + GitHub OAuth + res_lc 浏览 API 已于 09-08 上线**：网关双机 12:01 切 **master `6cf6157`**（[已被 09-09 `883daeb` 重部替换]，当时 res1 `cede6400ce65` / res2 `748f2125fe9d`；`ca92fb3` 二进制备份在宿主机 `spider.hotfix-p4-rollback.bak`，回到它需 `OSS_CONFIG_URL` 指回旧对象），27 个爬虫容器分批切 OSS 统一配置，NC-JS 前端 15:27 发布。**热修分支已弃用，网关此后从 master 构建。**
  遗留处置中：v2 二进制无本地回落导致未重部老容器重启即挂——已逐台重建 4 个 + 删 xunlei_share（15:56 完成，非 resdb 36 容器全部切 v2）；前端 gwEndpoint 默认值缺陷已修复重发（NC-JS `7fb3721`，15:48）；SLS log_store 漂移已修配置；~~配置按服务拆分为网关/爬虫两份~~ **[已废弃 2026-09-09] 这是对用户原则的误解**（要拆的是代码不是文件），两份文件方案已整体回退，见下方 09-09 条目；宿主机 config.yaml 未删。详见 `current/tasks.md`「配置 v2 上线」与 `lessons/failure-配置v2二进制无本地回落导致老容器重启即挂.md`。
- 上一步：**P0/P1/P2/P3 已完成（2026-09-05）**：
  生产已建 67 张 `res_lc_*` 表、两套 ES 模板、三索引四别名（P0）；网关双机含 lifecycle 且 `enabled=true`、
  `lifecycle_checker` 在 osec-jenkins 空转、前端 spiderAdmin 已发布（P1/P2）；
  **STORAGE 双写（osec-res1/res2 网关）与 API v3（两台 res-api）已上线并核验通过（P3）**——
  `res_short_202609` 开始增长、`index_failed=0`、MySQL 分表出行、`ReportUpsert` 正常、
  旧索引写入速率与改造前持平、v2/v3 四接口对拍一致。
  报告 `osec-spider-go/PRD/res-lifecycle/rollout-2026-09-05.md`（SPIDER `7435489`，已 push）。
  **P3 留了一个未完成项**：osec-resdb 的 `es_endpoint` 指向已下线 ES 集群，worker 侧双写未上线（已回滚，
  属既有故障，需用户决策）；**P4 启动前必须先确认 bootstrap 对 P3 期间已写入 id 的覆盖策略**。
  经验见 `sessions/2026/2026-09-05-生命周期P3上线.md`、`lessons/failure-resdb的ES端点指向已下线集群.md`。
- 上一步：P0 上线（基线采集 + `lifecycle_init_tables` + `lifecycle_init_indexes`），
  见 `sessions/2026/2026-09-05-生命周期P0上线.md`。
- 上一步：**Wave 1 五分支已本地合并并 push**——SPIDER(两分支)/STORAGE/API/NC-JS
  五仓库的 `feat/lifecycle-*` 分支均已 `merge --no-ff` 进本地主干，四仓库 build/test/type-check 全过，**均未 push**；
  验收通过后再定 push 与上线顺序。详见 `sessions/2026/2026-09-05-生命周期五分支合并.md`。
  验收报告"前置项 1"（轮换不回填 `index_role` 导致 prev 搬回 cur 路径失效）已修复，SPIDER `6b86db4`
  （master，未 push），详见 `current/tasks.md`。

- 次要待办：**队列 v2 上线收尾（人工）**——网关与全部消费者已上线在跑，剩余删 jenkins 旧容器、杀 2 个 2023 年裸进程、
  复核、旧队列存量迁移；脚本 `osec-spider-go/scripts/queue_v2_cutover_finish.sh`。**无回滚路径**。
  （queue-admin 原来那条"SLB 加 7543 监听"的待办**已随并入网关而作废**。）
- 最近一次重要变化：2026-09-05 晚 **生命周期改造代码全部完成并推送（五仓库），生产部署被权限拦截待用户决定**——
  Phase 0 契约 → 5 Agent 并行开发 → 合并 → Opus 端到端验收（修 2 阻塞 + 3 重要缺陷）→ 修前置项 → push。
  见 `sessions/2026/2026-09-05-生命周期改造实施.md`、`lessons/success-生命周期改造验收发现.md`、
  验收报告 `osec-spider-go/PRD/res-lifecycle/acceptance-2026-09-05.md`。
- 上一次重要变化：2026-09-05 **资源 ES 索引生命周期改造 PRD v1.1 完成**（`osec-spider-go/PRD/res-lifecycle/README.md`，
  2705 行，待用户确认 §14.2 Q1~Q6 后进入 Phase 0）。方案：短周期 cur/prev + 长周期三索引、读别名 `res_lc_all`、
  MySQL 128 张分表元数据、调度器并入网关 `services/gateway/lifecycle/`、STORAGE 双写、API 新增 v3 接口（v2 不动）、
  存量全量 bootstrap。**重大实测更正：旧索引里还有 2966 万无 join 的百度父文档（nested filelist），真实资源总量 ≈ 4440 万**。
  见 `decisions/decision-2026-09-04-资源索引生命周期改造方案.md`、`knowledge/architecture-es索引现状.md`、
  `sessions/2026/2026-09-04-资源生命周期改造PRD.md`。ES 体检脚本 `osec-spider-go/scripts/es_survey.sh`。
- 上一次重要变化：2026-09-04 晚 **管理服务并入网关 + 前端两个子应用合并**——
  按用户决策，`queue_admin` 由独立进程并入 `spider_gateway`（目录移到 `services/gateway/queue_admin/`，
  复用网关 RTC 7542 与原生 gRPC :8082、鉴权用网关 RtcToken，删掉 7543/7581/独立 token；
  网关跑两台机故新增 dlock 抢主锁只让一台做采集与告警）；**日后管理类需求一律放 `services/gateway/` 之下，不新增进程**。
  前端 `docSpiderScheduler` + `resSpiderScheduler` 合并成 `admin/spiderAdmin`，改为左侧栏+顶栏布局、
  全应用只保留一条 RTC 连接。两仓代码已 push（SPIDER `e725c86` / NC-JS `b1c6689`），**均未部署**。
  详见 `decisions/decision-2026-09-04-管理服务并入网关.md`、
  `decisions/decision-2026-09-04-前端合并为spiderAdmin.md`、
  `sessions/2026/2026-09-04-管理服务并入网关与前端合并.md`。
- 上一次重要变化：2026-09-04 晚 **队列监控管理系统 queue-admin 全流程上线**——
  一次会话完成 NC-JS 调研→PRD(v1.1, gRPC+WebRTC 接口层)→COMMON 契约 `queue_admin_rpc`→
  前后端并行开发(sonnet×2)→opus 验收(七条硬性项全过, 实修 12 问题含 3 个安全隐患)→
  合并部署：后端 `queue_admin` 已跑在 osec-res1(RTC 7543/回环 gRPC 7581, 复用网关 OSS 配置)，
  前端 resSpiderScheduler「队列监控」Tab 已发 OSS。线上实测队列快照/SLS/schema/年龄指标全通。
  详见 `knowledge/architecture-queue-admin.md`、`sessions/2026/2026-09-04-队列监控系统queue-admin.md`。
- 上一次重要变化：2026-09-04 **NC-JS 前端实现「队列监控管理」页**——在 `admin/resSpiderScheduler` 新增
  「队列监控」Tab（总览/队列详情/任务详情抽屉/日志搜索/黑名单管理），核心是通用 schema 渲染器
  （按后端 `GetDetailSchemas` 下发的 JSON 注册表渲染，未知 widget/无 schema 一律兜底 JSON 树，不白屏）；
  同时修好了失效的 `protc_gen.sh` 老路径并跑通生成链路，产出 COMMON `queue_admin_rpc` 的真实 TS 契约
  （非手写）；新增可切换的 mock 客户端供后端未就绪时整页联调。**过程中一次 `pnpm build` 意外触发了到
  生产 OSS 的真实上传**（NC-JS 子应用的 `mfe()` 构建插件默认 `deploy:true`，构建报错不代表没部署），
  已定位根因、验证无实际破坏、并把这个坑记录为 `lessons/failure-ncjs构建脚本会自动上传OSS.md`。
  已提交并 push 到 NC-JS 分支 `feat/queue-admin-ui`（**未合并 main**）。
  详见 `sessions/2026/2026-09-04-队列监控前端开发.md`。
- 上一次重要变化：2026-09-04 **SPIDER「队列 v2 升级」收尾清理完成**——删干净全仓残留的
  `queue_task.Service`(直连 redis list) 用法（`share`/`share_pwd`/`ad_share`/`quark_share`/
  `xunlei_share`/`keyword_filter`/`file_bot`/`urn` 命令及 `illuminate/queue-task/service.go`），
  爬虫提交链接统一走 `services/spider-common` 的 `CommitResLink`(推网关 `resourcePreCheck`)，
  关键词/资源消费统一用 `queue_task.StartQueueRemoteConsumer`；`go build`/`go vet` 全仓通过。
  `.vscode/launch.json` 补齐 `v2aliLoadShare`/`v2quarkLoadShare`/`v2xlLoadShare` 调试配置。
  已 push；上线时暴露**网关 ES 配置指向已下线集群**（自 1 月未重启没暴露），用户手改 `_note/config/spider.gateway.prod.yaml` 后恢复。见
  `decisions/decision-2026-09-04-队列v2统一走网关.md`（方案与状态）、
  `sessions/2026/2026-09-04-队列v2改造收尾清理.md`（过程）。
- 上一次重要变化：2026-09-03 **按线上进程清理已下线的爬虫代码**——以 `./deploy.sh ps`
  为唯一判据，删除 21 个线上无进程的爬虫命令及其代码/配置（26,228 行），保留 `keyword_haisou`
  与全部非爬虫工具命令；第二轮（09-04）补删 `deploy.sh` 的 `url_clear` 死条目与
  `services/online_doc/`、`services/alipan/` 两个无引用死包。
  见 `decisions/decision-2026-09-03-清理下线爬虫代码.md`。
  改动已 `git add` **未提交、未部署**；osec-resdb 两个废弃容器的删除需人工跑 sudo，见 `current/tasks.md`。
- 上一次重要变化：2026-09-03 **下线 `haisou.cc`**（见 `decisions/decision-2026-09-03-下线haisou.md`）。
  同日先完成了该站匿名身份头逆向与积分账本实现（SPIDER `2889959` 已 push），确认拦截绕不开后下线。
- 上一次重要变化：2026-09-03 **统一 7 个新爬虫的保活语义**——`p.alive()` 从
  「轮次成功后调用」改为「`CommitResLink` 返回 nil 时调用」；同时修掉 `illuminate/keepalive`
  读 nil channel 会挂死调用协程的隐患。见 `lessons/success-爬虫保活语义.md`。
- 上一次重要变化：2026-09-03 **并行开发并合并了站点发现首轮筛出的 6 个站点爬虫**——
  用 4 个并发子 Agent + 独立 git worktree 完成，全部已合并进 SPIDER 的本地 `master`
  （12 个提交）。当时未 push 未上线，**后已全部部署上线**（见本节最上方）。子命令与验收状态：

  | 站点 | 子命令 | 联网验收 |
  |---|---|---|
  | `bbs.dyyjmax.org` | `bbs_dyyjmax` | ✅ 通过（79987 与 sitemap 完全一致） |
  | `fuxipan.com` | `bbs_fuxipan` | ✅ 通过（小样本 15/15，增量对账 2510 一致） |
  | `feikuai.tv` | `bbs_feikuai` | ✅ 通过（30 个 id 区间对账完全一致） |
  | `kuakes.com` | `bbs_kuakes` | ✅ 通过（5618 两套 sitemap 互证差值 0） |
  | `www.misoso.cc` | `bbs_misoso` | ✅ 通过（增量 32/32，去重 20/20） |
  | `haisou.cc` | `keyword_haisou` | ❌ **未通过 → 已下线**，见下 |

  详见 `knowledge/domain-站点-2609接入批次.md`、`knowledge/domain-站点-misoso.md`，
  流程经验见 `procedures/workflow-并行开发多站点爬虫.md`。
  **haisou.cc 已下线**（2026-09-03 用户决定，见 `decisions/decision-2026-09-03-下线haisou.md`）：
  搜索端点对代理池 IP 段做**端点级拦截**（`13001`，**不扣积分**，全新满额 IP 首请求即被拒），
  客户端侧改造（身份头/积分账本/节流/指纹轮换）全部绕不开；用户自己 IP 花光 100 分后返回的是
  `11003`，说明**普通 IP 能搜、是代理网段被针对**——`11003` 与 `13001` 是两条互不相干的拒绝路径。
  另：额度 = min(ip 桶, fingerprint 桶)，ip 桶是硬约束；单 IP 上限 50 次搜索/天 ≈ 1000 条/天，
  即使放行也排不进优先级。RDAP 查实代理是**电信省级宽带秒拨段、不是机房 IP**，
  通用 IP 纯净度库对这类拦截无效。
  处置：代码保留但 `enabled` 为 nil 视为**关闭**（与其他爬虫相反），`deploy.sh` 保持注释，
  探路 cron 已撤除。逆向成果（`services/haisou/client_context.go` 的匿名身份头、
  `credits.go` 的按积分记账模式）对同类风控站点有复用价值。
- 上一次重要变化：2026-09-03 **建立常态化「站点发现」任务并跑完首轮**——
  流程与工具落在 `site-discovery/`（触发词 `task site-discovery`）；首轮初筛 47 个站点、
  深挖 23 个，**6 个满足全部验收标准**（`bbs.dyyjmax.org`、`fuxipan.com`、`www.misoso.cc`、
  `haisou.cc`、`kuakes.com`、`feikuai.tv`），等待用户定开发优先级。
  同时实测确认**夸克新业务码 `41031`（分享者被封）= 失效**，详见下方核心事实。
- 上一次重要变化：2026-09-02 **修复夸克/阿里云盘链接有效性检测**——
  改判定为业务码优先、限流不判失效、未知响应报错；API 与 SPIDER 两套 checker 对 30 条样本结论一致，
  0 报错，**尚未上线**。详见 `knowledge/网盘有效性检测` 与同日会话摘要。
  同日更早完成 kkpans 爬虫开发（命令 `bbs_kkpans`，亦未上线）、该站调研与 PRD、
  `PPIO → 1s` 重命名收尾、SPIDER 两处存量编译错误修复
- 当前阻塞：无。
- 四个 Go 仓库 `go build ./...` 全部通过；SPIDER 新增代码 `go vet` 干净
- 下一步：详见 `current/tasks.md`

## 3. 核心事实

- 仓库清单（磁盘目录名 ≠ Go module 名，务必分清）：
  | 角色 | 磁盘路径 | Go module / 技术栈 |
  |---|---|---|
  | COMMON | `1s/enfi-resource-common` | `github.com/1s/enfi-resource-common` |
  | SPIDER | `1s/osec-spider-go` | `github.com/1s/enfi-spider-go` |
  | API | `1s/osec-resource-api` | `github.com/1s/enfi-resource-api` |
  | STORAGE | `1s/enfi-resource-storage` | `enfi-resource-storage` |
  | NC-JS | `1s/nc-js` | 前端 mono repo（pnpm + Vite6 + Vue3 TSX + ant-design-vue） |
- **[事实 2026-09-08] 前端"环境选择"默认值必须由 `location.hostname` 推导**：两个连网关的子应用
  原本写死 `useLocalStorage('gwEndpoint', gwAddrs[1])`(本地 127.0.0.1)，生产清空 localStorage 后
  永远卡在「正在连接服务器(本地环境)」。已抽 `defaultGwAddr()`(catalyst `rtc-rpc.ts`，按 name 匹配非下标)
  并发布 spiderAdmin/panShareDownload（NC-JS `7fb3721`，2026-09-08 15:47/15:48 上线，CDP 复测通过）。
  → `lessons/failure-前端环境默认值写死本地.md`
- **[事实 2026-09-04] NC-JS 是后台前端仓库**：`admin/` 下是 qiankun 微前端主应用 + 3 个子应用
  （**spiderAdmin**(队列监控+资源配置+文档爬虫) / panShareDownload / login3rd），用于管理爬虫任务与网盘账号。
  它**不调 API 仓库的 HTTP 接口**，而是用 WebRTC DataChannel 上的 gRPC 直连 SPIDER gateway
  （`115.29.215.228:7542`）。**鉴权已于 2026-09-08 改为 GitHub OAuth 登录（限 1second 组织成员），
  固定管理秘钥 RtcToken 降级为可关闭兜底（生产 `allow_rtc_token=false`）；代码已合并未部署。**
  详见 `knowledge/architecture-nc-js.md`、`decisions/decision-2026-09-08-后台登录改为github-oauth.md`。
- COMMON 是唯一的契约中心：所有 gRPC `.proto` 与生成代码都在 `rpc/` 下，改协议必须先改 COMMON。
- 主数据链路：SPIDER 爬虫 → SPIDER gateway 调度（Redis 队列）→ `storage.UpsertResource` gRPC → STORAGE gateway(:8081) → 异步 worker → Elasticsearch → API 查询。
- 支持的网盘类型常量：`bnd`(百度)、`ali-share`(阿里)、`quark`(夸克)、`xunleipan`(迅雷)。
- 链接有效性检测有**两套独立实现**：API `services/valid/`（对外 `POST /v2/validShareLink`）
  与 SPIDER `services/gateway/valid/`（存量清理 `clear_expire`），改判定逻辑要同时改。
  判失效会不可逆地删 ES 数据，因此**未知响应一律报错，不判失效**。
- **[用户确认 2026-09-02] 磁力/BT 已停止采集与入库**，只处理上述 4 种网盘类型；存量索引与查询接口保留。
  新写爬虫不得调用 `resource.SaveMagnetResource`。
- **[用户确认 2026-09-03] 分享链接爬虫一律走 IP 代理池，任何情况下都不允许仅用本机直连。**
  确认有反爬的站点更要禁用本机 IP 直接访问。反爬站的可行性门槛是
  **单 IP ≥10 条分享链接/分钟**，达不到才算不可行——吞吐靠代理池横向扩，不靠单 IP 硬刚。
  本地拿代理的链路是：生产 `proxy-provider` 发布到 redis 频道 `proxy_subject` →
  SPIDER `tools/redis-topic-sync`（GoLand 配置 `sync-redis`）经 ssh 隧道同步到本地
  redis 127.0.0.1:6379/2 → 爬虫/工具订阅。**启动同步进程前必须先确认没有已在跑的实例**，
  多跑一个会让同一代理 IP 被重复推送，池子虚高且单 IP 请求频率翻倍。
  另外蜻蜓代理按 **IP 白名单**鉴权，本地还要常驻跑 `go run . dev_add_local_ip_to_qingting`
  把本机公网 IP 同步进白名单，否则代理全部连不上。
  [实测 2026-09-03] 两件事都做完后，代理 **6/6 可用**，`pancheck --require-proxy` 0 unknown。
  两个坑：① 取公网 IP **必须用境内接口**——装了 TUN 透明代理时境外接口给出的是代理出口，
  和境内出口不是同一个 IP，用错了只表现为"代理全部连不上"；
  ② 蜻蜓凭据正本在 `change_proxy_config.go` 的 `init()` 里，会覆盖 `proxy-provider.go`
  的旧常量与 config yaml，排查时只看旧常量会误判成"token 全过期"。
- **[事实 2026-09-03]** 夸克业务码 `41031`「分享者用户封禁链接查看受限」（HTTP 403）**属于失效**。
  两套生产 checker 的 code 白名单都没有它，只靠 message 兜底正则命中，
  建议补进 `quarkInvalidCodes` 减少对文案的依赖。
- **[用户确认 2026-09-03] 爬虫保活 `keepalive` 只在 `CommitResLink` 成功（返回 nil）时续期。**
  站点会一直返回相同的几个链接，轮次成功 ≠ 爬虫在正常工作；提交成功才是唯一判据。
  → `lessons/success-爬虫保活语义.md`
- **[用户确认 2026-09-03] 需要全站扫描的爬虫，禁止在启动时触发全量。**
  首次全量完成后把**完成时间写进 redis**（建议键 `<site>:fullsweep:lastdone`，不设 TTL，
  只有整轮成功才写）；启动时检查该时间，有且未超 `FullSweepInterval` 就**跳过全量**，
  直接进增量节奏。原因：线上重启是常态（部署、维护、`--restart always` 自动拉起），
  每次重扫全站会打爆站点限流与代理池额度，而增量本就在覆盖新增，重扫结果几乎全是 `skipDup`。
  → `decisions/decision-2026-09-03-全站扫描不在启动时触发.md`
  ⚠️ 现有 5 个爬虫（kkpans/dyyjmax/fuxipan/misoso/kuakes）**都还是启动即全量，待改造**；
  `feikuai` 的"游标分批全量"结构天然合规，新爬虫可优先照它写。
- **[事实 2026-09-03] `deploy.sh` 的 `serviceToHosts` 映射表不代表线上现状**，里面会残留僵尸条目
  （本次实测 `aiyoweia`/`repanso`/`yunso_net` 三个挂着主机但线上零进程，已删）。
  判断现役服务**只能**用 `./deploy.sh ps`。反过来也成立：线上还跑着 `spider.go` 里已不存在的
  老二进制命令（`osec-resdb` 上的 `share_download_push_resolve_alipan_241226`、
  `..._qb-250225`，已跑 18~20 个月），重新部署会起不来；用户已确认这两个不需要了，待人工删除容器。
- 生产部署靠 SPIDER 仓库的 `deploy.sh`（ssh + docker），主机名 `osec-res1/res2/resdb/restest/resngix/jenkins`。
  **[事实 2026-09-04] `deployService` 只部署 `serviceToCmd` 的第一个词**，一个 service 只能挂一个命令（多命令条目从未生效过）。
- **[事实 2026-09-04] SPIDER `feat/sweep-guard-a/b` 已合并进 master**（5 个 bbs 爬虫"启动不触发
  全量扫描"落地，`git merge --no-ff` + 冲突手工解决，`go build/vet/test` 全过，worktree 与分支已删，
  未 push）。冲突取舍见 `decisions/decision-2026-09-04-合并sweep-guard分支冲突取舍.md`。

## 4. 用户与协作偏好

- 输出语言：中文（对用户展示、代码注释、记忆文件全部中文）
- 有价值的脚本要落盘进仓库并写文档，后续通过项目内路径调用以省 token
- **[用户确认 2026-09-04] 编码/验收/合并都派 sonnet 子 Agent，主会话只把控全局**
- 详见 `agent-memory/02-user-preferences.md`

## 5. 当前关键决策

- **管理类服务并入 spider_gateway 进程，不再新增进程**（2026-09-04）：`queue_admin` 移到
  `services/gateway/queue_admin/`，复用网关 7542/:8082 与同一套握手鉴权（当时是 RtcToken，
  2026-09-08 起是 GitHub 会话票据）；双实例靠 dlock 抢主锁。
  影响：`./deploy.sh deploy gateway` 一条命令搞定，SLB 无需加端口；管理功能改动要重启网关。
  → `decisions/decision-2026-09-04-管理服务并入网关.md`
- **后台前端合并为 spiderAdmin**（2026-09-04）：两个子应用合一、左侧栏布局、一条 RTC 连接。
  影响：新后台页面一律加到 `spiderAdmin` 的左侧菜单；旧 apps.json 条目需人工摘除。
  → `decisions/decision-2026-09-04-前端合并为spiderAdmin.md`
- **跨进程任务投递统一走网关 res_scheduler 队列（队列 v2）**（2026-09-04）：全部 `queue_task.Service`（直连 redis list）
  用法已删除；爬虫 `CommitResLink` → 网关 `resourcePreCheck` → 网关预检分发 → `bnd*/ali/quark/xl LoadShare` 队列；
  关键词由网关扇出到 `keywordSubscribed:<site>`。影响：新增 `v2{ali,quark,xl}LoadShare` 命令，删 8 个旧命令；
  已 push 并上线（收尾见 `current/tasks.md`）。
  → `decisions/decision-2026-09-04-队列v2统一走网关.md`
- **按线上进程清理下线爬虫代码**（2026-09-03）：删掉 21 个 `./deploy.sh ps` 查不到进程的爬虫命令，
  非爬虫的工具/运维命令保留。影响：`spider.go` 命令表瘦身到 40 条，`config` 与 `deploy.sh` 同步清理。
  → `decisions/decision-2026-09-03-清理下线爬虫代码.md`
- **下线 haisou.cc**（2026-09-03）：站点对代理池 IP 段端点级拦截（13001，不扣积分），
  客户端改造绕不开；且单 IP 上限 50 次搜索/天 ≈ 1000 条/天，排不进优先级。
  影响：代码保留但默认不启动，本批可用站点由 6 个变 5 个。
  → `decisions/decision-2026-09-03-下线haisou.md`
- **全站扫描不在启动时触发**（2026-09-03）：改为 redis 记完成时间 + 启动时检查跳过。
  原因：重启是常态，重扫全站打爆限流与代理额度且收益近零。影响：5 个存量爬虫待改造。
  → `decisions/decision-2026-09-03-全站扫描不在启动时触发.md`
- **停止磁力资源采集**（2026-09-02）：只保留 4 种网盘类型。
  原因：业务范围收敛。影响：新爬虫不再抓磁力接口、不调 `SaveMagnetResource`；存量不动。
  → `decisions/decision-2026-09-02-停止磁力资源采集.md`

## 6. 高价值经验

- **跨包重构并行化用三阶段**：主会话先做共享契约(Phase 0) → 子 Agent 只加不删(Phase 1) → 单独清理 Agent 收尾(Phase 2)，
  否则各 worktree 会因互相引用编译互锁。hub 代码（网关分发）要由主会话亲自审，能抓到子 Agent 自测不出的时序 bug。
  见 `lessons/patterns-并行重构的分阶段切分.md`。
- 网盘失效判定要用**业务码**而不是中文文案匹配；**限流（429/空 body）不等于失效**；
  判不准就返回 error 让上层看到 -1，绝不能返回"失效"触发删除。见 `lessons/success-网盘失效判定原则.md`。
- 排查第三方接口判定问题，**一次跑一批样本（15 条起）**才抖得出冷门业务码，单条试探必漏。
- 新写爬虫要用「假 committer + 独立 redis 键前缀 + 环境变量开关」写联网集成测试，
  断言用站点自己返回的 `total` 对账而不是写死条数。见 `lessons/success-爬虫联网集成测试.md`。
- 线上非 gateway 服务的 `config.yaml` **不由 `deploy.sh` 分发**，新增配置节必须给全套内置缺省值，
  开关字段用 `*bool`（nil 视为开启），否则线上配置未同步时服务会静默空跑。
- 判断"能不能编译"必须逐仓库实测；Go 的目录型 `replace` 不校验被替换模块的 module 名，"下游能编译"不能证明上游模块声明是对的。
- 找新站点的渠道里，**开源聚合项目（PanSou/PanHub 的插件目录）性价比最高**，一次能薅几十个域名，
  已固化成 `site-discovery/tools/harvest.py`。
- 评估论坛型资源站，**先量化「游客可见率」**——最常见的淘汰原因是「回复可见/登录可见」而非规模或有效率。
- 调研新站点先挖前端 JS bundle 里的 REST 接口路径与参数枚举，比逐个试 URL 快得多；
  但**默认列表的 `total` 常只是"首页推荐"子集**，必须用 sitemap 对账才能确认全量。见 `procedures/workflow-新站点调研.md`。
- 配置文件（`config*.yaml`、`deploy.sh`）内含明文 AK/SK 与数据库口令，**禁止**写入记忆文件或对外输出，只记录文件路径。
- **调研结论有保质期，"限流/配额"这一类尤其短**。haisou.cc 上午调研串行 20 次全通过，
  下午开发时同一接口对代理池 IP 全量 429——调研与开发间隔越久，动手前越要花一次请求
  重验核心接口。区分"配额耗尽"与"端点被封"的硬判据是**全新 IP 的首次请求**是否也被拒。
- **并行开发多站点爬虫**：共享资源（代理池、白名单同步）必须由主会话集中准备，
  子 Agent 只读不启；提示词里提前禁止改共享配置文件，冲突面能收敛到
  `config/config.go` + `spider.go` 两处。见 `procedures/workflow-并行开发多站点爬虫.md`。
- 子 Agent 常见两种失败模式：**卡在等自己起的后台任务**（通知永远不来）、
  **把"跑全量"当成验收必要条件**（烧时间和站点配额）。提示词里直接禁掉 Monitor、
  明确"抽样对账即可"，能省掉整轮往返。
- SPIDER 仓库有**大量存量的 `go vet` 告警与测试失败**（`services/alipan`、`services/quark`、
  `services/gateway/*`、`services/devops/*` 等）。验收新代码只看新增包，存量问题如实报告但不要顺手改。
- **antdv 组件的 `style` 一律传对象、不要传字符串**：`Row`/`Menu.Item` 用 `Object.assign` 合并 `attrs.style`，
  字符串会被展开成索引键并抛 `Failed to set an indexed property [0] on 'CSSStyleDeclaration'`（异步渲染下显示为
  `Uncaught (in promise)`，容易误判成非渲染问题）。见 `lessons/failure-antdv-Row-字符串style.md`。
- **NC-JS 子应用的标准 `pnpm build` 会自动上传生产 OSS**（`mfe()` 插件默认 `deploy:true`，挂在
  `closeBundle`，不看 `mode`，构建报错也可能已经上传完）。验证构建前先在 `vite.config.ts` 给
  `mfe()` 传 `{ deploy: false }`，验证完 `git checkout` 还原。见 `lessons/failure-ncjs构建脚本会自动上传OSS.md`。
- **自研 RTC-gRPC 传输的统一取消路径 `cancelAllPendingCalls` 会把失败原因重建成只剩
  `code`/`message` 的 protobuf 类型，任何附加业务字段都会被物理丢弃**——凡是"握手/业务
  错误需要带结构化信息给上层"的需求，都要走专门回调，不能指望 RPC 错误通道能穿透。
  见 `lessons/failure-握手回包附加字段被传输层丢弃.md`。
- **涉及浏览器可见交互的改造，静态审查 + 单测不足以验收**：要造一个只保留被测链路的
  桩服务（不依赖 redis/mysql/ES）+ 带登录态的调试浏览器（`scripts/agent-browser.sh` +
  `scripts/cdp.py`）做真实联调，本次靠它抓到两个"两端代码分别看都对、串起来不对"的
  阻断级问题。见 `lessons/success-桩网关加cdp浏览器做登录链路联调.md`。
- **前端改动验收至少跑一次"清空 localStorage / 无痕的首次访问"**——开发者浏览器里的存量本地状态
  会系统性掩盖首次访问类缺陷（本次的生产卡死缺陷从 09-04 潜伏到 09-08 才被发现）。
  见 `lessons/failure-前端环境默认值写死本地.md`。
- **收到"拆分/隔离"类需求先复述拆的对象**（代码/文件/进程）再动手；发现自己在写"误用就 panic"的
  运行时护栏或"配置里不要写某项"时，说明本可以让错误引用编译不过——层级选错了。
  见 `lessons/failure-把拆配置理解成拆文件.md`。
- **旁路能力（监控/埋点）的初始化必须能降级**：不要用 `db.Redis` 这类"失败即 Fatal/panic"的
  基础设施函数去初始化可有可无的监控，尤其在配置按服务拆分之后（网关那份没有 `services.proxy` 节）。
  `log.Fatal` 无法 recover，只能靠前置条件判断绕开。**埋点只覆盖"拿到响应"的分支，
  等于让最严重的故障隐形**——设计观测点先问"失败得最彻底的那条路径会被记录吗"。
  见 `lessons/failure-旁路能力初始化拖垮主流程.md`。
- **多任务并行时先由主控做 Phase 0**（proto 契约 + 前端菜单/插槽/mock/客户端接线一次做完），
  子 Agent 只填各自的文件：本次 5 个 Agent 并行改 5 个仓库**零合并冲突**。
  NC-JS 用不了 worktree（pnpm workspace），改用"文件边界互斥 + 禁止子 Agent commit、主控代提交"，
  同样有效。**hub 代码（命令分发、服务注册、热路径埋点）必须主控逐行审**——本次两个验收
  Agent 都没抓到的阻塞级缺陷是主控自己审出来的。
- **qiankun 子应用的 Vue 必须挂到 `props.container.querySelector('#app')`，不能挂包裹层本身**——Vue `mount()` 会清空容器，
  把 `<qiankun-head>` 内联的静态 CSS 一起删掉，症状是"线上样式丢、本地全正常"。覆盖 antd 4 组件缺省外观要看清它生成的
  两级选择器，优先用 `ConfigProvider` 组件 token。线上样式问题先用无头 Chrome `--dump-dom` 拿真实 DOM。
  见 `lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md`。

## 7. 待解决问题

- 见 `current/open-questions.md`

## 8. 快速加载指引

| 主题 | 文件 |
|---|---|
| 项目背景与仓库职责 | `03-project-context.md` |
| 用户偏好 | `02-user-preferences.md` |
| 系统架构与数据链路 | `knowledge/architecture-系统总览.md` |
| 爬虫内部结构/命令 | `knowledge/architecture-spider.md` |
| 存储与 ES 索引 | `knowledge/architecture-storage.md` |
| HTTP 查询接口 | `knowledge/architecture-api.md` |
| 后台前端 / qiankun 子应用 / 加后台页面 / spiderAdmin | `knowledge/architecture-nc-js.md` |
| 后台登录 / GitHub OAuth / RtcToken 兜底 | `knowledge/architecture-nc-js.md` §5、`decisions/decision-2026-09-08-后台登录改为github-oauth.md` |
| 带登录态的浏览器自动化 / 桩网关联调 | `procedures/workflow-带登录态的浏览器自动化.md`、`lessons/success-桩网关加cdp浏览器做登录链路联调.md` |
| gRPC 协议契约 | `knowledge/api-rpc契约.md` |
| 术语（bnd/valid/version…） | `knowledge/concept-术语表.md` |
| 本地编译与验证 | `procedures/workflow-本地构建与验证.md` |
| 生产部署 | `procedures/workflow-部署.md` |
| 历史决策 | `decisions/` |
| 爬虫集成测试写法 | `lessons/success-爬虫联网集成测试.md` |
| 调研新站点 / 写爬虫 PRD | `procedures/workflow-新站点调研.md` |
| kkpans / KK网盘 / 光鸭云盘 | `knowledge/domain-站点-kkpans.md` |
| dyyjmax/fuxipan/feikuai/kuakes/haisou | `knowledge/domain-站点-2609接入批次.md` |
| misoso / melost.cn | `knowledge/domain-站点-misoso.md` |
| 并行开发多个爬虫 / worktree 分工 | `procedures/workflow-并行开发多站点爬虫.md` |
| 派子 Agent / 任务描述落盘 / 多 agent 上下文重复 | `procedures/workflow-子agent任务简报.md`（模板 `agent-tasks/README.md`） |
| 哪些爬虫是现役的 / 为什么删了某个爬虫 | `decisions/decision-2026-09-03-清理下线爬虫代码.md` |
| haisou 为什么下线 / 13001 | `decisions/decision-2026-09-03-下线haisou.md`、`lessons/failure-haisou搜索接口收紧.md` |
| 全量扫描什么时候触发 / 启动即全量 | `decisions/decision-2026-09-03-全站扫描不在启动时触发.md` |
| 保活 / keepalive / alive() 放哪 | `lessons/success-爬虫保活语义.md` |
| 链接失效检测 / validShareLink | `knowledge/domain-网盘有效性检测.md` |
| 站点发现常态化任务 | `procedures/workflow-站点发现.md` → `site-discovery/README.md` |
| 已探索过哪些资源站 | `site-discovery/history.md` |
| 队列 v2 / 网关队列怎么用 / 旧队列命令去哪了 | `knowledge/architecture-spider.md`"队列约定"、`decisions/decision-2026-09-04-队列v2统一走网关.md` |
| 并行重构怎么切子 Agent | `lessons/patterns-并行重构的分阶段切分.md` |
| 重启网关/服务前要查什么 / ES 集群换了 | `procedures/workflow-部署.md`"重启前验证"、`lessons/failure-网关重启暴露ES集群已更换.md` |
| NC-JS 加后台页面 / queue_admin 前端 / schema 渲染器 | `knowledge/architecture-nc-js.md`、`sessions/2026/2026-09-04-队列监控前端开发.md` |
| NC-JS `pnpm build` 会不会部署到生产 OSS | `lessons/failure-ncjs构建脚本会自动上传OSS.md` |
| antdv 组件 style 报错 / CSSStyleDeclaration 索引属性 | `lessons/failure-antdv-Row-字符串style.md` |
| 资源生命周期架构图 / 用 archify 画图 | `osec-spider-go/PRD/res-lifecycle/diagrams/README.md`、`lessons/success-archify画图的几何约束.md` |
| 告警怎么配 / 失败率窗口阈值 / 告警历史 | `services/gateway/queue_admin/{alert.go,alert_rules.go,alert_history.go,fail_window.go}` |
| 代理池监控 / Scene / 失败分类 / 上报包 | `illuminate/proxy-client/{hook.go,classify.go}`、`illuminate/proxy-monitor/`、`services/gateway/proxy_admin/` |
| 一条链接为什么没入库 / 链路时间线 | 后台「链接追踪」页；`services/gateway/queue_admin/trace.go` |
| 云端 Chrome / FC 装插件油猴 | `enfi-resource-common/fc-chrome/README.md` |
| 文档爬虫服务端 / doc-crawler | `osec-spider-go/services/doc_crawler/`、契约 `agent-tasks/2026-09-08-monitoring-and-doc-fc/05-doc-fc-contract.md` |
| 当前任务/风险/疑问 | `current/` |
