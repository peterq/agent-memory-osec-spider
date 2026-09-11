---
title: 记忆索引
type: index
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T07:00:00+08:00
priority: critical
keywords: [索引, 关键词, 导航]
summary: 按关键词与主题定位记忆文件，先看概要再决定是否读正文
load: always
related:
  - agent-memory/00-overview.md
---

# 记忆索引

## 使用方法

先用下面的"关键词索引"定位候选文件，再读正文。`load: always` 的只有 `00-overview.md` 和本文件。

## 文件索引

| 文件 | 类型 | 状态 | 关键词 | 概要 | 更新 |
|---|---|---|---|---|---|
| `00-overview.md` | overview | active | 总览、四仓库、当前状态 | 最小可用上下文 | 2026-09-09 |
| `01-index.md` | index | active | 索引、导航 | 本文件 | 2026-09-02 |
| `02-user-preferences.md` | preference | active | 中文、脚本沉淀、记忆维护 | 用户硬性要求与工作习惯 | 2026-09-02 |
| `03-project-context.md` | context | active | 仓库、module、replace、依赖、NC-JS | 五仓库（4 Go + 1 前端）职责与 go.mod 现状 | 2026-09-04 |
| `knowledge/architecture-es索引现状.md` | knowledge | active | ES 6.7、单索引、join 父子、无join、百度存量、墓碑、容量、增速、es_survey | 生产 ES/MySQL 实测基线与读写清理链路代码位置 | 2026-09-05 |
| `decisions/decision-2026-09-04-资源索引生命周期改造方案.md` | decision | active | 生命周期、三索引、res_lc_all、分表、v3、双写、bootstrap | 三索引 + 元数据库替代单大索引的拍板要点与异议裁定 | 2026-09-05 |
| `sessions/2026/2026-09-07-资源生命周期架构图.md` | session | active | 生命周期、架构图、archify、资源视角、服务端视角 | 用 archify 产出两视角 HTML 图，落盘 SPIDER PRD/res-lifecycle/diagrams/ | 2026-09-07 |
| `sessions/2026/2026-09-04-资源生命周期改造PRD.md` | session | active | 生命周期、PRD、Opus、Sonnet、核验、无join | 调研→方案→撰写→核验全程与经验 | 2026-09-05 |
| `sessions/2026/2026-09-05-生命周期五分支合并.md` | session | active | 生命周期、分支合并、lifecycle-gateway、lifecycle-checker、lifecycle-dual-write、lifecycle-v3、lifecycle-admin、config.go冲突 | Wave 1 五分支本地合并进各仓库主干的过程、唯一冲突点与验证结果(均未push) | 2026-09-05 |
| `sessions/2026/2026-09-05-生命周期改造实施.md` | session | active | 生命周期、实施、并行开发、验收、部署拦截 | 五仓库代码落地全程与部署阻塞 | 2026-09-05 |
| `sessions/2026/2026-09-05-生命周期P3上线.md` | session | active | 生命周期、P3、双写、dual_write_legacy、API v3、ReportUpsert、osec-resdb、es_endpoint | P3 上线全程：网关双机双写与 API v3 成功、resdb worker fail-fast 回滚 | 2026-09-05 |
| `sessions/2026/2026-09-05-生命周期P4启动失败.md` | session | active | 生命周期、P4、bootstrap、STORAGE重部、继承字段、lc-backfill-legacy、lc-check | STORAGE 重部+双写窗口补齐 3551 条+P4 bootstrap 启动 10 分钟后失败并停止 | 2026-09-05 |
| `lessons/failure-bootstrap按id排序打爆ES堆.md` | lesson | active | bootstrap、sort _id、fielddata、熔断器、heap、Error 1390、占位符、BatchUpsert | P4 两个阻塞缺陷：按 `_id` 排序翻页打爆 ES 堆 / 批量 upsert 超 MySQL 占位符上限 | 2026-09-05 |
| `lessons/failure-copy_child小reindex被轮询间隔拖垮.md` | lesson | active | bootstrap、copy_child、reindexPollInterval、_reindex、轮询间隔、吞吐、测试替身屏蔽缺陷 | P4 第三个缺陷：每 200 个父 id 一次小 `_reindex` 却按 10 s 轮询，22 s/批 → 全量 20 天 | 2026-09-05 |
| `lessons/failure-临时表排序规则不一致导致JOIN报错.md` | lesson | active | MySQL、collation、ERROR 1267、Illegal mix of collations、临时表、utf8mb4_general_ci、utf8mb4_0900_ai_ci、生产回滚脚本 | MySQL 8 里临时表不写 COLLATE 会继承服务器默认 0900_ai_ci, 与 general_ci 的业务表 JOIN 报 ERROR 1267; dry-run 只跑 SELECT 验证不了写路径 | 2026-09-06 |
| `lessons/failure-copy_child计数校验对称差误判重跑.md` | lesson | active | bootstrap、copy_child、childCountOk、version_conflicts、重跑 | 计数校验对称差误判导致整窗白跑，判据应只看短缺 | 2026-09-07 |
| `lessons/failure-配置v2二进制无本地回落导致老容器重启即挂.md` | lesson | active | 配置 v2、OSS_CONFIG_URL、crash-loop、deploy.sh、set -e 、OSS html 强制下载、srcdoc | v2 无本地回落，同机未重部容器重启即挂；部署半完成态 | 2026-09-10 |
| `lessons/failure-copy_child真正瓶颈是子文档量.md` | lesson | active | copy_child、reindex 限速、requests_per_second、子文档、file_count、量纲估算、slices 不均 | 修完轮询后只快 2.1 倍：真正的工作量是 3245 万子文档/单月、7.4 亿/全量，被 2000 rps 限速卡住 | 2026-09-05 |
| `sessions/2026/2026-09-05-生命周期P4第三次尝试.md` | session | active | P4、fbddacb、网关重部、resume、作业id4、复测未达标、失败即停 | 网关重部到修复 3 成功且零损伤；单月 copy_child 复测未达标，拿到子文档量纲后再次暂停，全量未启动 | 2026-09-05 |
| `lessons/failure-resdb的ES端点指向已下线集群.md` | lesson | active | osec-resdb、es_endpoint、ES 集群更换、fail-fast、哑故障、部署前置检查 | 各机 config.yaml 不一致导致 fail-fast，以及哑故障的识别方法 | 2026-09-05 |
| `knowledge/architecture-系统总览.md` | knowledge | active | 架构、数据链路、端口、中间件 | 爬取→入库→检索全链路 | 2026-09-02 |
| `knowledge/architecture-spider.md` | knowledge | active | SPIDER、子命令、gateway、队列 | 爬虫仓库结构与已知编译问题 | 2026-09-02 |
| `knowledge/architecture-storage.md` | knowledge | active | STORAGE、ES 索引、幂等、version | 存储服务与写入策略 | 2026-09-02 |
| `knowledge/architecture-api.md` | knowledge | active | API、gin、路由、限流 | HTTP 查询服务 | 2026-09-02 |
| `knowledge/architecture-nc-js.md` | knowledge | active | NC-JS、前端、qiankun、微前端、Vue3、TSX、ant-design-vue、WebRTC、protobuf-ts、spiderAdmin、架构图页、syncDiagrams、GitHub OAuth、登录门、OSS html 强制下载、srcdoc | 前端 mono repo 分包/微前端注册/网关对接(鉴权已改GitHub OAuth未部署)/新增页面落点/架构图页与构建时同步 | 2026-09-10 |
| `knowledge/api-rpc契约.md` | knowledge | active | proto、gRPC、契约、protoc | 所有 RPC 方法与消息 | 2026-09-02 |
| `knowledge/architecture-queue-admin.md` | knowledge | active | queue-admin、队列监控、7542、抢主锁、schema、巡检 | 队列监控管理系统(已并入网关)架构/端口/机制/缺口 | 2026-09-08 |
| `decisions/decision-2026-09-04-管理服务并入网关.md` | decision | active | 进程合并、queue_admin、网关、dlock、抢主锁、pushgateway覆盖 | 管理类服务并入 spider_gateway，日后不新增进程 | 2026-09-04 |
| `decisions/decision-2026-09-04-前端合并为spiderAdmin.md` | decision | active | spiderAdmin、子应用合并、布局、apps.json | 两个后台子应用合并、左侧栏布局、一条 RTC 连接 | 2026-09-04 |
| `sessions/2026/2026-09-04-管理服务并入网关与前端合并.md` | session | active | 进程合并、spiderAdmin、抢主锁、LazyKeepAlive | 合并全程、四条关键发现与经验 | 2026-09-04 |
| `sessions/2026/2026-09-04-队列监控系统queue-admin.md` | session | active | queue-admin、全流程、验收、上线 | PRD→并行开发→验收→上线全程与经验 | 2026-09-04 |
| `knowledge/concept-术语表.md` | knowledge | active | bnd、valid、version、命名 | 缩写与字段语义 | 2026-09-02 |
| `procedures/workflow-本地构建与验证.md` | procedure | active | go build、编译失败、protoc | 各仓库可编译状态与修复思路 | 2026-09-02 |
| `procedures/troubleshooting-代理池总览无数据.md` | procedure | active | 代理池总览、proxy_admin、proxyMon、dataSource、无数据、上报侧未部署 | 代理池页全 0 的三步定位 + proxy-admin-check 工具；09-10 上报侧已全部重部解决 | 2026-09-10 |
| `procedures/workflow-部署.md` | procedure | active | deploy.sh、docker、ssh、OSS | 生产部署与配置分发 | 2026-09-02 |
| `procedures/workflow-站点发现.md` | procedure | active | 站点发现, site-discovery, 常态化任务 | 找新资源站的入口与三条铁律，正文在 site-discovery/README.md | 2026-09-03 |
| `sessions/2026/2026-09-03-站点发现任务首轮.md` | session | active | 站点发现, 工具集, 41031, 首轮结果 | 任务落地过程与首轮 6 个达标站点 | 2026-09-03 |
| `sessions/2026/2026-09-03-并行开发6站爬虫.md` | session | active | 并行开发, worktree, 6站爬虫, 合并 | 6 站接入过程、5 站验收通过、haisou 缺口 | 2026-09-03 |
| `procedures/workflow-新站点调研.md` | procedure | active | 站点调研、PRD、公开API、分页陷阱 | 调研资源站并产出 PRD 的标准步骤 | 2026-09-02 |
| `knowledge/domain-站点-kkpans.md` | knowledge | active | kkpans、KK网盘、公开API、光鸭云盘 | kkpans 接口/坑/规模/采集范围/实现状态 | 2026-09-02 |
| `knowledge/domain-站点-misoso.md` | knowledge | active | misoso、melost.cn、域名不一致、sitemap陷阱、越界文件假200 | misoso 域名/sitemap 两层陷阱、626万规模、实现状态 | 2026-09-03 |
| `knowledge/domain-站点-2609接入批次.md` | knowledge | active | dyyjmax、fuxipan、feikuai、kuakes、haisou、Flarum、苹果CMS、magicpost | 本批 5 站的形态/子命令/坑/实现状态 | 2026-09-03 |
| `procedures/workflow-并行开发多站点爬虫.md` | procedure | active | 并行开发、worktree、子agent、合并冲突 | 多站点同时接入的分工、冲突收敛与合并流程 | 2026-09-03 |
| `procedures/workflow-子agent任务简报.md` | procedure | active | 子agent、任务描述、agent-tasks、简报、token、prompt | 任务描述落盘成文件、prompt 只给路径，避免重复上下文 | 2026-09-08 |
| `lessons/failure-proto3零值与负一哨兵冲突.md` | lesson | active | proto3、零值、哨兵、-1、不过滤、筛选参数、静默空结果 | 0 是合法业务值时用 -1 当"不过滤"哨兵，前端漏传会静默查错数据 | 2026-09-08 |
| `decisions/decision-2026-09-08-后台登录改为github-oauth.md` | decision | active | GitHub OAuth、后台登录、RtcToken、OAuth App、client_id、allow_rtc_token | 固定管理秘钥改 GitHub OAuth 登录的四个关键设计取舍 | 2026-09-08 |
| `lessons/failure-握手回包附加字段被传输层丢弃.md` | lesson | active | RtcTransport、cancelAllPendingCalls、UnaryCallResponse、needLogin、githubClientId、重试覆盖错误信息 | 握手403回包业务字段被RTC传输层统一取消路径丢弃；附带登录失败原因被重试覆盖的关联问题 | 2026-09-08 |
| `lessons/success-桩网关加cdp浏览器做登录链路联调.md` | lesson | active | 桩网关、stubgw、CDP、agent-browser、浏览器联调、验收方法论 | 只保留被测链路的桩服务+带登录态调试浏览器做端到端验收 | 2026-09-08 |
| `procedures/workflow-带登录态的浏览器自动化.md` | procedure | active | agent-browser、cdp.py、CDP、调试浏览器、user-data-dir | 启动/复用调试Chrome并用CDP驱动的用法与前提坑 | 2026-09-08 |
| `knowledge/reference-github-oauth配置.md` | knowledge | active | GitHub OAuth App、client_id、redirect_uri、1second 组织 | 两个OAuth App的名称/client_id/管理页/回调列表(不含secret) | 2026-09-08 |
| `lessons/success-配置v2上线准备发现的两个衔接问题.md` | lesson | active | 配置v2、github_auth、spider.gateway.prod.yaml、oss.last、uploadConfigToOss | config_show 掩盖"父节点缺失"、README 首次上传步骤与代码相反 | 2026-09-08 |
| `sessions/2026/2026-09-08-后台登录改为github授权.md` | session | active | GitHub OAuth、后台登录、握手协议、桩网关 | 登录改造全程：协议设计→三仓库开发→两轮联调发现修复→未部署 | 2026-09-08 |
| `decisions/decision-2026-09-09-配置按进程拆代码而非文件.md` | decision | active | 配置拆分、拆代码、角色包、config/gateway、config/crawler、构建 tag、单文件 | 用户纠正后的配置隔离方案: 每进程自己的根结构体+惰性 Get, 无全局 Config, 文件保持一份 | 2026-09-09 |
| `lessons/failure-把拆配置理解成拆文件.md` | lesson | active | 需求理解、复述确认、拆分对象、运行时断言、层级选错 | "拆分"先确认拆的是什么; 写运行时护栏/文件里不写某项 = 层级选错 | 2026-09-09 |
| `sessions/2026/2026-09-10-代理池监控上线.md` | session | active | 代理池总览、proxy-monitor、上报侧未部署、分批重部、proxy-admin-check | 排查全 0 → 重部 proxy + 20 个爬虫 service → 20 个场景有数据 | 2026-09-10 |
| `sessions/2026/2026-09-08-并行四任务监控与文档爬虫上云.md` | session | active | 并行四任务、告警后台、代理池监控、链接追踪、doc-crawler、fc-chrome、Phase 0、worktree | 一次会话并行完成四件需求的全过程、Phase 0 做法与三层复核发现 | 2026-09-09 |
| `lessons/failure-旁路能力初始化拖垮主流程.md` | lesson | active | db.Redis、log.Fatal、panic、监控初始化、降级、埋点覆盖、nil 回调 | 用会 Fatal/panic 的基础设施初始化旁路监控会让每个子命令一起死; 埋点只覆盖成功路径让故障隐形 | 2026-09-09 |
| `sessions/2026/2026-09-08-res_lc数据纳入后台.md` | session | active | res_lc、管理后台、只读、分表浏览、表诊断、并行开发 | 四个只读接口+四个页面落地全程与三层复核经验 | 2026-09-08 |
| `lessons/failure-haisou搜索接口收紧.md` | lesson | active | haisou、13001、限流、调研结论过期、代理网段、积分、X-HS-Client-Context、FingerprintJS | 搜索端点对代理池 IP 全量429；已排除积分/请求头/HTTP2/会话/匿名身份，锁定为按来源网络的端点级拦截 | 2026-09-03 |
| `lessons/failure-按进程数分配主机压垮restest.md` | lesson | active | 部署、主机分配、负载、sshd失联、restest | 只数 spider 进程低估负载，压垮 restest 20 分钟 | 2026-09-03 |
| `knowledge/domain-网盘有效性检测.md` | knowledge | active | 有效性检测、validShareLink、失效、业务码、限流 | 两套 checker 位置、各网盘失效码表、联网自测 | 2026-09-02 |
| `lessons/success-本地代理池打通.md` | lesson | active | 代理池, 蜻蜓, 白名单, 出口IP, redis-topic-sync | 本地怎么用上代理池与三个查错方向的坑 | 2026-09-03 |
| `lessons/success-爬虫联网集成测试.md` | lesson | active | 集成测试、爬虫、假committer、键前缀 | 可复跑且不污染线上的爬虫联网测试写法 | 2026-09-02 |
| `lessons/success-爬虫保活语义.md` | lesson | active | keepalive、保活、CommitResLink、AfterFunc、nil channel | 保活只在提交成功时续期，及 keepalive 挂死隐患修复 | 2026-09-03 |
| `lessons/success-网盘失效判定原则.md` | lesson | active | 失效判定、业务码、限流、误删 | 业务码优先、限流≠失效、未知就报错 | 2026-09-02 |
| `decisions/decision-2026-09-02-停止磁力资源采集.md` | decision | active | 磁力、magnet、采集范围、网盘类型 | 只采 4 种网盘类型，磁力停采 | 2026-09-02 |
| `decisions/decision-2026-09-03-全站扫描不在启动时触发.md` | decision | active | 全站扫描、全量、启动、redis、重启 | 全量完成时间存 redis，启动检查后跳过 | 2026-09-03 |
| `decisions/decision-2026-09-03-清理下线爬虫代码.md` | decision | active | 清理、下线爬虫、deploy.sh ps、死代码 | 按线上进程删掉 21 个爬虫命令及配置，附遗留问题清单 | 2026-09-03 |
| `decisions/decision-2026-09-03-下线haisou.md` | decision | active | haisou、下线、13001、端点级拦截、放弃站点 | 为什么放弃 haisou 及具体处置动作 | 2026-09-03 |
| `decisions/decision-2026-09-04-队列v2统一走网关.md` | decision | active | 队列v2、queue_task、res_scheduler、resourcePreCheck、关键词扇出 | 跨进程任务投递统一走网关队列的方案取舍与实施状态(已完成) | 2026-09-04 |
| `decisions/decision-2026-09-04-合并sweep-guard分支冲突取舍.md` | decision | active | sweep-guard、merge 冲突、keepalive、runRound、全量扫描守卫 | 合并遗留分支时，master 已修正的旧逻辑不因"两边全保留"被恢复 | 2026-09-04 |
| `decisions/decision-2026-09-06-全量bootstrap熔断后原地resume.md` | decision | active | bootstrap、熔断、resume、窗口固定开销 | id=8 吞吐熔断后原地 resume 的依据与修订熔断条款 | 2026-09-06 |
| `decisions/decision-2026-09-06-全量bootstrap动态rps守护续跑.md` | decision | active | bootstrap、v2 延迟、动态 rps、守护、rethrottle | 熔断后 rps 2500 起步 + 动态峰值守护续跑的算法与安全边界 | 2026-09-06 |
| `sessions/2026/2026-09-04-队列v2改造.md` | session | active | 队列v2、并行子agent、sonnet、Phase0/1/2、上线顺序 | 队列 v2 升级全程：契约、6 个并行 Agent、合并、清理、后续上线步骤 | 2026-09-04 |
| `sessions/2026/2026-09-04-队列v2改造收尾清理.md` | session | active | 队列v2、清理、CommitResLink、StartQueueRemoteConsumer | Phase 2 清理 Agent 的过程细节 | 2026-09-04 |
| `sessions/2026/2026-09-04-队列监控前端开发.md` | session | active | NC-JS、队列监控、schema渲染器、queue_admin、mock | 在 resSpiderScheduler 加队列监控 Tab 的实现过程与决策(**目录已并入 spiderAdmin**) | 2026-09-04 |
| `lessons/failure-ncjs构建脚本会自动上传OSS.md` | lesson | active | NC-JS、pnpm build、mfe插件、OSS部署 | 标准 build 脚本默认会真实部署到生产 OSS, 验证前要关掉 | 2026-09-04 |
| `lessons/failure-前端环境默认值写死本地.md` | lesson | active | gwEndpoint、gwAddrs、defaultGwAddr、正在连接服务器、本地环境 | 网关地址默认值写死本地下标导致生产首次访问卡死, 改为按 hostname 自动选择 | 2026-09-08 |
| `lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md` | lesson | active | qiankun、initMicroFeApp、Vue mount、qiankun-head、样式丢失、antd Layout header、无头 Chrome | 子应用挂包裹层致线上 CSS 被清空 + antd 两级选择器压过单类名, 附 dump-dom 核对法 | 2026-09-08 |
| `sessions/2026/2026-09-08-spiderAdmin样式修复.md` | session | active | spiderAdmin、样式丢失、header 深色、生产部署 | 两个样式根因定位→修复→OSS 重发→线上 DOM 复核全程 | 2026-09-08 |
| `lessons/failure-antdv-Row-字符串style.md` | lesson | active | ant-design-vue、Row、style 字符串、CSSStyleDeclaration、前端报错 | antdv 的 Row/Menu.Item 用 Object.assign 合并 style, 传字符串会运行时报索引属性错 | 2026-09-04 |
| `lessons/failure-网关重启暴露ES集群已更换.md` | lesson | active | 网关、ES、集群更换、配置过期、长期不重启、重启前检查 | 重启网关暴露 ES 配置指向死集群；重启前逐项验证外部依赖 | 2026-09-04 |
| `lessons/success-archify画图的几何约束.md` | lesson | active | archify、lifecycle、viewBox、宽高比、visual-check | archify 固定布局规则与修到双过的顺序 | 2026-09-07 |
| `lessons/success-生命周期改造验收发现.md` | lesson | active | 验收、refresh、BatchUpsert !id、recover、幂等、别名判据 | 端到端验收抓出的 5 类阻塞/重要缺陷与写法规则 | 2026-09-05 |
| `lessons/patterns-统计ES索引先查文档形态.md` | lesson | active | ES、join、nested、must_not exists、统计漏算 | 同一索引混两代形态，统计/迁移前先做形态对账 | 2026-09-05 |
| `lessons/patterns-长周期生产巡检.md` | lesson | active | 巡检、子Agent、隧道、keepalive、_count 差分 | 数小时生产巡检的 4 条硬经验与实测吞吐 | 2026-09-06 |
| `lessons/patterns-并行重构的分阶段切分.md` | lesson | active | 并行重构、子agent、worktree、编译互锁、三阶段 | 跨包重构如何切成能并行的子 Agent 任务 | 2026-09-04 |
| `lessons/failure-longBoundary漂移导致父子跨索引与shortfall误报.md` | lesson | active | longBoundary、shortfall、has_parent、copyMode=ids、mover、TriggerMove | 长跑 bootstrap 边界漂移致父子跨索引，shortfall 全为误报；copyMode=ids 禁用，修法 mover 父归位 | 2026-09-11 |
| `current/tasks.md` | task | active | 任务、待办、生命周期、bootstrap、id=8 | 待办清单（最上方为生命周期 P4 全量 bootstrap 巡检） | 2026-09-09 |
| `current/risks.md` | risk | active | 风险、密钥、生产测试 | 5 项已知风险 | 2026-09-02 |
| `current/open-questions.md` | question | active | 疑问、待确认、生命周期 Q1~Q6 | 生命周期改造 PRD 的 6 个待用户确认问题 | 2026-09-05 |
| `sessions/2026/2026-09-02-初始化记忆体系.md` | session | active | 首次会话、架构调研 | 初始化过程与经验 | 2026-09-02 |
| `sessions/2026/2026-09-02-重命名收尾与修复编译.md` | session | active | 重命名、go.mod、编译修复 | PPIO→1s 收尾与两处编译错误修复 | 2026-09-02 |
| `sessions/2026/2026-09-02-kkpans站点调研与PRD.md` | session | active | kkpans、站点调研、PRD | 调研过程与关键发现 | 2026-09-02 |
| `sessions/2026/2026-09-02-kkpans爬虫开发.md` | session | active | kkpans、bbs_kkpans、爬虫开发 | 按 PRD 实现并实测通过 | 2026-09-02 |
| `sessions/2026/2026-09-02-修复夸克阿里有效性检测.md` | session | active | 有效性检测、夸克、阿里、41004、限流 | 复现并修复三类误判，两套实现结论对齐 | 2026-09-02 |

## 关键词索引

### 配置怎么读 / 某个进程读哪些配置 / config.Config 去哪了 / 网关为什么拿不到 spider_gateway
→ `decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`; 代码 `osec-spider-go/config/`(根包注释是入口),
角色包 `config/{gateway,crawler,proxyprov,lifecyclechecker,doccrawler,devops,downloader}`, 隔离检查
`scripts/check_config_isolation.sh`, 看某角色实际读到什么 `./spider config_show <角色>`。
配置文件只有一份 `res/spider.prod.yaml`; 合并/反向脚本 `scripts/config_v2_merge_by_service.py`。

### 队列告警怎么配 / 失败率窗口和阈值 / 告警历史在哪看 / 告警为什么没发
→ `services/gateway/queue_admin/alert.go`(引擎与 6 条规则)、`alert_rules.go`(按队列覆盖, redis hash + 30s 热同步)、
`alert_history.go`(历史落 redis, 7 天/2000 条)、`alert_logs.go`(触发时抓 SLS 现场日志)、
`fail_window.go`(失败率分钟桶, 数据不足时宁可漏报不误报)。缺省 1h/60%(2026-09-08 由 10min/50% 调整)。
前端: spiderAdmin「队列监控」组的「告警历史」「告警配置」两页。

### 代理池监控 / Scene 是什么 / IP 不可用 vs 被站点封禁 / 推送 IP 数
→ 上报侧 `illuminate/proxy-client/{hook.go,classify.go}`(只暴露 hook, 不含上报逻辑) +
`illuminate/proxy-monitor/`(独立包, 消费端 `Init` 注册; 分钟桶 + 延迟直方图 + HLL 去重);
读取侧 `services/gateway/proxy_admin/`; 契约 `COMMON rpc/spider/proxy_admin_rpc/`。
前端: spiderAdmin「代理池」组两页。加新消费端只需在 `ProxyClient{}` 里填 `Scene:`。
无数据排查 → `procedures/troubleshooting-代理池总览无数据.md`

### 一条链接为什么没入库 / 想看它的完整时间线
→ 后台 spiderAdmin「队列监控 → 链接追踪」页; 后端 `services/gateway/queue_admin/trace.go`。
各阶段日志带 `link_key` 顶层字段, SLS 建索引后可开 `services.queue_admin.sls.link_key_indexed`。

### 云端 Chrome / FC 上跑浏览器 / 装插件或油猴脚本 / 文档爬虫上云
→ `enfi-resource-common/fc-chrome/README.md`(新 FC 实例, 独立嵌套 module)、
`osec-spider-go/services/doc_crawler/`(服务端进程)、
接口契约 `agent-tasks/2026-09-08-monitoring-and-doc-fc/05-doc-fc-contract.md`。
旧实例 `nerve-center/fc-entry`(只读参考)。

### 我要改 gRPC 协议 / proto
→ `knowledge/api-rpc契约.md`，然后 `procedures/workflow-本地构建与验证.md`（生成流程）

### 我要改爬虫 / 加一个站点 / 看某个子命令
→ `knowledge/architecture-spider.md`，部署时 `procedures/workflow-部署.md`

### 我要找新的资源站 / task site-discovery / 启动网站发现任务
→ `procedures/workflow-站点发现.md`（入口），正文流程 `site-discovery/README.md`，
工具 `site-discovery/tools/`（用前必跑 `selftest.py`），已探索站点 `site-discovery/history.md`

### 我要调研一个新的资源站 / 写爬虫 PRD / 找站点的接口
→ `procedures/workflow-新站点调研.md`（通用步骤与必测项），已调研站点见 `knowledge/domain-站点-*.md`

### kkpans / KK网盘 / 光鸭云盘 / guangyapan / bbs_kkpans
→ `knowledge/domain-站点-kkpans.md`，需求文档 `osec-spider-go/PRD/2609/www.kkpans.com.md`（§11 实现落地）
代码：`osec-spider-go/services/bbs/kkpan.com.go`

### dyyjmax / fuxipan / feikuai / kuakes / haisou / bbs_* 新爬虫 / 2609 批次
→ `knowledge/domain-站点-2609接入批次.md`，各站需求文档 `osec-spider-go/PRD/2609/<域名>.md`
代码：`osec-spider-go/services/bbs/`（前 4 站）、`services/haisou/`（haisou）
探测脚本：`osec-spider-go/scripts/<站点>_probe.py`

### 我要一次接入多个站点 / 并行开发 / worktree 怎么分工 / 合并冲突
→ `procedures/workflow-并行开发多站点爬虫.md`
建 worktree 用 `osec-spider-go/scripts/new_worktree.sh <分支名>`

### 队列监控 / queue-admin / 队列出问题了怎么看 / 任务详情 schema / 端口连不上
→ `knowledge/architecture-queue-admin.md`（架构/端口/机制/巡检工具/已知缺口）
**已并入网关进程**（无独立端口/独立 token）：`decisions/decision-2026-09-04-管理服务并入网关.md`
全程与经验：`sessions/2026/2026-09-04-队列监控系统queue-admin.md`
需求：`osec-spider-go/PRD/queue-admin/README.md`；巡检：`osec-spider-go/tools/queue-admin-check/`

### 队列 v2 / queue_task.Service / 旧队列 share_pwd/ad_share/quark_share/xunlei_share/keyword_filter 去哪了 / 怎么上线
→ `decisions/decision-2026-09-04-队列v2统一走网关.md`（方案取舍、目标拓扑、已完成）
全程与上线步骤：`sessions/2026/2026-09-04-队列v2改造.md`；清理细节：`sessions/2026/2026-09-04-队列v2改造收尾清理.md`
队列约定速查：`knowledge/architecture-spider.md`"队列约定"一节

### 我要写新的网关队列消费者 / 关键词站点怎么收关键词 / 爬虫怎么提交链接
→ `knowledge/architecture-spider.md`"队列约定"；辅助代码 `osec-spider-go/services/v2/gw_remote_queue/res_queue_helpers.go`，
参考实现 `services/v2/res_crawler/{bnd,ali,quark,xl}`、关键词站点 `services/keyword/sp2023/funletu.go`

### 网关起不来 / no such host / ES 集群换了 / 重启前要检查什么 / 队列 v2 上线收尾脚本
→ `lessons/failure-网关重启暴露ES集群已更换.md`、`procedures/workflow-部署.md`
收尾脚本：`osec-spider-go/scripts/queue_v2_cutover_finish.sh`（文档同名 `.md`）

### 多个包同时重构 / 子 Agent 编译互锁 / Phase 0-1-2
→ `lessons/patterns-并行重构的分阶段切分.md`
代码：爬虫提交链接统一走 `osec-spider-go/services/spider-common/spider-common.go` 的
`CommitResLink`；关键词/资源消费统一用 `queue_task.StartQueueRemoteConsumer`

### 哪些爬虫还在跑 / 某个爬虫代码去哪了 / 为什么删了 xxx 爬虫 / 想恢复一个老爬虫
→ `decisions/decision-2026-09-03-清理下线爬虫代码.md`（删除清单、连带清理、遗留问题）
判据只有一个：`./deploy.sh ps`。`deploy.sh` 的 `serviceToHosts` 会残留僵尸条目，不可信。
恢复老代码：`cd osec-spider-go && git log --diff-filter=D -- <路径>`

### haisou 为什么下线 / 还能不能复活
→ `decisions/decision-2026-09-03-下线haisou.md`（结论、处置动作、复盘条件）

### haisou 跑不通 / 13001 / 请求过于频繁 / 积分额度 / X-HS-Client-Context / 调研结论和实际对不上
→ `lessons/failure-haisou搜索接口收紧.md`（含两轮归因、积分模型、匿名身份头逆向）
工具：`osec-spider-go/scripts/haisou_probe.py credits|curl`（不耗积分的连通性探针 / 生成可粘贴 curl）、
`osec-spider-go/scripts/haisou_client_context.py`（复刻站点匿名身份头，带自检）、
`osec-spider-go/scripts/haisou_watch.py`（探路 + 邮件通知，**cron 已随下线撤除**，需要时手动跑一次）

### 管理员邮件通知 / cron 任务怎么发通知
→ `POST http://cf-worker.peterq.cn/notify_admin`，body `{"subject","htmlContent","source"}`
参考实现 `osec-spider-go/scripts/haisou_watch.py` 的 `notify()`

### misoso / melost.cn / 影盘社 / bbs_misoso / disk-N.xml / 越界sitemap假200
→ `knowledge/domain-站点-misoso.md`，需求文档 `osec-spider-go/PRD/2609/www.misoso.cc.md`
代码：`osec-spider-go/services/bbs/misoso.cc.go`（分支 `feat/spider-misoso`，未合并未部署）

### 链接失效检测 / validShareLink 返回 -1 / 夸克阿里判定不准 / 误删资源
→ `knowledge/domain-网盘有效性检测.md`（接口与业务码表），判定原则见 `lessons/success-网盘失效判定原则.md`
代码：`osec-resource-api/services/valid/`（对外接口）、`osec-spider-go/services/gateway/valid/`（清理存量）

### 代理池 / 代理连不上 / 蜻蜓白名单 / 出口 IP 不对 / redis-topic-sync
→ `lessons/success-本地代理池打通.md`
代码：`osec-spider-go/services/proxy-provider/`、`site-discovery/tools/proxypool.py`

### 我要给爬虫写测试 / 联网测试怎么不污染线上
→ `lessons/success-爬虫联网集成测试.md`

### 保活 / keepalive / alive() 该在哪调 / 爬虫空跑不告警
→ `lessons/success-爬虫保活语义.md`
代码：`osec-spider-go/illuminate/keepalive/keepalive.go`，各爬虫提交成功处调用

### 新增服务配置节 / yaml 解析 Duration / 线上配置没同步
→ `knowledge/architecture-spider.md`（"写新爬虫时的可复用要点"一节）

### 资源生命周期 / 三索引 / res_lc / 索引轮换 / 失效检测改造 / 生产 ES 有多大 / 怎么查生产 ES / 双写 / v3 / P3 上线 / P4 bootstrap
→ PRD `osec-spider-go/PRD/res-lifecycle/README.md`（唯一需求来源，§14.2 待确认 Q1~Q6），
决策 `decisions/decision-2026-09-04-资源索引生命周期改造方案.md`，事实基线 `knowledge/architecture-es索引现状.md`，
**P4 bootstrap 为什么跑不起来 / 作业 id=1 为什么 failed** → `lessons/failure-bootstrap按id排序打爆ES堆.md`、
`sessions/2026/2026-09-05-生命周期P4启动失败.md`；
**P4 第二次演练 / copy_child 为什么这么慢（轮询空等）** → `lessons/failure-copy_child小reindex被轮询间隔拖垮.md`、
`sessions/2026/2026-09-05-生命周期P4演练.md`，
**P4 第三次尝试 / 作业 id=4 为什么还是 paused / copy_child 修完还是慢 / 要搬多少子文档 / reindex 限速**
→ `lessons/failure-copy_child真正瓶颈是子文档量.md`、`sessions/2026/2026-09-05-生命周期P4第三次尝试.md`，
报告 `osec-spider-go/PRD/res-lifecycle/rollout-2026-09-05.md` §8，
体检脚本 `osec-spider-go/scripts/es_survey.sh`（经 osec-res1 跳板；**同一索引混两代文档形态，统计务必同时查 `must_not exists join`**）

### 我要改入库逻辑 / ES 索引 / 查资源为什么没写进去
→ `knowledge/architecture-storage.md`（幂等与 version 判重是最常见原因）

### 后台怎么看 res_lc_* 分表数据 / 资源列表 / 分表统计 / 事件流水 / 表诊断
→ `sessions/2026/2026-09-08-res_lc数据纳入后台.md`；契约 COMMON `lifecycle.proto` 末尾
「res_lc_* 数据浏览(只读)」一节；后端 SPIDER `services/gateway/lifecycle/browse.go`、
`browse_dao.go`；前端 `nc-js/admin/spiderAdmin/src/pages/lifecycle/`（ResourceListPage /
TableStatsPage / EventListPage / TableDiagnosticsPage）。**已合并已 push，未部署**

### 筛选参数传了 0 却查不出数据 / proto3 不传字段被当成过滤条件
→ `lessons/failure-proto3零值与负一哨兵冲突.md`

### 我要测浏览器可见的交互 / 带登录态的浏览器 / CDP / 桩服务验收 / agent-browser.sh / cdp.py
→ `procedures/workflow-带登录态的浏览器自动化.md`（用法与"默认 profile 会被拦截"的前提坑）、
`lessons/success-桩网关加cdp浏览器做登录链路联调.md`（方法论：只保留被测链路的桩服务 + 真实浏览器）
代码：`COMMON/scripts/agent-browser.sh`、`COMMON/scripts/cdp.py`、`osec-spider-go/tools/stubgw`

### 我要派子 Agent / 任务描述太长 / 多个 agent 上下文重复 / 并行开发怎么分工
→ `procedures/workflow-子agent任务简报.md`（任务描述落盘 `agent-tasks/`，prompt 只给路径）
模板正本：`agent-tasks/README.md`；实例：`agent-tasks/2026-09-08-lifecycle-admin-data/`
多站点爬虫那种 worktree 并行分工另见 `procedures/workflow-并行开发多站点爬虫.md`

### 我要改后台前端 / 加一个后台页面 / qiankun 子应用 / NC ADMIN / apps.json / spiderAdmin
→ **线上样式丢/本地正常、顶栏变深色**：`lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md`（挂载点 + 选择器特异性 + 无头 Chrome 核对）
→ `knowledge/architecture-nc-js.md` §7（分包布局、微前端注册与部署、页面写法、代表性文件路径）
代码：子应用外壳 `nc-js/admin/spiderAdmin/src/layout/AppLayout.tsx`（加一项菜单 = 加一个页面），
队列/任务列表页范本 `nc-js/admin/spiderAdmin/src/pages/doc/comps/queuedTasks.vue`，
共享库 `nc-js/packages/catalyst/`；下线子应用要跑 `admin/spiderAdmin/scripts/removeMfeApps.mjs`

### 前端怎么连后端 / 网关 IP 换了 / 前端 proto 怎么生成
→ `knowledge/architecture-nc-js.md` 第 5 节。后台不走 REST，走 WebRTC DataChannel 上的 gRPC 直连
SPIDER gateway(`115.29.215.228:7542`)。生成 TS 契约：`nc-js/packages/catalyst/scripts/devops/protc_gen.sh`
（**内含已失效的 pplabs 老路径，先改**）

### 后台登录 / GitHub OAuth / 管理秘钥去哪了 / gwToken / RtcToken 兜底 / needLogin / githubClientId
→ **[事实 2026-09-08，未部署] 鉴权已改为 GitHub OAuth（限 1second 组织成员）**，
`RtcToken` 降为可关闭兜底(`allow_rtc_token`)：`decisions/decision-2026-09-08-后台登录改为github-oauth.md`、
`knowledge/architecture-nc-js.md` 第 5 节、`knowledge/reference-github-oauth配置.md`（App 配置，不含 secret）；
握手回包字段传不到前端的坑 → `lessons/failure-握手回包附加字段被传输层丢弃.md`；
全程 `sessions/2026/2026-09-08-后台登录改为github授权.md`

### 我要改查询接口 / 限流 / 搜索
→ `knowledge/architecture-api.md`

### 编译不过 / 依赖报错 / replace 问题 / go mod tidy
→ `procedures/workflow-本地构建与验证.md`、`03-project-context.md`

### 泛型队列 PushTask 怎么写 / GwQueue 类型对不上
→ `knowledge/architecture-spider.md`（"关键类型速查"一节）

### bnd / ali-share / quark / xunleipan 是什么、字段什么意思
→ `knowledge/concept-术语表.md`

### 任务队列怎么消费 / seq / 永久失败
→ `knowledge/concept-术语表.md`（语义）+ `knowledge/architecture-spider.md`（队列定义）

### 部署 / 上线 / 看日志 / 重启 / 确认线上跑着哪些服务 / 新服务放哪台机
→ `procedures/workflow-部署.md`（含"新服务怎么选主机"与各机负载基线）
踩过的坑：`lessons/failure-按进程数分配主机压垮restest.md`

### 密钥、安全
→ `current/risks.md` R2

### 当前该做什么
→ `current/tasks.md`、`current/open-questions.md`

## 尚未创建的目录

`archive/` —— 待产生真实内容时创建，勿提前建空目录。

## 最近更新

0. `03-project-context.md`、`00-overview.md`：**更新**——AGENTS.md/agent-memory/agent-tasks 实体迁至独立仓库 agent-memory-osec-spider，COMMON 内改为软链接，记忆 commit 改在新仓库（2026-09-12 07:00）
0. `current/tasks.md`、`00-overview.md`、`patterns` #96~98、`open-questions`、`sessions/2026-09-11-*`：**更新**——shortfall 父归位 09-12 02:17 完成（102,601 父，对拍 0.001% 级），P4 全部完成，遗留 2 个 :cur 窗口与 5 个未部署提交（2026-09-12 02:40）
0. `00-shared.md`（ES 只读白名单）、`70-move-shortfall.md`（枚举改走 DB）、`patterns` #94~95、`risks`、`tasks`：**更新**——子 Agent 在 legacy 跑 has_child 致节点重启事故（已恢复，零写操作），重派执行（2026-09-11 17:50）
0. `current/tasks.md`、`lessons/failure-longBoundary…`：**更新**——lc-check -trigger-move（aac5f84）与 bootstrap 三处缺陷修复（61cf1db/e856540/93f4d38）已提交未部署；shortfall 父归位 Opus 执行中（2026-09-11 17:00）
0. `lessons/failure-longBoundary漂移…`（新增）、`current/tasks.md`、`00-overview.md`、`open-questions`：**更新**——shortfall 只读分析：零丢失、父留 cur；copyMode=ids 禁用；mover 父归位待用户决策（2026-09-11 12:10）
0. `current/tasks.md`、`00-overview.md`、`patterns` #90~93、`open-questions`：**更新**——id=8 09-11 10:25 done（repair id=10 + retry），遗留 shortfall 补搬待分析（2026-09-11 11:10）
0. `current/tasks.md`：**更新**——bootstrapVerify 两索引汇总失败已修（SPIDER `3b8cc13`，未部署）；恢复执行（cancel id=4→repair→retry）Opus 进行中（2026-09-11 07:25）
0. `current/tasks.md`：**更新**——取证只读脚本已固化（SPIDER `b80d899`，lc_mysql_ro/lc_es_ids_probe/lc_db_lookup + README 对拍小节）（2026-09-11 06:40）
0. `sessions/2026/2026-09-11-p4-bootstrap接管巡检与校验失败取证.md`（新增）、`current/open-questions.md`：**更新**——本会话摘要与 id=8 恢复的 4 项待决策（2026-09-11 06:30）
0. `current/tasks.md`、`patterns` #85~89、`00-overview.md`：**更新**——id=8 校验取证：long 也超标（双索引副本）、cur 零漏搬、推荐 repair→retry 路径与 5 项用户决策；rollout §12 已 push（2026-09-11 06:15）
0. `current/tasks.md`、`00-overview.md`：**更新**——作业 id=8 09-11 05:16 终结 failed（verify 差额 0.107%，别名未切），copy_child 跑满，下一步 repair 定位（2026-09-11 05:35）
0. `current/tasks.md`、`patterns` #83~84、`00-overview.md`：**更新**——第 25 轮巡检：槽 1505/1620，`_count` 被业务删除抵消尾段作废，完成按槽 09-11 05:00~11:00（2026-09-11 00:25）
0. `current/tasks.md`、`patterns` #81~82、`00-overview.md`：**更新**——第 24 轮巡检：进度 83.12%，午后吞吐 1,861，完成校准 09-11 ≈16:20（2026-09-10 19:20）
0. `current/tasks.md`、`patterns` #79~80、`00-overview.md`：**更新**——第 23 轮巡检：进度 80.33%，白天吞吐 2,071（夜间 61%），完成校准 09-11 14:40（2026-09-10 14:15）
0. `current/tasks.md`、`00-overview.md`、`procedures/workflow-部署.md`、`current/open-questions.md`、`sessions/2026/2026-09-10-代理池监控上线.md`：**更新/新增**——代理池监控上报侧（proxy + 20 个爬虫 service）全部重部，20 个场景有数据；新增 `tools/proxy-admin-check`；两个待确认口径问题（2026-09-10 10:10）
0. `procedures/troubleshooting-代理池总览无数据.md`：**新增**——代理池总览全 0 排查三步法；本次结论为上报侧（爬虫容器 + proxy 服务）全部未重部，读取侧正常（2026-09-10 09:30）
0. `current/tasks.md`、`patterns` #77~78、`00-overview.md`：**更新**——第 22 轮巡检：进度 77.12%，早高峰 08:00 后压制 −40%，完成校准 09-11 08:40（2026-09-10 09:05）
0. `knowledge/architecture-nc-js.md`：**更新**——架构图页改为 fetch+srcdoc（OSS html 直连 iframe 会被强制下载，NC-JS `6ce0b9b`），dev 注入行为由推断改为实测（2026-09-10 08:20）
0. `current/tasks.md`、`patterns` #75~76、`00-overview.md`：**更新**——第 21 轮巡检：进度 72.18%，夜间吞吐 3,388 收敛，完成校准 09-11 07:10（2026-09-10 03:55）
0. `current/tasks.md`、`patterns` #71~74、`00-overview.md`：**更新**——第 20 轮巡检：17:50 越过重跑段，进度 66.89%，吞吐 3,642，完成校准 09-11 00:00~20:00（2026-09-09 22:45）
0. `current/tasks.md`、`patterns` #67~70、`00-overview.md`：**更新**——第 19 轮巡检：resume 自动重跑旧 failedSlices（代码核实）、shortfall 2.24%、完成校准后推到 09-11 16:00~24:00、panic 判据修正（2026-09-09 17:35）
0. `current/tasks.md`、`00-overview.md`：**更新**——网关 `883daeb` 重部完成（中断 35 分钟、零孤儿、四项全部生效），守护 PID 2967491；本会话收尾交接（2026-09-09 12:50）
0. `current/tasks.md`、`00-overview.md`、`agent-tasks/2026-09-09-p4-bootstrap-patrol/`：**更新**——网关重部 `883daeb` 完成核查（res1 11:53 / res2 12:04，12:13 resume，12:17 守护重启），第 19 轮巡检由新会话接管，简报落盘（2026-09-09 12:35）
0. `current/tasks.md`、`00-overview.md`：**更新**——新会话交接文档位置（SPIDER `_note/handoff-2026-09-09-p4-bootstrap-config-v2.md`）（2026-09-09 12:00）
0. `current/tasks.md`、`00-overview.md`：**更新**——master 启动 panic/构建残缺/门禁三处已修（`883daeb`，含去 build tag），网关重部 11:45 重开（2026-09-09 11:45）
0. `02-user-preferences.md`、`current/tasks.md`：**更新**——用户决定去掉 build tag（spider 二进制须可复用），角色运行时按子命令决定；并入修复（2026-09-09 11:15）
0. `current/tasks.md`、`00-overview.md`、`lessons/failure-配置v2…`（续）、`patterns` #66：**更新**——网关重部第二次中止：master `4f5f528` init 双角色 panic、
   deploy.sh 单文件构建残缺、门禁只编译不运行；修复中（2026-09-09 11:05）
0. `02-user-preferences.md`、`current/tasks.md`、`00-overview.md`、`patterns` #65：**修正**——用户另一会话澄清"配置按服务拆分"是拆代码不拆文件（`4f5f528`），
   两份文件方案已回退；网关重部按新状态重新授权（2026-09-09 10:55）
0. `current/tasks.md`、`00-overview.md`、`patterns-长周期生产巡检.md`（63~65）：**更新**——第 17 轮：重跑自然消失、进度 60.47%、校准 09-11 10:00~18:00；
   短缺不重跑修复 `97541e9`；用户决定立即重部网关四项合并（进行中，含配置拆分顺序陷阱）（2026-09-09 10:30）
0. `lessons/failure-copy_child计数校验对称差误判重跑.md`（续）、`patterns-长周期生产巡检.md`（61~62）、`current/tasks.md`、`00-overview.md`：**更新**——
   第 16 轮诊断：结构性短缺触发无效整窗重跑（58% 时间浪费），修复中；进度 56.92%，校准 09-11 晚~09-12（2026-09-09 05:20）
0. `current/tasks.md`、`00-overview.md`、`lessons/patterns-长周期生产巡检.md`（59~61 条）：**更新**——第 15 轮：守护新版重启生效、吞吐降至 1,850、
   进度 53.71%、校准后移 09-12 上午；低产出窗口成因待第 16 轮诊断（2026-09-09 00:35）
0. `current/tasks.md`、`current/risks.md` R7：**更新**——下载调度日志网盘凭据打码已修（SPIDER `1ab56b4`，7 处含 worker 级 logger）；新风险：测试文件硬编码真实 RefreshToken/BDUSS（2026-09-08 20:05）
0. `lessons/patterns-长周期生产巡检.md`（56~58 条）、`current/tasks.md`、`00-overview.md`：**更新**——第 14 轮：跨过 50%；守护因 es_curl.sh 解析 v2 格式失败失能 37 分钟
   （守护存活但取数失败是巡检盲区），已修并恢复；校准 09-11 01:45~02:20（2026-09-08 19:35）
0. `current/tasks.md`：**更新**——启动日志凭据打码已修（SPIDER `9cea15a`、pan/common `e36a582`），随下次重启生效；新发现下载调度运行时日志打印网盘账号凭据待修（2026-09-08 17:45）
0. `02-user-preferences.md`、`current/tasks.md`、`00-overview.md`：**更新**——用户原则：配置按服务拆分（统一文件多余注入、网关自注入可能成环）；
   只读分析确认当前无实际循环但凭据暴露面扩大；拆分方案准备中，等 bootstrap 完成后随网关重启生效（2026-09-08 16:50）
0. `current/tasks.md`、`00-overview.md`：**更新**——前端 gwEndpoint 缺陷修复重发（NC-JS `7fb3721`）并 CDP 复测通过；网关→GitHub 出网偶发超时记为排查线索（2026-09-08 16:30）
0. `lessons/failure-前端环境默认值写死本地.md`：**新增**——NC-JS 两个子应用 `gwEndpoint` 默认值写死 `gwAddrs[1]`(本地)，
   生产清空 localStorage 后卡在「正在连接服务器(本地环境)」；已抽 `defaultGwAddr()` 按 hostname 选择并发布（NC-JS `7fb3721`）（2026-09-08 16:10）
0. `lessons/failure-配置v2二进制无本地回落导致老容器重启即挂.md`（子 Agent 追加处置与单主机部署路径）、`current/tasks.md`、`00-overview.md`：
   **更新**——4 个老容器重建 + xunlei_share 删除完成，非 resdb 全部切 v2；新隐患 3 个 exited 历史容器 restart=always（2026-09-08 16:15）
0. `lessons/failure-配置v2二进制无本地回落导致老容器重启即挂.md`：**新增**——换宿主机 spider 后未重部容器重启即 crash-loop（jenkins url_check 已挂），
   set -e 半完成态、spider.old 备份；`current/tasks.md`、`00-overview.md` 同步第二阶段完成与熔断待决策（2026-09-08 15:10）
0. `current/tasks.md`、`00-overview.md`、`lessons/patterns-长周期生产巡检.md`：**更新**——第 13 轮零介入，进度 46.52%，剩余全小窗口，
   校准 09-10 15:00~09-11 02:00；经验条目重号修正（巡检 Agent 追加的 46~51 改为 48~53，45 条被 48 条推翻）（2026-09-08 14:35）
0. `current/tasks.md`、`00-overview.md`、`lessons/patterns-长周期生产巡检.md`：**更新**——配置 v2 第一阶段完成（OSS 首次上传、kuakes 灰度、
   网关切 master `6cf6157`，OAuth+浏览 API 上线，id=8 中断 19 分钟），发现 log_store 漂移并修配置；第二阶段 41 进程分批开始；经验 2 条（2026-09-08 12:45）
0. `current/tasks.md`、`00-overview.md`、`lessons/success-配置v2上线准备发现的两个衔接问题.md`：
   **配置 v2 上线准备完成**——github_auth 实际贴错文件（在 `spider.gateway.prod.yaml` 而非
   `spider.prod.yaml`）已结构化合并修复；`config_show`/`Start()` 硬校验/6 台宿主机结构核对全过；
   README §2.7/§2.8 两处过时表述已订正；灰度候选 `kuakes`；执行手册
   `osec-spider-go/PRD/config-v2/rollout-runbook-2026-09-08.md`；SPIDER `6cf6157` 已 push；
   待人工确认 `services.gateway.redis` 与 `redises.*` 是否同实例后即可执行（2026-09-08 11:40）
0. `current/tasks.md`、`lessons/patterns-长周期生产巡检.md`、`00-overview.md`：**更新**——第 12 轮零介入，进度 41.86%，进入密集小窗口段
   吞吐 2,100，校准后延 09-10 06:00~09-11 00:00；经验 3 条（小窗口段分段估算、压力由窗口体量驱动、setsid pid 取法）（2026-09-08 09:40）
0. `sessions/2026/2026-09-08-后台登录改为github授权.md`、
   `decisions/decision-2026-09-08-后台登录改为github-oauth.md`、
   `lessons/failure-握手回包附加字段被传输层丢弃.md`、
   `lessons/success-桩网关加cdp浏览器做登录链路联调.md`、
   `procedures/workflow-带登录态的浏览器自动化.md`、
   `knowledge/reference-github-oauth配置.md`：**新增**——后台登录改为 GitHub OAuth
   （限 1second 组织成员），三仓库已合并 push（SPIDER `41832ca` / NC-JS `5808d42` /
   COMMON `ac5cfc5`），**未部署**；两轮真实浏览器联调抓到两个阻断级问题（握手回包
   字段被 RTC 传输层丢弃、登录失败原因被重试覆盖）并修复；`knowledge/architecture-nc-js.md`
   第 5 节、`knowledge/architecture-queue-admin.md`、`00-overview.md`、`current/tasks.md`
   同步订正旧的"鉴权只有全局 RtcToken"结论（2026-09-08 16:00）
0. `sessions/2026/2026-09-08-res_lc数据纳入后台.md`、`lessons/failure-proto3零值与负一哨兵冲突.md`：**新增**——
   res_lc_* 四个只读接口 + 四个后台页面全部完成、验收通过并合并 push（COMMON `35eb8fd` / SPIDER `0b35940` / NC-JS `8aed2fd`），
   **未部署**（等 P4 bootstrap 完成）；`procedures/workflow-子agent任务简报.md` 补三条协作经验（2026-09-08 10:30）
0. `procedures/workflow-子agent任务简报.md`、`agent-tasks/`（新目录）、`02-user-preferences.md` 第 7 条：**新增**——
   [用户确认] 子 Agent 任务描述一律落盘成简报文件（`00-shared.md` 共享 + `10-*.md` 角色 + `90-review.md` 验收），
   prompt 只给绝对路径，追加要求改文件不复述；首次应用于 `agent-tasks/2026-09-08-lifecycle-admin-data/`（2026-09-08 09:45）
0. `agent-tasks/2026-09-08-lifecycle-admin-data/`：**新增**——res_lc_* 数据纳入管理后台任务：COMMON 契约 `3c0f4f8`
   （ListResources/TableStats/ListEvents/TableDiagnostics 四个只读 rpc）+ 顺带修正 8 个 proto 的 PPIO 老 go_package
   与前端 protc_gen.sh 缺 PATH；SPIDER/NC-JS 两个 sonnet 子 Agent 并行开发中（2026-09-08 09:45）
0. `lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md`、`sessions/2026/2026-09-08-spiderAdmin样式修复.md`：**新增**——spiderAdmin 线上样式丢失
   (Vue mount 清空 qiankun 包裹层)与顶栏 #001529(antd 两级选择器)已修并重发 OSS(NC-JS `b93922d`)；`architecture-nc-js.md` §8、`00-overview.md` §6 同步（2026-09-08 07:20）
0. `current/tasks.md`、`lessons/patterns-长周期生产巡检.md`、`00-overview.md`：**更新**——第 11 轮夜巡零介入，进度 35.13%，夜间 5,526 docs/s，
   04:04 repair 互斥再次生效，校准 09-09 19:30~09-10 01:30；经验 3 条（隧道 setsid、互斥判据命中 id=4、刹车计数归零）（2026-09-08 04:35）
0. `current/tasks.md`、`lessons/patterns-长周期生产巡检.md`、`00-overview.md`：**更新**——第 10 轮：补跑 20:22 结束、真实复制 4,807 docs/s、
   进度 26.15%、完成校准 09-09 18:00~09-10 06:00；经验 4 条（尾段分片退出、翻台间隙、补跑结束信号、小窗口段）（2026-09-07 23:05）
0. `current/tasks.md`、`lessons/patterns-长周期生产巡检.md`、`00-overview.md`：**更新**——第 9 轮：守护新版 PID 4106692 生效、零重跑、
   仍在幂等补跑（净新增负），完成校准 09-10 06:00；经验 4 条（_tasks total 语义、补跑看 conflicts、探针与 r 解耦、pgrep 自匹配）（2026-09-07 18:00）
0. `current/tasks.md`、`lessons/patterns-长周期生产巡检.md`：**更新**——第 8 轮：白跑 3 h 后取消孤儿任务立竿见影，新校验生效 FailedSlices 12→0，
   进度仍 22.6%；经验 3 条（容器名 spider-gateway、守护无全局预算、守护脚本须原子替换）（2026-09-07 13:05）
0. `current/tasks.md`、`00-overview.md`、`lessons/patterns-长周期生产巡检.md`：**更新**——第三次热修 `ca92fb3` 重部完成（中断 24 分钟，
   新校验生效，互斥热修在 04:00 生产验证），守护新 PID 3963729；新增经验：pause 不取消 ES reindex、孤儿任务需 `_cancel`（2026-09-07 10:45）
0. `knowledge/architecture-nc-js.md` §7.1、`sessions/2026/2026-09-07-资源生命周期架构图.md`：spiderAdmin 新增「架构图」页 + 构建前同步脚本（未部署）（2026-09-07 09:20）
0. `sessions/2026/2026-09-07-资源生命周期架构图.md`、`lessons/success-archify画图的几何约束.md`：**新增**——
   资源生命周期两视角架构图（`osec-spider-go/PRD/res-lifecycle/diagrams/`），archify 几何约束经验（2026-09-07 08:30）
0. `lessons/failure-copy_child计数校验对称差误判重跑.md`：**新增**——childCountOk 对称差把 dst>src 判不达标，整窗重跑全 version_conflicts 白跑（一次 2.5 h）；
   `current/tasks.md`、`patterns-长周期生产巡检.md`、`00-overview.md` 同步第 7 轮（守护上限 18000、进度 22.6%、无 bnd child 阶段、守护无人值守验证）（2026-09-07 08:05）
0. `current/tasks.md`、`lessons/patterns-长周期生产巡检.md`、`00-overview.md`：**更新**——第 6 轮巡检零介入；源索引子文档实测 12.0 亿，
   copy_child 纯净吞吐 ≈4,400 docs/s，完成校准 09-09 晚~09-10 早；新增 4 条经验（res_long file 计数口径、早年窗口为 0、禁聚合、守护取数失败标记）（2026-09-06 18:55）
0. `current/tasks.md`、`lessons/patterns-长周期生产巡检.md`、`00-overview.md`：**更新**——动态 rps 守护上线（SPIDER `73dd99d`/`523e2a8`），
   12:42 rps 2500 resume，13:25 切入 copy_child，peak 2500→7500；新增 4 条经验（sliced reindex 父任务 rps=0、集群空载 heap 85~93、
   外部守护架空网关 guard、copy_child 窗口不按子文档配平）（2026-09-06 13:45）
0. `decisions/decision-2026-09-06-全量bootstrap动态rps守护续跑.md`：**新增**——v2 延迟熔断后续跑方案：rps 2500 起步 + 10 分钟区间慢请求占比动态调峰，
   UPDATE params 持久化 + _rethrottle 即时；记录网关守护只在 copy_child 且只看 heap 的架构缺口与真实用户影响量化（2026-09-06 11:50）
0. `current/tasks.md`、`00-overview.md`、`lessons/patterns-长周期生产巡检.md`：**更新**——第 5 轮巡检：id=9 canceled；v2 延迟 5,469 ms 真熔断，
   id=8 11:08 paused（copy_parent 94%）；子文档突增定性为回滚后重写；新增 4 条巡检经验（延迟脚本分组、尾段窗口缩小、守护只看 heap、pkill 陷阱）（2026-09-06 11:30）
0. `current/tasks.md`、`lessons/patterns-长周期生产巡检.md`：**更新**——P4 三件事完成细节（回滚 147,424、`e44b702` 双机、resume 续跑）、
   第 5 轮巡检启动并决定 cancel id=9；巡检经验修订 `_tasks` 精确后缀匹配结论、写脚本最小真实试跑、pause 前看 pending（2026-09-06 09:50）
0. `00-overview.md`、`lessons/failure-临时表排序规则不一致导致JOIN报错.md`：**更新/新增**——P4 三件事收口：误标 147,424 行已回滚（剩余 0、事件 147,424 条）、repair/bootstrap 互斥热修 `e44b702` 上线双机（res1 `b0a118d1` 09:22 / res2 `d1972841` 09:26，leader 切到 res1，回滚位 `fb26e82`）、id=8 已 09:30 resume 并断点续跑；新增排序规则失败经验（SPIDER `82ef0d8` 修复回滚脚本）（2026-09-06 09:40）
0. `current/tasks.md`、`lessons/failure-repair对账在bootstrap未完成时误标数据.md`：**更新**——误标精确范围（res_lc_bnd_00 147,432 行）、
   389 纠正/14 去重为良性、互斥热修 `dd4b7e0`/`e44b702`、回滚脚本 `2d32689`；用户授权回滚并决定立即重部热修网关（2026-09-06 09:20）
0. `current/risks.md` R6、`current/tasks.md`、`00-overview.md`：**更新**——repair 作业 id=9 趁 id=8 暂停开跑误标数据，
   Agent pause 被 auto 分类器拦截，P4 阻塞等用户人工 pause 与回滚误标行；作业调度串行导致 id=8 resume 后不推进（2026-09-06 07:50）
0. `lessons/failure-repair对账在bootstrap未完成时误标数据.md`：**新增（critical）**——第 3 轮巡检发现 repair 作业 `id=9` 的
   `db_to_es` 把 bootstrap「尚未复制到 ES」的 DB 行误置 `status=3`（≈50 行/秒），会导致 copy_child 静默漏搬子文档；
   触发时序是「pause bootstrap 反而放行了从 04:00 起排队的 repair」（jobRunner 同步执行、轮询被占）。
   同时 SPIDER `4f22ffa` 固化巡检脚本 `scripts/lc_job_brief.sh` / `scripts/lc_count_light.sh`（2026-09-06）
0. `decisions/decision-2026-09-06-全量bootstrap熔断后原地resume.md`：**新增**——id=8 copy_parent 吞吐 1,442/1,523 触发熔断 pause，
   主控判定为作业侧窗口固定开销（reindex created==total 限速空等、集群全正常），决定原地 resume 并修订吞吐熔断条款；
   `lessons/patterns-长周期生产巡检.md` 补 4 条（created/total 判据、slices 前缀计数、双写背景增速、lc-check 输出过大）；
   `current/open-questions.md` 新增提速方案待用户决策（2026-09-06）
0. `lessons/patterns-长周期生产巡检.md`：**新增**——全量 bootstrap 第 1 轮巡检经验：巡检子 Agent 须前台 sleep 等待、
   隧道要 keepalive、复制阶段 lc-check progress 失效改用 `_count` 差分、watch 脚本静默降级要识别；
   建库 3.9 h、copy_parent ≈2,100 docs/s 实测数据。`current/tasks.md` 同步（2026-09-06）
0. `current/tasks.md`、`00-overview.md`：**更新**——热修 4/5（窗口整段 reindex + 自适应窗口）上线 `fb26e82`，单月实测 id=5 通过、
   dryRun id=7 通过；**全量 bootstrap 作业 id=8 于 2026-09-05 23:01 启动**，首 2 小时无熔断，预计 09-07 14:00 完成；
   记录跨会话巡检命令、熔断条件与全量完成后待办（P5 灰度、配置 v2 上线等）（2026-09-06）
0. `lessons/failure-copy_child真正瓶颈是子文档量.md`、`sessions/2026/2026-09-05-生命周期P4第三次尝试.md`：**新增**——
   网关双机重部到 `fbddacb`（修复 3）成功、线上零损伤；单月 `copy_child` 复测每批 63~103 s、
   单月剩余约 7 h，**未达标**，作业 `id=4` 再次 paused、全量未启动。
   量纲事实：单月 64.9 万父 → 3245 万子文档（50/父），全量约 7.4 亿；2000 rps 限速下 30 分钟目标不可达。
   同步更新 `00-overview.md`、`current/tasks.md`。报告 `rollout-2026-09-05.md` §8（SPIDER `6f436a7`）。
0. `lessons/failure-copy_child小reindex被轮询间隔拖垮.md`、`sessions/2026/2026-09-05-生命周期P4演练.md`：**新增**——
   P4 重排：网关双机重部热修分支 `f0d5048` 成功、缺陷 A/B 生产验证通过（fielddata 恒为基线、无 Error 1390）；
   新发现 `copy_child` 每 200 个父 id 一次小 `_reindex` 却按 `reindexPollInterval=10s` 轮询
   （实测 22 s/批 → 单月 21 h、全量 20 天），作业 id=4 已 paused、**全量未启动**；
   `00-overview.md` 同步（2026-09-05）

0. `sessions/2026/2026-09-05-生命周期P4启动失败.md`、`lessons/failure-bootstrap按id排序打爆ES堆.md`：**新增**——
   STORAGE 双机重部(首写从旧索引兜底继承已核验)、双写窗口补齐 3551 条(新工具 `SPIDER tools/lc-backfill-legacy`)、
   P4 bootstrap 启动 10 分钟后 failed(两个阻塞缺陷：`sort:["_id"]` 打爆 ES 堆 / `batch=5000` 超 MySQL 占位符上限)，
   线上无损；`00-overview.md`、`current/tasks.md` 同步（2026-09-05）

0. `sessions/2026/2026-09-05-生命周期P3上线.md`、`lessons/failure-resdb的ES端点指向已下线集群.md`：**新增**——
   生命周期 P3 上线（STORAGE 双写网关双机 + API v3 两台，核验全过；osec-resdb worker 因 ES 端点失效
   fail-fast 并完整回滚，属既有故障）；报告 SPIDER `7435489` 已 push；
   `00-overview.md`、`current/tasks.md` 同步（2026-09-05）

0. `sessions/2026/2026-09-05-生命周期P0上线.md`：**新增**——资源生命周期改造 P0 上线
   （基线采集 + 67 张 `res_lc_*` 表 + 两套 ES 模板/三索引/四别名，全部核验通过；报告 SPIDER `bbb9f2a`）；
   `00-overview.md`、`current/tasks.md` 同步（2026-09-05）
0.1. `knowledge/architecture-es索引现状.md`、`decisions/decision-2026-09-04-资源索引生命周期改造方案.md`、
   `sessions/2026/2026-09-04-资源生命周期改造PRD.md`：**新增**——生命周期改造 PRD v1.1 完成，生产 ES 实测基线
   （含 2966 万无 join 百度存量），`current/tasks.md`、`current/open-questions.md`、`00-overview.md` 同步（2026-09-05）
1. `decisions/decision-2026-09-04-管理服务并入网关.md`、`decisions/decision-2026-09-04-前端合并为spiderAdmin.md`、
   `sessions/2026/2026-09-04-管理服务并入网关与前端合并.md`：**新增**——`queue_admin` 由独立进程并入
   `spider_gateway`（目录 `services/gateway/queue_admin/`，复用 7542/:8082，新增 dlock 抢主锁），
   前端 `docSpiderScheduler`+`resSpiderScheduler` 合并成 `admin/spiderAdmin`（左侧栏布局、一条 RTC 连接）；
   `knowledge/architecture-queue-admin.md`、`knowledge/architecture-nc-js.md`、`00-overview.md`、
   `current/tasks.md` 全部同步（2026-09-04 晚）
2. `knowledge/architecture-queue-admin.md`、`sessions/2026/2026-09-04-队列监控系统queue-admin.md`：**新增**——
   队列监控管理系统 queue-admin 全流程上线（后端 osec-res1、前端已发 OSS）；`00-overview.md`、`current/tasks.md` 同步（2026-09-04 晚）
3. `knowledge/architecture-nc-js.md`：**新增**——调研新加入工作空间的前端仓库 NC-JS
   （pnpm workspace + Vite6 + Vue3 TSX + ant-design-vue，`admin/` 下 4 个 qiankun 子应用 + 主应用，
   共享库 `packages/catalyst`）；确认后台**不走 REST 而是 WebRTC gRPC 直连 SPIDER 网关**、
   仓库内**没有任何 schema 驱动渲染**、新增后台页应加在资源调度子应用里（**该结论已被 spiderAdmin 合并取代**）；
   `00-overview.md`、`01-index.md` 同步（2026-09-04）
4. `decisions/decision-2026-09-04-合并sweep-guard分支冲突取舍.md`：**新增**——SPIDER 合并
   `feat/sweep-guard-a/b` 到 master（`go build/vet/test` 通过、worktree 与分支已删、未 push），
   记录冲突取舍依据（不机械套用"两边全保留"，master 已修正的保活语义优先）；
   `00-overview.md`、`current/tasks.md` 同步（2026-09-04）
5. `lessons/failure-网关重启暴露ES集群已更换.md`：**新增**——上线时网关因 ES 配置过期崩溃重启的归因与"重启前验证外部依赖"规则；
   `procedures/workflow-部署.md` 加该检查清单并更正"一个服务多命令"的错误描述；`02-user-preferences.md` 加"子 Agent 用 sonnet"、"完成后 commit+push"；
   `sessions/2026/2026-09-04-队列v2改造.md` 补上线执行记录与人工收尾交接；`current/tasks.md`、`00-overview.md` 同步（2026-09-04 下午）
6. `sessions/2026/2026-09-04-队列v2改造.md`、`lessons/patterns-并行重构的分阶段切分.md`：**新增**——队列 v2 升级全程摘要
   （Phase 0 契约 + 6 个 sonnet 子 Agent 并行 + 清理）、三阶段并行重构模式；`00-overview.md`、`02-user-preferences.md`
   （子 Agent 一律 sonnet）、`knowledge/architecture-spider.md`（队列约定重写）、`current/tasks.md` 同步（2026-09-04）
7. `decisions/decision-2026-09-04-队列v2统一走网关.md`（状态改为已完成）、
   `sessions/2026/2026-09-04-队列v2改造收尾清理.md`：**新增**——删干净全仓残留的
   `queue_task.Service`/`OnKeyword` 等旧队列代码（`share`/`share_pwd`/`ad_share`/`quark_share`/
   `xunlei_share`/`keyword_filter`/`file_bot`/`urn` 命令及 `illuminate/queue-task/service.go`），
   `upyunso-detail.go`/`haisou.cc.go` 残留引用改走网关队列；`go build`/`go vet` 全仓通过；
   `.vscode/launch.json` 补 3 个 v2 消费者调试配置；未 push、未上线（2026-09-04）
8. `lessons/failure-antdv-Row-字符串style.md`：**新增**——antdv `Row` 传字符串 style 触发 `CSSStyleDeclaration` 索引属性报错，已修 spiderAdmin 总览页（2026-09-04）
9. `decisions/decision-2026-09-03-清理下线爬虫代码.md`：**新增决策**——以 `./deploy.sh ps` 为判据，
   删除 21 个线上无进程的爬虫命令及其代码/配置（26,228 行，含 `services/{pansoso,panduoduo,sosuopan,pan56,xiaobaipan}`、
   `services/keyword/fuck0fy`、9 个 `keyword_*`、`keyword_magnet`、`keyword_repanso`、`keyword_yunso_net`），
   保留 `keyword_haisou` 与全部非爬虫工具命令；`deploy.sh` 删 3 个僵尸条目、`config` 与两份 yaml 同步清理。
   顺带确认 2609 批次 6 站爬虫**已全部上线在跑**。`00-overview.md`、`current/tasks.md` 同步（2026-09-03 晚）。
   **第二轮（2026-09-04）**：按用户定夺补删 `deploy.sh` 的 `url_clear` 死条目、
   `services/online_doc/` 与 `services/alipan/` 两个无引用死包；osec-resdb 两个废弃容器
   用户确认不要了但删除需 sudo 被策略拦截，命令留在 `current/tasks.md` 待人工执行。
10. `decisions/decision-2026-09-03-下线haisou.md`：**新增决策**——用户决定下线 haisou，
   代码保留但 `enabled` 改为 nil 视为关闭、`deploy.sh` 保持注释、探路 cron 撤除；
   `00-overview.md`、`current/tasks.md` 同步（2026-09-03 晚）
11. `lessons/failure-haisou搜索接口收紧.md`：**追加第二轮归因**——验证了「13001 与积分无关」
   （全新满额 IP 首请求即被拒且不扣分），逆向出站点新上的 `X-HS-Client-Context` 匿名身份头
   并落地成 `osec-spider-go/scripts/haisou_client_context.py`；结论改为"按来源网络的端点级拦截"，
   用户实测补齐最后一块后**结论定案**：普通 IP 能搜（耗尽返 `11003`）、代理 IP 满额却 `13001`，
   两者是互不相干的拒绝路径，属代理网段的端点级拦截；额度 min(ip,fingerprint)、单 IP 50 次搜索/天。
   按用户要求已把身份头 + 积分账本写进 Go 爬虫
   （`services/haisou/client_context.go`、`credits.go`、`credits_test.go`），
   编译/vet/离线单测通过但联网仍无法验收（2026-09-03 傍晚—晚间）
12. `lessons/success-爬虫保活语义.md`：**新增**——7 个新爬虫的 `alive()` 从「轮次成功」
   改到「`CommitResLink` 成功」，并修掉 keepalive 包读 nil channel 挂死的隐患；
   `00-overview.md`、`knowledge/architecture-spider.md` 同步（2026-09-03）
13. `knowledge/domain-站点-2609接入批次.md`、`procedures/workflow-并行开发多站点爬虫.md`、
   `lessons/failure-haisou搜索接口收紧.md`：**新增**——并行开发并合并 6 个站点爬虫，
   5 站联网验收通过、haisou 被站点收紧未能验收；`00-overview.md`、`site-discovery/history.md` 同步（2026-09-03）
14. `knowledge/domain-站点-misoso.md`：**新增**——misoso.cc(实抓 melost.cn) 爬虫开发完成，
   626 万条规模，域名不一致+过期sitemap+越界文件假200 三层陷阱；`00-overview.md`、
   `current/tasks.md`、`procedures/workflow-新站点调研.md` 同步补记（2026-09-03）
15. `lessons/success-本地代理池打通.md`：**新增**——修复 `localIp()` 并打通本地代理池，记录三个查错方向的坑（2026-09-03）
16. `site-discovery/`（新目录）、`procedures/workflow-站点发现.md`、`sessions/2026/2026-09-03-站点发现任务首轮.md`：**新增**——建立常态化站点发现任务与工具集，首轮 6 个站点达标（2026-09-03）
17. `knowledge/domain-网盘有效性检测.md`、`procedures/workflow-新站点调研.md`：补记夸克 `41031` 业务码、连接层限流、magicpost 插件站、域名不一致等实测经验（2026-09-03）
18. `knowledge/domain-网盘有效性检测.md`、`lessons/success-网盘失效判定原则.md`、`sessions/2026/2026-09-02-修复夸克阿里有效性检测.md`：**新增**——修复夸克/阿里有效性检测的三类误判（2026-09-02）
19. `sessions/2026/2026-09-02-kkpans爬虫开发.md`、`lessons/success-爬虫联网集成测试.md`：**新增**——kkpans 爬虫开发落地与爬虫联网集成测试经验（2026-09-02）
20. `knowledge/architecture-spider.md`：新增 `services/bbs` 包、`bbs_*` 命令分类、"写新爬虫时的可复用要点"（2026-09-02）
21. `knowledge/domain-站点-kkpans.md`：新增"实现状态"一节（2026-09-02）
22. `current/tasks.md`、`00-overview.md`：kkpans 爬虫 P0 待办完成，改为待上线核对（2026-09-02）
23. `decisions/decision-2026-09-02-停止磁力资源采集.md`：**新增决策**——项目停止磁力采集与入库，只做 4 种网盘类型（2026-09-02）
24. `current/open-questions.md`：kkpans 5 个问题全部答复并落地，已清空（2026-09-02）
25. `03-project-context.md`、`00-overview.md`、`procedures/workflow-新站点调研.md`、`knowledge/domain-站点-kkpans.md`：同步磁力停采约束（2026-09-02）
26. `knowledge/domain-站点-kkpans.md`、`procedures/workflow-新站点调研.md`：新增——kkpans 调研结论与通用站点调研工作流（2026-09-02）
27. `02-user-preferences.md`：**更正**——规则正本是 `AGENTS.md`，`CLAUDE.md` 是软链接，不是两份副本（2026-09-02）
28. `procedures/workflow-部署.md`：新增"如何确认线上现役服务"（`./deploy.sh ps`）（2026-09-02）
29. `current/tasks.md`、`current/risks.md`、`current/open-questions.md`：重命名收尾与编译修复已完成，改写待办与风险（2026-09-02）
30. `procedures/workflow-本地构建与验证.md`：四仓库均可编译；补记收尾步骤与 tidy 副作用（2026-09-02）
31. `knowledge/architecture-spider.md`：编译状态、`bnd_resolver` 关键类型速查、`devops_res_reindex` 守卫（2026-09-02）
32. `00-overview.md`、`03-project-context.md`：module 名与 replace 表更新（2026-09-02）
33. `sessions/2026/2026-09-02-重命名收尾与修复编译.md`：新增并追加"同日后续"（2026-09-02）
