---
title: 项目总览
type: overview
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-18T10:45:00+08:00
priority: critical
keywords: [网盘资源爬取, 版权取证, COMMON, SPIDER, STORAGE, API, NC-JS]
summary: 网盘资源取证系统的最小启动上下文：五仓库职责、数据链路、最近 7 天状态、在生效的决策与经验，以及怎么用 mem.py 找其余记忆文件
load: always
related:
  - agent-memory/03-project-context.md
  - agent-memory/current/changelog.md
  - agent-memory/current/tasks.md
---

# 项目总览

## 1. 项目身份

- 风控技术部「网盘资源爬取与取证系统」：爬分享资源 → 沉淀可检索证据 → 支撑版权追责。
- 4 个 Go 仓库（爬虫/存储/API/契约库）+ 1 个前端 mono repo（内部后台 NC-JS）。
- 长期运行的存量系统；2609 批次 6 个爬虫在跑（kkpans/dyyjmax/fuxipan/feikuai/kuakes/misoso），第 7 个 haisou.cc 已下线。
- 边界：发现、入库、检索 + 内部后台；不做对外产品前端与法务流程。

## 2. 当前状态（最近 7 天；更早见 `current/changelog.md`）

- 09-16 **五站爬虫已上线**（jenkins/res2/res1，新版 deploy.sh 首次实跑），首日观察速率与类型 → `knowledge/domain-站点-260916接入批次.md`
- 09-16 **十项提案已合入五仓库并 push，服务未重部**（前置项 `agent-tasks/2026-09-16-ten-proposals/95-merge-plan.md`）；云端文档脚本迁入 NC-JS 已合入（OSS 上传待人工）
- 09-16 **文档发现首轮完成**（29 篇，批量待执行）→ `procedures/workflow-文档发现.md`
- 09-15 **P5 阶段 D 灰度爬坡中**；失效上报仍 dry run → `current/tasks.md`
- 09-12 **🔴 事故：lifecycle_checker 误删 115.5 万资源**，修复已部署，重爬回库 ≈56% → `lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`
- 阻塞：无；风险 `current/risks.md` R9。

## 3. 核心事实

- 仓库（磁盘名 ≠ module 名）：COMMON `enfi-resource-common`、SPIDER `osec-spider-go`→`enfi-spider-go`、API `osec-resource-api`→`enfi-resource-api`、STORAGE、NC-JS。→ `03-project-context.md`
- COMMON 是唯一契约中心，`.proto` 与生成代码都在 `rpc/`，**改协议先改 COMMON**。→ `knowledge/api-rpc契约.md`
- 主链路：爬虫 → 网关调度（Redis 队列）→ `storage.UpsertResource` → STORAGE → 异步 worker → ES → API。→ `knowledge/architecture-系统总览.md`
- 只处理 4 种网盘 `bnd`/`ali-share`/`quark`/`xunleipan`；磁力已停采，不得调 `SaveMagnetResource`。→ `decisions/decision-2026-09-02-停止磁力资源采集.md`
- 有效性检测 **API/SPIDER 两套独立实现**，改判定要同时改；判失效会不可逆删 ES，**未知响应一律报错**。→ `knowledge/domain-网盘有效性检测.md`
- **爬虫一律走 IP 代理池**，禁止本机直连；本地链路与两个坑见 `lessons/success-本地代理池打通.md`。反爬站门槛：单 IP ≥10 条/分钟。
- 保活 `keepalive` 只在 `CommitResLink` 返回 nil 时续期。→ `lessons/success-爬虫保活语义.md`
- 全站扫描**禁止启动即全量**（redis 记完成时间跳过）；5 个存量爬虫待改造，`feikuai` 合规。→ `decisions/decision-2026-09-03-全站扫描不在启动时触发.md`
- 云端文档脚本源码在 NC-JS `apps/doc-cloud-spider`；上传 OSS 前先本机端到端。
- 部署用 SPIDER 的 `deploy.sh`（ssh+docker）；**现役服务只能用 `./deploy.sh ps` 判断**。→ `procedures/workflow-部署.md`
- NC-JS 是后台前端（qiankun + spiderAdmin 等 3 子应用），**不调 API 仓库 HTTP**，走 WebRTC 上的 gRPC 直连网关 `:7542`；鉴权已改 GitHub OAuth，RtcToken 降为兜底。→ `knowledge/architecture-nc-js.md`

## 4. 用户与协作偏好

- 全中文输出（展示/注释/记忆）；有复用价值的脚本落盘写文档，按路径调用省 token。
- **用户常不在电脑旁：长任务开始/里程碑/完成、任何异常或阻塞都要主动发邮件**，`scripts/mail/notify.py -s 主题 -f body.md -l progress|done|warn|error`（Markdown→HTML 卡片）→ `procedures/workflow-任务进度邮件汇报.md`
- 编码/验收/合并派 sonnet 子 Agent；任务描述落盘 `agent-tasks/` 而非写进 prompt。
- 禁用 harness 记忆，只写 `agent-memory/`（独立仓库，单独 commit+push）。
- **配置文件里的明文 AK/SK 与库口令禁止写进记忆文件或对外输出，只记路径。** → `02-user-preferences.md`

## 5. 当前关键决策（正本在 `decisions/`，本节只列仍在生效的）

- P5 切 v3 准入门槛 G1~G6 与 D1~D4 裁定（失效只提前复检、口径改语料级、bnd 去 has_child、门槛全过才切）→ `decision-2026-09-12-P5切v3准入门槛与失效同步.md`
- 记忆系统瘦身与脚本化加载 → `decision-2026-09-12-记忆系统瘦身与脚本化加载.md`
- 配置按进程拆**代码**而非拆文件 → `decision-2026-09-09-配置按进程拆代码而非文件.md`
- 后台登录改 GitHub OAuth（含上线顺序）→ `decision-2026-09-08-后台登录改为github-oauth.md`
- 资源 ES 索引生命周期改造 → `decision-2026-09-04-资源索引生命周期改造方案.md`
- **弃用 report/likes/dislikes/addViews 等 update ES 文档的接口**（删文档不回收磁盘），不做 v3 → `decision-2026-09-12-弃用文档更新类接口.md`
- 管理类服务并入 `spider_gateway`，不新增进程 → `decision-2026-09-04-管理服务并入网关.md`
- 后台前端合并为 `spiderAdmin` → `decision-2026-09-04-前端合并为spiderAdmin.md`
- 任务投递统一走网关队列（队列 v2，收尾无回滚路径）→ `decision-2026-09-04-队列v2统一走网关.md`
- 按线上进程清理下线爬虫代码 → `decision-2026-09-03-清理下线爬虫代码.md`
- 全站扫描不在启动时触发 → `decision-2026-09-03-全站扫描不在启动时触发.md`
- 下线 haisou.cc（端点级拦截绕不开）→ `decision-2026-09-03-下线haisou.md`

## 6. 高价值经验（正本在 `lessons/` `procedures/`，其余用 `mem.py search`）

- **删除等不可逆功能上线前必须线上 dry run，再用 CDP/查库等独立手段复核（禁止复用新功能代码），通过才开启** → `procedures/checklist-不可逆操作上线.md`；首日看 valid/invalid 绝对数、告警配绝对阈值 → `lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`
- 跨包重构切三阶段，hub 代码主控逐行审 → `lessons/patterns-并行重构的分阶段切分.md`；多线并行改造：断网跑测试、假主机名、逐线验收、`scripts/dev/integration_check.sh` 合并预演 → `procedures/workflow-并行多任务开发与合并预演.md`
- 失效判定看业务码不看文案，判不准就报错；样本 15 条起 → `lessons/success-网盘失效判定原则.md`
- 监控/埋点初始化必须可降级，且要覆盖最彻底的失败路径 → `lessons/failure-旁路能力初始化拖垮主流程.md`
- NC-JS `pnpm build` 会真实上传生产 OSS，验证前先关 `deploy` → `lessons/failure-ncjs构建脚本会自动上传OSS.md`
- **FC 上 WebSocket 断开即冻结实例，收尾/写回必须在连接内做（拦截 `Browser.close`）** → `lessons/failure-FC实例在WebSocket断开后立即冻结.md`
- **找在线文档：GitHub 代码搜索 ≫ link3 关键词搜索；link3 直连 100 次即 429，必须走代理池** → `lessons/failure-link3接口按IP限流直连百次即429.md`
- 新站点调研先挖 JS bundle 接口、`total` 须用 sitemap 对账；**结论有保质期** → `procedures/workflow-新站点调研.md`
- 端到端验证脚本不要"端口有响应就复用"，托管进程每次重启、脚本 URL 带哈希 → `lessons/failure-端到端复用旧托管进程导致注入旧脚本.md`
- 在线文档站解析优先 fetch 页面自带接口（performance 资源列表 + bundle 搜路径常量）→ `lessons/success-在线文档解析优先用页面自带接口.md`
- **SLS `field:value` 是分词匹配，统计口径要用 SQL `where` 等值过滤** → `lessons/failure-SLS字段检索按分词匹配误命中其他stage.md`
- 邮件脚本直接 `scripts/mail/notify.py` 调用，不用 `python3 x.py`；发送类脚本禁止静默降级 → `lessons/failure-notify脚本静默降级把原始Markdown发成邮件.md`

## 7. 待解决问题

- 事故恢复方案、P5 是否顺延 → `current/open-questions.md`；风险 `current/risks.md`。
- 爬虫运行时选型（FC+Lua/WASM vs 单进程宿主）→ `knowledge/architecture-站点爬虫运行时方案对比.md`

## 8. 怎么找记忆文件

不要通读 `01-index.md`（脚本生成物，检索用脚本更全）。用 `scripts/mem/mem.py`（README 同目录）：

1. `boot` —— 启动包（hook 已注入则跳过）。
2. `search <关键词>` —— 全库检索定位候选文件。
3. `outline <文件>` —— 只看章节标题，判断该读哪一段。
4. `body <文件> --section <标题>` —— 只读那一段，不要整篇读。
5. 历史变更看 `current/changelog.md`。
