---
title: 项目总览
type: overview
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T16:55:00+08:00
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

- 09-12 **进行中：记忆系统瘦身**——常驻 5.4 万字超规则，`scripts/mem/mem.py` 已可用，协议改动待确认。→ `decisions/decision-2026-09-12-记忆系统瘦身与脚本化加载.md`
- 09-12 16:34 **P5 阶段 A/B 已上线**（D1 旧链路失效同步钩子；API v2 valid 上报 lc；bnd 去 `has_child` 后 v3 热态反超 v2 2×）；09-13 起 24 h 观察 → 阶段 C 复测 → A' 存量 → 阶段 D 切流。→ `decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md`、`current/tasks.md`「进行中」
- 09-11 **P4 bootstrap id=8 已 done**（终态对拍 0.001% 级）；遗留 2 个 `:cur` 窗口（5 个未部署提交已随 09-12 网关重部生效）。→ `current/tasks.md`
- 09-10 **代理池监控上线闭环**——全 0 是上报侧未部署，重部即有数据；新增只读巡检 `tools/proxy-admin-check`。→ `procedures/troubleshooting-代理池总览无数据.md`
- 09-09 **配置按进程拆代码已部署**（SPIDER `883daeb`，网关双机 + 爬虫 + proxy 全重部）。→ `decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`
- 阻塞：无；四个 Go 仓库 `go build ./...` 全过；在办任务见 `current/tasks.md`，风险见 `current/risks.md`。

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

- 跨包重构切三阶段，hub 代码主控逐行审 → `lessons/patterns-并行重构的分阶段切分.md`
- 失效判定看业务码不看文案，判不准就报错；样本 15 条起 → `lessons/success-网盘失效判定原则.md`
- 监控/埋点初始化必须可降级，且要覆盖最彻底的失败路径 → `lessons/failure-旁路能力初始化拖垮主流程.md`
- 前端验收跑一次清空 localStorage 的首访 + 桩网关/CDP 联调 → `lessons/success-桩网关加cdp浏览器做登录链路联调.md`
- RTC-gRPC 错误通道会丢附加字段，结构化信息走专门回调 → `lessons/failure-握手回包附加字段被传输层丢弃.md`
- 收到「拆分/隔离」需求先复述拆的对象，护栏应做在编译期 → `lessons/failure-把拆配置理解成拆文件.md`
- NC-JS `pnpm build` 会真实上传生产 OSS，验证前先关 `deploy` → `lessons/failure-ncjs构建脚本会自动上传OSS.md`
- 长周期生产作业巡检清单 → `lessons/patterns-长周期生产巡检.md`（实测吞吐数据 `knowledge/domain-bootstrap吞吐实测数据.md`）
- 新爬虫写联网集成测试（假 committer + 独立 redis 前缀 + 环境变量开关）→ `lessons/success-爬虫联网集成测试.md`
- 新站点调研先挖 JS bundle 接口、`total` 须用 sitemap 对账；**结论有保质期** → `procedures/workflow-新站点调研.md`
- 生产 API 探针按 res-api 三级漏桶算节奏、不伪造来源头；排序差异用 `explain` 看 idf 求和项 → `lessons/failure-v3首页重合度受前缀展开分片彩票影响.md`
- 部署半完成态（容器已删未重建）用 `deploy.sh call redeployHost <svc> <host>` 补救，别用 `call dockerRun`（缺 OSS 配置注入）→ `procedures/workflow-部署.md`

## 7. 待解决问题

- P5 阶段 A' 存量复检节奏、阶段 D 调用方切流对接待确认→ `current/open-questions.md`、`current/tasks.md`；风险 `current/risks.md`。

## 8. 怎么找记忆文件

不要通读 `01-index.md`（它是 `mem.py` 生成的索引产物，不是正本，检索用脚本更全）。用 `scripts/mem/mem.py`（文档同目录 README）：

1. `boot` —— 列出本次会话该常驻的启动包（若 hook 已注入则跳过）。
2. `search <关键词>` —— 全库检索定位候选文件。
3. `outline <文件>` —— 只看章节标题，判断该读哪一段。
4. `body <文件> --section <标题>` —— 只读那一段，不要整篇读。
5. 历史变更（哪天做了什么）在 `current/changelog.md`，不在本文件。
