---
title: 项目总览
type: overview
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-14T10:30:00+08:00
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

- 09-13 **转存下载链路空转不可用**：阿里 3 在队账号 token 全失效、百度 0 可用；体检脚本 `scripts/dl_chain_health.sh` → `knowledge/domain-转存下载链路.md`
- 09-13 **新版 FC Chrome 上线**（`nc-app-prod-cdp3`，`/cdp3/*`）；**14:30 挂 NAS**（`app-20260913k`）：`CDP3DATA=/mnt/nas/apps/cdp3`、`CDP3TEMP`、`extensions=`、`profile=ns/name`（调用方须发 `Browser.close`）。→ `decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md`
- 09-12 22:17 **🔴 事故：lifecycle_checker 把资源 md5 当分享 id，115.5 万条有效资源（quark/ali）被误判失效并从新旧索引删除**。修复 `b888846` + bnd「违规」tooltip 误判修复 `06ef50d` **23:11 已部署 checker**；**Mongo 无数据，恢复只能重爬**：`tools/lc-recrawl` 09-14 08:47 投完，回库 63.8 万（≈55%，其余网盘侧本就失效），ali 尾部排队中。→ `lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`、`current/open-questions.md`
- 09-12 `:cur` 两窗口不搬；阶段 D 改 API 侧自动灰度分流（开发中）；A' 进度见 `current/tasks.md`。→ `decisions/decision-2026-09-12-阶段D改由API侧自动灰度分流.md`
- 09-12 16:34 **P5 阶段 A/B 已上线**（D1 钩子；API v2 valid 上报 lc；bnd 去 `has_child`）；顺序：阶段 C 复测 → A' → 阶段 D。→ `decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md`
- 阻塞：无；重爬进行中；风险见 `current/risks.md` R9。

## 3. 核心事实

- 仓库（磁盘名 ≠ module 名）：COMMON `enfi-resource-common`、SPIDER `osec-spider-go`→`enfi-spider-go`、API `osec-resource-api`→`enfi-resource-api`、STORAGE、NC-JS。→ `03-project-context.md`
- COMMON 是唯一契约中心，`.proto` 与生成代码都在 `rpc/`，**改协议先改 COMMON**。→ `knowledge/api-rpc契约.md`
- 主链路：爬虫 → 网关调度（Redis 队列）→ `storage.UpsertResource` → STORAGE → 异步 worker → ES → API。→ `knowledge/architecture-系统总览.md`
- 只处理 4 种网盘 `bnd`/`ali-share`/`quark`/`xunleipan`；磁力已停采，不得调 `SaveMagnetResource`。→ `decisions/decision-2026-09-02-停止磁力资源采集.md`
- 有效性检测 **API/SPIDER 两套独立实现**，改判定要同时改；判失效会不可逆删 ES，**未知响应一律报错**。→ `knowledge/domain-网盘有效性检测.md`
- **爬虫一律走 IP 代理池**，禁止本机直连；本地链路与两个坑见 `lessons/success-本地代理池打通.md`。反爬站门槛：单 IP ≥10 条/分钟。
- 保活 `keepalive` 只在 `CommitResLink` 返回 nil 时续期。→ `lessons/success-爬虫保活语义.md`
- 全站扫描**禁止启动即全量**（redis 记完成时间跳过）；5 个存量爬虫待改造，`feikuai` 合规。→ `decisions/decision-2026-09-03-全站扫描不在启动时触发.md`
- 部署用 SPIDER 的 `deploy.sh`（ssh+docker，主机 osec-res1/res2/resdb/restest/resngix/jenkins）；**现役服务只能用 `./deploy.sh ps` 判断**。→ `procedures/workflow-部署.md`
- NC-JS 是后台前端（qiankun + spiderAdmin 等 3 子应用），**不调 API 仓库 HTTP**，走 WebRTC 上的 gRPC 直连网关 `:7542`；鉴权已改 GitHub OAuth，RtcToken 降为兜底。→ `knowledge/architecture-nc-js.md`
- 前端「环境选择」默认值必须由 `location.hostname` 推导。→ `lessons/failure-前端环境默认值写死本地.md`

## 4. 用户与协作偏好

- 全中文输出（展示/注释/记忆）；有复用价值的脚本落盘写文档，按路径调用省 token。
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
- 跨包重构切三阶段，hub 代码主控逐行审 → `lessons/patterns-并行重构的分阶段切分.md`
- 失效判定看业务码不看文案，判不准就报错；样本 15 条起 → `lessons/success-网盘失效判定原则.md`
- 监控/埋点初始化必须可降级，且要覆盖最彻底的失败路径 → `lessons/failure-旁路能力初始化拖垮主流程.md`
- 前端验收跑一次清空 localStorage 的首访 + 桩网关/CDP 联调 → `lessons/success-桩网关加cdp浏览器做登录链路联调.md`
- 收到「拆分/隔离」需求先复述拆的对象，护栏应做在编译期 → `lessons/failure-把拆配置理解成拆文件.md`
- NC-JS `pnpm build` 会真实上传生产 OSS，验证前先关 `deploy` → `lessons/failure-ncjs构建脚本会自动上传OSS.md`
- **FC 上 WebSocket 断开即冻结实例，收尾/写回必须在连接内做（拦截 `Browser.close`）** → `lessons/failure-FC实例在WebSocket断开后立即冻结.md`
- 新站点调研先挖 JS bundle 接口、`total` 须用 sitemap 对账；**结论有保质期** → `procedures/workflow-新站点调研.md`
- 生产 API 探针按 res-api 三级漏桶算节奏；排序差异用 `explain` 看 idf → `lessons/failure-v3首页重合度受前缀展开分片彩票影响.md`

## 7. 待解决问题

- 事故止血/部署/恢复方案（人工 + 决策）→ `current/open-questions.md`；恢复期间 P5 是否顺延；风险 `current/risks.md`。

## 8. 怎么找记忆文件

不要通读 `01-index.md`（它是 `mem.py` 生成的索引产物，不是正本，检索用脚本更全）。用 `scripts/mem/mem.py`（文档同目录 README）：

1. `boot` —— 列出本次会话该常驻的启动包（若 hook 已注入则跳过）。
2. `search <关键词>` —— 全库检索定位候选文件。
3. `outline <文件>` —— 只看章节标题，判断该读哪一段。
4. `body <文件> --section <标题>` —— 只读那一段，不要整篇读。
5. 历史变更（哪天做了什么）在 `current/changelog.md`，不在本文件。
