---
title: 记忆索引（脚本生成）
type: index
status: active
created_at: 2026-09-02T10:55:00+08:00
updated_at: 2026-09-14T10:23:38+08:00
priority: critical
keywords: [索引, 导航, 启动包, mem.py]
summary: 由 scripts/mem/mem.py index --write 从各文件 Front Matter 自动生成，禁止手工编辑；改 summary/keywords/questions 后重新生成
load: always
---

# 记忆索引（脚本生成，勿手改）

本文件 = `scripts/mem/mem.py boot --kw 3` 的输出快照。找文件先看这里；找不到就 `mem.py search <自然语言问题>`；
定位到文件后 `mem.py outline <file>` 看章节，再 `mem.py body <file> --section <标题>` 只读需要的一段。
维护方式：改目标文件 Front Matter（summary / keywords / questions），然后运行 `scripts/mem/mem.py index --write`。

# agent-memory 启动包（脚本生成, 133 文件）— 格式: 路径 | 优先级 | 更新 | summary | 关键词; ? 后为该文件能回答的问题

## 根目录 (3)
- 00-overview.md | crit | 2026-09-14 | 网盘资源取证系统的最小启动上下文：五仓库职责、数据链路、最近 7 天状态、在生效的决策与经验，以及怎么用 mem.py 找其余记忆文件 | 网盘资源爬取、版权取证、COMMON
- 03-project-context.md | crit | 2026-09-13 | 五个仓库（4 个 Go + 1 个前端）的磁盘路径、module 名、职责、相互依赖与 go.mod replace 现状 | 仓库、module、replace
  ? 各仓库的职责分别是什么 / go.mod replace 现状是怎样的
- 02-user-preferences.md | high | 2026-09-13 | 用户对语言、脚本沉淀、记忆维护、thinking 长度、敏感信息禁写，以及删除类不可逆功能上线前必须线上 dry run + 独立复核的明确要求 | 偏好、中文、脚本沉淀

## current/ (5)
- current/tasks.md | crit | 2026-09-14 | 仍在推进/阻塞/待决策的事项（P0 误删事故重爬中；P5 顺序 阶段C→A'→阶段D）；已上线任务在 archive | 任务、进度、待办
  ? 当前该做什么，有哪些待办
- current/open-questions.md | high | 2026-09-13 | 待确认：转存下载链路账号池是否续期；误删资源重爬已按确认节奏开始（进度在 tasks.md），A'/阶段 D 已按答复推进 | 待确认、事故恢复、lifecycle_checker
  ? 当前有哪些待用户确认的问题
- current/risks.md | high | 2026-09-14 | 影响开发与运维安全的已知风险点；最高 R9 lifecycle_checker 误删 115.6 万资源（修复已上线、恢复待决策） | lifecycle_checker误删、风险、阻塞
  ? 密钥、安全相关的风险在哪看
- current/changelog.md | low | 2026-09-13 | 按日期倒序的一句话变更流水，每条指向 session/decision 文件；回答"某事哪天做的、细节在哪 | 变更记录、changelog、历史
- current/tasks-backlog.md | low | 2026-09-13 | 从 tasks.md 拆出的低优先级/等人工/归档遗留事项：文档爬虫 FC 6 项人工步骤、归档任务遗留待办、P3 代码小修 | backlog、P3、文档爬虫
  ? 文档爬虫 FC 自动化还差哪些人工步骤 / 有哪些 P3 低优先级待办

## decisions/ (17)
- decisions/decision-2026-09-02-停止磁力资源采集.md | crit | 2026-09-02 | 项目现只采集 4 种网盘类型资源，不再采集或入库磁力/BT 资源；存量索引与接口保留 | 磁力、torrent、magnet
- decisions/decision-2026-09-03-全站扫描不在启动时触发.md | crit | 2026-09-03 | 全量扫描完成后把时间写进 redis；启动时检查该时间，有则跳过全量，只跑增量 | 全站扫描、全量、启动
- decisions/decision-2026-09-04-资源索引生命周期改造方案.md | crit | 2026-09-12 | 用短周期(cur/prev)+长周期三索引与 MySQL 分表元数据替代单大索引的失效清理方式；两套方案共存、v3 接口切换、双写保回滚 | 生命周期、lifecycle、三索引
  ? 资源生命周期改造方案是什么，为什么用三索引 / res_lc 是什么，双写和 v3 接口是怎么回事 / 索引轮换/失效检测怎么改造的
- decisions/decision-2026-09-09-配置按进程拆代码而非文件.md | crit | 2026-09-12 | 用户 2026-09-09 纠正——"配置按服务拆分"指每个进程用自己的配置结构体与 Get(), 禁止导出 config.Config, 配置文件保持一份;… | 配置拆分、拆代码、角色包
  ? 某个进程/角色实际读哪些配置项，怎么本地验证 / config.Config 去哪了，为什么找不到这个类型 / 网关为什么拿不到 spider_gateway 配置节 / 配置文件是不是要拆成多份
- decisions/decision-2026-09-12-记忆系统瘦身与脚本化加载.md | crit | 2026-09-12 | 记忆常驻体积曾达 5.4 万字；已执行：索引改由脚本从 Front Matter 生成、问句路由迁成 questions 字段、词法+语义混合检索、总览 4.… | 记忆系统、token、启动包
  ? 记忆太大，启动 token 太多怎么办 / mem.py 索引怎么生成
- decisions/decision-2026-09-03-下线haisou.md | high | 2026-09-12 | haisou.cc 被站点端点级拦截且单 IP 产出上限极低，决定下线；代码保留、默认不启动、探路 cron 撤除 | haisou、下线、13001
  ? haisou 为什么下线 / haisou 还能不能复活
- decisions/decision-2026-09-03-清理下线爬虫代码.md | high | 2026-09-12 | 以 `./deploy.sh ps` 的线上进程为唯一判据，删除 21 个已不在线的爬虫命令及其代码与配置，保留 haisou | 清理、下线爬虫、deploy.sh ps
  ? 哪些爬虫还在跑，怎么判断 / 某个爬虫代码去哪了，为什么被删了 / 想恢复一个老爬虫怎么办
- decisions/decision-2026-09-04-前端合并为spiderAdmin.md | high | 2026-09-04 | 两个后台子应用合并成 admin/spiderAdmin 并重做左侧栏布局，全应用只保留一条 RTC 连接 | spiderAdmin、NC-JS、子应用合并
- decisions/decision-2026-09-04-管理服务并入网关.md | high | 2026-09-04 | queue_admin 由独立进程并入 spider_gateway，日后管理类需求一律放 services/gateway 之下，不增新进程 | queue_admin、网关、进程合并
- decisions/decision-2026-09-04-队列v2统一走网关.md | high | 2026-09-12 | SPIDER 所有跨进程任务投递从 queue_task.Service(直连 redis list) 改为网关 res_scheduler 队列；选 res… | 队列v2、queue_task、res_scheduler
  ? 队列 v2 是什么，为什么统一走网关 / 旧队列 share_pwd/ad_share/quark_share/xunlei_share/keyword_filter 去哪了 / 队列 v2 怎么上线的
- decisions/decision-2026-09-08-后台登录改为github-oauth.md | high | 2026-09-12 | 固定管理秘钥改为 GitHub OAuth 登录并校验 1second 组织成员身份的四个关键设计取舍与原因 | GitHub OAuth、后台登录、RtcToken
  ? 后台登录为什么改成 GitHub OAuth / 管理秘钥去哪了，needLogin/githubClientId 是什么
- decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md | high | 2026-09-12 | 用户 2026-09-12 采纳 D1~D4——旧链路失效只提前 lc 复检、重合度改语料级三项、bnd 去 has_child、门槛全过才切流；阶段 A/B… | P5、准入门槛、legacy→lc 失效同步
  ? 切 v3 前必须满足哪些门槛 / 旧链路判失效为什么只提前复检而不直接置 lc 失效 / bnd 搜索在 v3 慢的原因与修法 / P5 灰度怎么切、怎么回滚
- decisions/decision-2026-09-12-弃用文档更新类接口.md | high | 2026-09-12 | 用户 2026-09-12 确认——report/likes/dislikes/addViews 这类频繁 update ES 文档的接口已弃用，不做 v3、… | 弃用、addViews、likes
  ? report/likes/dislikes/views 这些接口还要不要做 v3 / 为什么 v3 detail 不能调 addViews / 哪些接口不允许频繁 update ES 文档
- decisions/decision-2026-09-12-阶段D改由API侧自动灰度分流.md | high | 2026-09-12 | 用户 09-12 裁定：API 在 /api/v2/search 服务端按比例走 v3，30% 起、无异常每 100 个 v3 请求 +1% 到全量，异常自动… | 阶段D、灰度、分流
  ? 搜索流量怎么从 v2 切到 v3，谁来切 / search_canary 是什么，比例怎么涨、异常怎么回滚
- decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md | high | 2026-09-13 | 2026-09-13 用户要求 cdp3 挂 NAS（锁心跳 2 s/6 s 过期/被占不等待直接 409）：CDP3DATA=/mnt/nas/apps/c… | cdp3、CDP3DATA、CDP3TEMP
  ? cdp3 的扩展和会话数据放在哪、目录怎么约定 / 调用方用 profile= 时要注意什么
- decisions/decision-2026-09-13-lint长度双阈值.md | high | 2026-09-13 | 超长改为 >12,000 触发、触发后必须压到 <6,000，9,000 起只提示；避免 8,000 单线反复报警 | lint、超长、双阈值
  ? lint 报超长该压到多少字，上限为什么不是 8000 / tasks.md 反复超长怎么办
- decisions/decision-2026-09-04-合并sweep-guard分支冲突取舍.md | medi | 2026-09-04 | 合并遗留分支时，master 已修正的旧逻辑不应因"冲突两边都保留"而被恢复，需先判断冲突是否为真实的两个功能重叠 | sweep-guard、全量扫描守卫、merge 冲突

## procedures/ (12)
- procedures/checklist-不可逆操作上线.md | crit | 2026-09-13 | [用户确认 2026-09-13] 数据误删事故后的硬规则：任何删除/清理/判失效等无法撤销的功能，上线前必须先在线上跑 dry run，再用与新功能无关的独… | 不可逆操作、dry run、二次复核
  ? 要上线一个会删数据/判失效/清理的功能，上线前必须做什么 / dry run 的结果怎么复核，能不能用新功能自己的日志当依据 / 什么时候才允许正式开启删除类功能
- procedures/workflow-fc-chrome上线.md | high | 2026-09-13 | 2026-09-13 实测可行的 fc-chrome 上线链路：本机构建→docker save/rsync 到 osec-jenkins→load/push… | fc-chrome、serverless-devs、ACR
  ? 本机推不了 ACR 时怎么把 fc-chrome 镜像弄上去 / 怎么给共用 FC 域名加路由不碰证书 / fc-chrome 只改 Go 代码怎么快速上线/本地联调
- procedures/workflow-子agent任务简报.md | high | 2026-09-12 | 派子 Agent 时任务描述落盘成文件、prompt 只给路径，并列出子 Agent 的常见失败模式与提示词对策 | 子agent、任务描述、agent-tasks
  ? 我要派子 Agent，任务描述太长怎么办 / 多个 agent 上下文重复怎么解决
- procedures/workflow-并行开发多站点爬虫.md | high | 2026-09-12 | 一次接入多个新站点时的分工方式：worktree 隔离、共享资源集中准备、冲突面收敛、合并与验收 | 并行开发、worktree、子agent
  ? 我要一次接入多个站点，worktree 怎么分工 / 多站点并行开发怎么处理合并冲突
- procedures/workflow-新站点调研.md | high | 2026-09-12 | 接到"探索某资源站并输出爬虫 PRD"时的标准步骤：先找结构化接口，再验证全量可枚举性，最后对账 | 站点调研、爬虫、PRD
  ? 我要调研一个新的资源站，怎么写爬虫 PRD / 怎么找一个站点的公开接口
- procedures/workflow-本地构建与验证.md | high | 2026-09-12 | 四个仓库当前的可编译状态、编译命令、已知失败原因，以及编译/go vet 的验收口径，改代码前必读 | 构建、go build、replace
  ? 编译不过，依赖报错怎么排查 / go mod tidy / replace 问题怎么处理
- procedures/workflow-站点发现.md | high | 2026-09-12 | 收到 `task site-discovery` / `启动网站发现任务` 时的入口、候选来源渠道与要点；正文流程在 site-discovery/READM… | 站点发现、site-discovery、候选站点
  ? 我要找新的资源站，怎么启动网站发现任务 / task site-discovery 是干什么的
- procedures/checklist-仓库脚本清单.md | medi | 2026-09-13 | MEMORY 仓库 scripts/ 下可复用脚本一览（git-hooks 提交信息违禁词钩子、claude-rc systemd 托管 Remote Con… | scripts、git-hooks、commit-msg
  ? 怎么后台启动当前工作空间的 Claude Remote Control 会话 / 记忆仓库 scripts/ 下有哪些可复用脚本，各自做什么 / 怎么给管理员发邮件通知 / 提交信息违禁词钩子在哪，怎么加词或装到新仓库
- procedures/troubleshooting-代理池总览无数据.md | medi | 2026-09-12 | 后台代理池页全 0 时三步定位：网关 dataSource → 上报侧是否部署 → tools/proxy-admin-check 只读巡检 | proxy-admin-check、代理池总览、proxy_admin
  ? 代理池监控的 Scene 是什么，怎么加新消费端 / IP 不可用和被站点封禁怎么区分 / 代理池推送 IP 数在哪看 / 代理池总览/场景明细全 0 怎么排查
- procedures/workflow-带登录态的浏览器自动化.md | medi | 2026-09-12 | 如何启动/复用一个带登录态的调试Chrome并用CDP脚本驱动它, 含"默认profile会被安全策略拦截"的前提坑 | agent-browser、cdp.py、CDP
  ? 我要测浏览器可见的交互，带登录态的浏览器怎么起 / agent-browser.sh / cdp.py 怎么用
- procedures/workflow-部署.md | medi | 2026-09-13 | SPIDER deploy.sh 的常规用法、服务到主机的映射方式、判断线上现役服务的唯一判据、新服务选主机方法、配置分发机制与安全提醒；历次上线（生命周期/… | auto模式、权限分类器、部署
  ? 部署 / 上线怎么操作，日志在哪看 / 新服务该放哪台机器 / 队列 v2 上线收尾脚本是哪个
- procedures/workflow-部署-历史补充.md | low | 2026-09-12 | 历次生产上线（2026-09-05~09-10 生命周期 P3/P4 网关多次重部、代理池监控上线等）的一次性踩坑与已固化到 deploy.sh 的加固记录；… | 生命周期上线、网关重部、dryRun

## lessons/ (32)
- lessons/failure-bootstrap按id排序打爆ES堆.md | crit | 2026-09-12 | P4 bootstrap 的 B1 用 sort:["_id"] 在 15.7 亿文档旧索引上翻页, 触发 _id fielddata 加载, 单页 >550… | bootstrap、存量迁移、P4
  ? P4 bootstrap 为什么跑不起来 / 作业 id=1 为什么 failed
- lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md | crit | 2026-09-14 | checker 用 task.Id(md5) 而非 ShareId 探测，115.5 万条 quark/ali 误删；bnd 再因「违规」tooltip 误判… | lifecycle_checker、误删、dry run
  ? lifecycle_checker 为什么把所有夸克资源判成失效 / 116 万条资源误删是怎么回事，怎么恢复 / 检测吞吐 valid=0 意味着什么 / 代理池 lifecycle_checker 场景成功率 0 的原因
- lessons/failure-longBoundary漂移导致父子跨索引与shortfall误报.md | crit | 2026-09-12 | shortfall 89 条不是子文档丢失：copy_parent/copy_child 各自取 now 算 90 天边界、长跑漂移致父 cur 子 long… | bootstrap、longBoundary、shortfallSlices
- lessons/failure-repair对账在bootstrap未完成时误标数据.md | crit | 2026-09-06 | bootstrap 未完成时跑 repair 的 db_to_es 会把「尚未复制到 ES」的 DB 行误判为丢失并置 status=3，导致 copy_ch… | repair、对账、bootstrap
- lessons/failure-FC实例在WebSocket断开后立即冻结.md | high | 2026-09-13 | 2026-09-13 线上实测：客户端断开 WebSocket 后 FC 视为调用结束并立刻冻结实例，handler 中 kill Chrome→写回 NAS… | FC 冻结、WebSocket、Browser.close
  ? FC 上 WebSocket 断开后 handler 收尾代码为什么不执行 / fc-chrome profile= 为什么要求客户端先发 Browser.close
- lessons/failure-copy_child小reindex被轮询间隔拖垮.md | high | 2026-09-12 | bootstrap B3c copy_child 上万个小 reindex 被固定 3 s 轮询拖垮，改指数退避后吞吐恢复 | bootstrap、copy_child、reindexPollInterval
  ? P4 第二次演练，copy_child 为什么这么慢
- lessons/failure-copy_child真正瓶颈是子文档量.md | high | 2026-09-12 | 修完轮询空等后 copy_child 只快 2.1 倍——因为真正的工作量是 3245 万/单月、7.4 亿/全量的子文档，被 reindex 的 2000 … | copy_child、bootstrap、reindex
  ? P4 第三次尝试，作业 id=4 为什么还是 paused / copy_child 修完轮询还是慢，到底要搬多少子文档 / reindex 限速是多少
- lessons/failure-copy_child计数校验对称差误判重跑.md | high | 2026-09-12 | childCountOk 用 |src-dst| 判达标，但 cur 含双写、long 源侧被删，dst>src 是结构性的；重跑幂等补不回，白跑 2.5 h | bootstrap、copy_child、childCountOk
- lessons/failure-haisou搜索接口收紧.md | high | 2026-09-12 | haisou.cc 搜索接口对代理池 IP 全量 429；傍晚复查排除了积分、请求头、HTTP/2、会话、匿名身份，锁定为按来源网络的端点级拦截 | haisou、13001、限流
  ? haisou 跑不通，13001/请求过于频繁是什么原因 / X-HS-Client-Context 头怎么来的 / haisou 积分额度模型是什么
- lessons/failure-ncjs构建脚本会自动上传OSS.md | high | 2026-09-04 | admin/*子应用的标准 `pnpm build` 脚本默认会把 dist 上传到生产 OSS 并改写 apps.json, 验证构建前必须先用 { dep… | NC-JS、pnpm build、mfe插件
- lessons/failure-proto3零值与负一哨兵冲突.md | high | 2026-09-12 | proto3 标量字段不传时零值是 0，若 0 恰好是合法业务值、而"不过滤"哨兵定成 -1，前端漏传就会静默查错数据且不报错 | proto3、零值、哨兵
  ? 筛选参数传了 0 却查不出数据 / proto3 不传字段被当成过滤条件是什么坑
- lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md | high | 2026-09-12 | 子应用 Vue app.mount 直接挂 qiankun 包裹层会把 <qiankun-head> 内联的全部静态 CSS 删掉(只在线上/被 qianku… | NC-JS、qiankun、微前端
- lessons/failure-resdb的ES端点指向已下线集群.md | high | 2026-09-05 | STORAGE worker 所在的 osec-resdb 配置里的 ES 地址是已下线集群，旧代码只打 error 日志继续跑（哑故障），新代码 fail-… | osec-resdb、es_endpoint、ES 集群更换
- lessons/failure-v3首页重合度受前缀展开分片彩票影响.md | high | 2026-09-12 | P5 对拍首页重合度 84%<95% 的两个根因——4% 坑位是 legacy 已删 lc 未删的死链（无反向失效同步）；其余是 match_phrase_p… | P5、重合度、match_phrase_prefix
  ? P5 对拍为什么没通过，v3 首页和 v2 为什么不一样 / dfs 能不能让新旧索引排序一致 / 旧索引 url_check 删掉的文档新方案会同步失效吗
- lessons/failure-前端环境默认值写死本地.md | high | 2026-09-08 | 子应用把 useLocalStorage('gwEndpoint') 默认值写死成 gwAddrs[1](本地 127.0.0.1)，导致生产首次访问卡死；改… | gwEndpoint、gwAddrs、defaultGwAddr
- lessons/failure-品牌版Chrome禁用load-extension与userScripts二次授权.md | high | 2026-09-13 | 2026-09-13 fc-chrome 上线实测：品牌版 Chrome 137+ 忽略 --load-extension，改企业策略 force_insta… | Chrome、load-extension、ExtensionSettings
  ? 为什么 headless Chrome 加了 --load-extension 却看不到扩展 / 怎么让容器里的 Chrome 自动装上 Tampermonkey / 油猴脚本装上了但页面不执行是怎么回事 / Tampermonkey 就绪要等多久, 怎么把等待挪到构建期
- lessons/failure-把拆配置理解成拆文件.md | high | 2026-09-09 | 用户说"拆分"时先确认拆的是什么(代码结构/文件/进程); 用运行时断言或"文件里不写某项"来保证隔离, 通常说明方案层级选错了 | 需求理解、拆分对象、复述确认
- lessons/failure-握手回包附加字段被传输层丢弃.md | high | 2026-09-12 | 网关握手 403 回包的 needLogin/githubClientId 等附加字段被 RTC-gRPC 错误通道丢弃，结构化信息要走专门回调 | RtcTransport、cancelAllPendingCalls、UnaryCallResponse
  ? 握手回包字段传不到前端是什么原因 / 登录失败原因被重试覆盖是怎么回事
- lessons/failure-旁路能力初始化拖垮主流程.md | high | 2026-09-09 | 用会 log.Fatal/panic 的基础设施函数去初始化"可有可无"的监控, 会让每个子命令随配置缺失或 redis 抖动一起死; 以及埋点只覆盖成功路径… | db.Redis、log.Fatal、panic
- lessons/failure-注入脚本用consolelog回传被页面自身替换吞掉.md | high | 2026-09-13 | fc-chrome + kdocCloud.ts 真实文档只回传一条 start 就彻底沉默——根因是金山文档自己的代码加载后整体替换了 window.con… | console.log、CDP、addScriptToEvaluateOnNewDocument
  ? 为什么 CDP 注入脚本只打出第一条日志就再也没有输出了 / 用 console.log 给 doc-crawler/上层回传协议，什么情况下会突然全部收不到 / 页面看起来"卡死"，但定时器明明还在跑，可能是什么原因 / fc-chrome inject=1 主世界注入脚本调试思路
- lessons/failure-网关重启暴露ES集群已更换.md | high | 2026-09-12 | 线上网关自 1 月未重启，期间 ES 集群已更换；队列 v2 上线一重启就 panic。教训：长期不重启的服务会掩盖外部依赖变更，重启前先在目标主机验证配置里… | 网关、gateway、ES
  ? 网关起不来，报 no such host 怎么查 / 重启网关前要检查什么
- lessons/failure-配置v2二进制无本地回落导致老容器重启即挂.md | high | 2026-09-09 | v2 二进制只认 OSS_CONFIG_URL/LOCAL_CONFIG_PATH，不读宿主机 config.yaml；deploy.sh 替换宿主机 spi… | 配置 v2、OSS_CONFIG_URL、config.yaml
- lessons/patterns-并行重构的分阶段切分.md | high | 2026-09-12 | 多个包同时改造且互相引用时，用"主会话先做共享契约 → 子 Agent 只加不删 → 单独清理 Agent 收尾"三阶段避免编译互锁 | 并行重构、子agent、worktree
  ? 多个包同时重构，子 Agent 怎么避免编译互锁 / Phase 0/1/2 怎么切分任务
- lessons/patterns-统计ES索引先查文档形态.md | high | 2026-09-05 | 同一索引可能混着两代写入形态；只按 join=resource 统计会漏掉三分之二资源，任何统计/迁移前先做 exists/must_not exists 对账 | ES、join、nested
- lessons/patterns-长周期生产巡检.md | high | 2026-09-13 | 派子 Agent 做数小时生产巡检的可操作清单（原 98 条经验按主题压缩）：前台等待、隧道 keepalive、复制阶段用 _count 差分而非 prog… | 巡检、bootstrap、子Agent
- lessons/success-本地代理池打通.md | high | 2026-09-12 | 本地怎么用上代理池、三个会让人查错方向的坑，以及验证方法 | 代理池、蜻蜓代理、白名单
  ? 代理池连不上怎么办，本地怎么用上代理池 / 蜻蜓白名单/出口IP不对怎么查
- lessons/success-桩网关加cdp浏览器做登录链路联调.md | high | 2026-09-12 | 涉及浏览器交互的改造仅靠静态审查+单测不足以验收, 要造一个只保留被测链路的桩服务并用带登录态的调试浏览器实测, 本次靠它抓到两个"代码看起来完全正确"的阻断… | 桩网关、stubgw、CDP
  ? 桩服务验收怎么做，为什么静态审查+单测不够
- lessons/success-爬虫保活语义.md | high | 2026-09-12 | 保活续期的唯一判据是"有新链接真正提交成功"，轮次成功不算；顺带修掉 keepalive 包读 nil channel 挂死的隐患 | keepalive、保活、CommitResLink
  ? 保活 keepalive 该在哪调 / 爬虫空跑为什么不告警
- lessons/success-爬虫联网集成测试.md | high | 2026-09-12 | 用「假 committer + 独立 redis 键前缀 + 环境变量开关」让爬虫的联网测试可重复运行且不污染线上 | 集成测试、爬虫、联网测试
  ? 我要给爬虫写测试，联网测试怎么不污染线上
- lessons/success-网盘失效判定原则.md | high | 2026-09-12 | 靠 message 文案匹配判定网盘失效必然随站点文案漂移而失灵，应改用业务码并把未知响应升级为 error | 失效判定、业务码、限流
- lessons/failure-fc-chrome上线踩坑合集.md | medi | 2026-09-13 | 2026-09-13 fc-chrome 上线踩到的 5 个具体坑与对策：Chrome /json/list 是 JSON 数组不是 {targetInfos… | /json/list、pkill -f、docker exec
  ? seedprep 为什么永远等不到扩展 target / docker exec 里 pkill -f 之后命令立刻结束是为什么 / FC 上 WebSocket 连接 120 s 就断是为什么 / 叠层镜像和本地验证过的镜像行为不一样先查什么
- lessons/success-cdp3策略强装扩展与NAS持久化profile.md | medi | 2026-09-13 | 2026-09-13 fc-chrome 实测可行的扩展启用链路（解包目录→chrome --pack-extension→本机 /cdp3-ext upda… | 扩展安装、ExtensionSettings、override_update_url
  ? 怎么让品牌版 headless Chrome 装 NAS 上的自定义扩展 / 策略强装的扩展改了版本为什么不更新 / Chrome profile 存 NAS 为什么慢、怎么存

## knowledge/ (21)
- knowledge/architecture-系统总览.md | crit | 2026-09-02 | 从爬取到入库到检索的完整链路、各服务端口与中间件分工 | 架构、数据链路、网关
- knowledge/api-rpc契约.md | high | 2026-09-12 | COMMON 仓库中各 proto 服务的方法清单、核心消息结构与代码生成流程 | proto、gRPC、StorageRpc
  ? 我要改 gRPC 协议 / proto，改完怎么生成 / 某个 rpc 方法的入参/出参消息结构是什么 / proto 改完要同步哪些下游仓库
- knowledge/api-v3-detail-filectx兼容性分析.md | high | 2026-09-12 | 结论——lc 索引结构与 v2 detail/fileCtx 的查询方式兼容（nested filelist、join file、fid/parent、rou… | v3 detail、fileCtx、res_lc_all
  ? detail/fileCtx 能不能直接查 res_lc_all / 补 v3 detail/fileCtx 要改哪些地方 / 为什么 /api/v2/detail 会报 size 反序列化错误
- knowledge/architecture-api.md | high | 2026-09-12 | osec-resource-api 的路由表、中间件链、依赖服务与后台管理模块；另含 SPIDER 网关 LifecycleRpc 新增的 res_lc 分表… | API、osec-resource-api、gin
  ? 我要改查询接口/限流/搜索 / 后台怎么看 res_lc_* 分表数据
- knowledge/architecture-es索引现状.md | high | 2026-09-12 | 阿里云 ES 6.7 单索引的分片/容量/父子文档结构/入库增速与读写清理链路代码位置，是生命周期改造方案的事实基线 | ES、Elasticsearch、6.7
  ? 生产 ES 有多大，怎么查生产 ES / 无 join 索引和 join 父子索引的区别
- knowledge/architecture-fc-chrome文档爬虫上云.md | high | 2026-09-13 | 2026-09-13 上线的 nc-app-prod-cdp3（14:30 起挂 NAS：CDP3DATA/CDP3TEMP、extensions=、prof… | fc-chrome、nc-app-prod-cdp3、Tampermonkey
  ? 新版 FC Chrome 部署在哪、地址、健康检查 / cdp3 的 NAS 目录/extensions=/profile= 怎么用 / 共用 FC 域名 fc-resource-node-api.krzb.net 有哪些路由
- knowledge/architecture-nc-js-qiankun与后台页面.md | high | 2026-09-12 | qiankun 主应用注册/子应用生命周期、本地开发流程；spiderAdmin 新增后台页面写法与落点（队列监控、资源生命周期各页、架构图页、res_lc … | qiankun、微前端、spiderAdmin
  ? 我要改后台前端，加一个后台页面该怎么加 / qiankun 子应用 / NC ADMIN / apps.json 是什么 / 后台怎么看 res_lc_* 分表数据，资源列表/分表统计/事件流水/表诊断页面在哪
- knowledge/architecture-nc-js-网关对接.md | high | 2026-09-12 | NC-JS 后台前端与 SPIDER gateway 之间没有 REST，只有 WebRTC DataChannel 上自实现的 gRPC 传输；鉴权已改 G… | WebRTC、gRPC、protobuf-ts
  ? 前端怎么连后端，网关 IP 换了改哪 / 前端 proto 怎么生成 / 后台登录 GitHub OAuth 怎么接的，gwToken / RtcToken 兜底是什么
- knowledge/architecture-nc-js.md | high | 2026-09-12 | NC-JS 前端 mono repo 的仓库定位、工程栈、分包布局（admin/*、packages/*）与构建/OSS/Cloudflare 部署机制；qi… | NC-JS、前端、pnpm
- knowledge/architecture-queue-admin.md | high | 2026-09-12 | 队列 v2 的监控管理系统：已并入网关进程的架构、端口、schema 解耦机制、抢主锁、巡检工具与已知数据缺口 | queue-admin、队列监控、QueueAdminRpc
  ? 队列告警怎么配，失败率窗口和阈值是多少 / 告警历史在哪看，告警为什么没发 / queue-admin 队列出问题了怎么看，任务详情 schema 哪来的 / 队列监控端口连不上怎么办
- knowledge/architecture-spider.md | high | 2026-09-12 | osec-spider-go 的入口子命令、目录分层、编译状态、bnd_resolver 关键类型、写新爬虫可复用要点（含配置节 yaml/Duration/… | SPIDER、osec-spider-go、爬虫
  ? 我要改爬虫/加一个站点，该看哪个子命令 / 新增服务配置节，yaml 怎么解析 Duration / 泛型队列 PushTask 怎么写，GwQueue 类型对不上怎么办 / 任务队列怎么消费，seq 是什么，永久失败怎么处理
- knowledge/architecture-storage.md | high | 2026-09-12 | enfi-resource-storage 的三个子命令、写入流程、ES 索引名与幂等策略 | STORAGE、enfi-resource-storage、入库
  ? 我要改入库逻辑，查资源为什么没写进去 / ES 索引幂等/version 判重是怎么回事
- knowledge/domain-站点-2609接入批次.md | high | 2026-09-12 | 本批 5 个站点的形态、子命令、规模、各自的坑与实现状态；详细规格见各自 PRD | dyyjmax、fuxipan、feikuai
  ? dyyjmax/fuxipan/feikuai/kuakes 是什么站，各自的坑是什么 / 2609 批次都接了哪些站
- knowledge/domain-网盘有效性检测.md | high | 2026-09-12 | 两套有效性检测实现的位置、各网盘的判定接口与业务码表、联网自测方法 | 有效性检测、validShareLink、失效
  ? 链接失效检测怎么做，validShareLink 返回 -1 是什么意思 / 夸克/阿里网盘判定不准怎么排查 / 误删资源怎么避免
- knowledge/domain-转存下载链路.md | high | 2026-09-13 | SPIDER 下载调度链路的代码结构、redis 键/MySQL 表、阿里/百度解析方式、三条下载路径，以及 2026-09-13 体检结论：链路空转，阿里 … | 转存下载、share_download、resolve_link
  ? 分享链接里的文件是怎么被转存、解析成下载地址并落到 OSS 的 / 转存下载链路的进程跑在哪台机器，队列和账号池在 redis 哪些键 / 怎么检查转存下载链路是否通畅，脚本在哪 / 为什么 share_download_resolve_link 一直报 InvalidParameter.RefreshToken
- knowledge/architecture-spider-队列约定.md | medi | 2026-09-12 | SPIDER 队列 v2（2026-09-04 起）的固定队列名、去重键、消费者并发度与通用队列（gateway_v2）命名空间约定；写新队列消费者或排查任务… | 队列、队列v2、resourcePreCheck
  ? 我要写新的网关队列消费者，代码放哪 / 关键词站点怎么收关键词 / 爬虫怎么提交链接给网关
- knowledge/concept-术语表.md | medi | 2026-09-12 | 代码里高频出现的缩写、字段含义与命名来历，避免误读 | 术语、bnd、valid
  ? bnd / ali-share / quark / xunleipan 是什么，字段什么意思 / 任务队列 seq / 永久失败是什么含义
- knowledge/domain-bootstrap吞吐实测数据.md | medi | 2026-09-12 | P4 全量 bootstrap（作业 id=8）巡检各轮实测的 copy_parent/copy_child/建库吞吐数值（docs/s），供估算完成时间时查… | bootstrap、copy_parent、copy_child
- knowledge/domain-站点-kkpans.md | medi | 2026-09-12 | kkpans 的公开 JSON API、分页陷阱、数据规模与采集范围（只采 quark/xunlei/baidu 4295 条）；爬虫已于 2026-09-0… | kkpans、KK网盘、站点调研
  ? kkpans / KK网盘 / 光鸭云盘是什么站，接口在哪 / bbs_kkpans 爬虫实现在哪
- knowledge/domain-站点-misoso.md | medi | 2026-09-12 | misoso.cc 实际抓取域名是 melost.cn；sitemap 有"过期快照"与"越界文件假200"两个陷阱；爬虫已于 2026-09-03 实现为 … | misoso、melost.cn、影盘社
  ? misoso / melost.cn 域名不一致是怎么回事 / misoso sitemap 有什么陷阱
- knowledge/reference-github-oauth配置.md | medi | 2026-09-12 | 两个GitHub OAuth App(prod/dev)的名称、client_id、管理页、已注册回调列表与组织第三方应用策略, 不含任何secret | GitHub OAuth App、client_id、redirect_uri
  ? GitHub OAuth App 的 client_id 在哪查 / 1second 组织的回调地址怎么配置

## sessions/ (33 个, 仅列最近 3 个; 其余用 mem.py search 找)
- sessions/2026/2026-09-13-cdp3挂NAS与持久化会话.md | medi | 2026-09-13 | 2026-09-13 13:00~14:45：按用户要求给 nc-app-prod-cdp3 挂 NAS 并实现 extensions=/profile=/定… | cdp3、NAS、CDP3DATA
- sessions/2026/2026-09-13-fc-chrome上线.md | medi | 2026-09-13 | 用户授权后一天内把 09-08 遗留的 6 项人工事项全部落地：FC 部署、共用域名路由、两条脚本路径线上全通；记录派单被分类器拦、镜像经 jenkins 中… | fc-chrome、nc-app-prod-cdp3、Tampermonkey
- sessions/2026/2026-09-13-转存下载链路体检.md | medi | 2026-09-13 | 用户要求检查"网盘分享链接文件下载"链路是否通畅；结论是链路空转且账号池全失效，沉淀了知识文件与体检脚本 | 转存下载、链路体检、refresh token

## archive/ (10 个, 已归档不列出; 需要时 mem.py search --dir archive)
