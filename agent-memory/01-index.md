---
title: 记忆索引（脚本生成）
type: index
status: active
created_at: 2026-09-02T10:55:00+08:00
updated_at: 2026-09-16T10:21:00+08:00
priority: critical
keywords: [索引, 导航, 启动包, mem.py]
summary: 由 scripts/mem/mem.py index --write 从各文件 Front Matter 自动生成，禁止手工编辑；改 summary/keywords/questions 后重新生成
load: always
---

# 记忆索引（脚本生成，勿手改）

本文件 = `scripts/mem/mem.py boot --kw 3` 的输出快照。找文件先看这里；找不到就 `mem.py search <自然语言问题>`；
定位到文件后 `mem.py outline <file>` 看章节，再 `mem.py body <file> --section <标题>` 只读需要的一段。
维护方式：改目标文件 Front Matter（summary / keywords / questions），然后运行 `scripts/mem/mem.py index --write`。

# agent-memory 启动包（脚本生成, 164 文件）— 格式: 路径 | 优先级 | 更新 | summary | 关键词; ? 后为该文件能回答的问题

## 根目录 (3)
- 00-overview.md | crit | 2026-09-16 | 网盘资源取证系统的最小启动上下文：五仓库职责、数据链路、最近 7 天状态、在生效的决策与经验，以及怎么用 mem.py 找其余记忆文件 | 网盘资源爬取、版权取证、COMMON
- 03-project-context.md | crit | 2026-09-15 | 五个仓库（4 个 Go + 1 个前端）的磁盘路径、module 名、职责、相互依赖与 go.mod replace 现状 | 仓库、module、replace
  ? 各仓库的职责分别是什么 / go.mod replace 现状是怎样的
- 02-user-preferences.md | high | 2026-09-15 | 用户对语言、脚本沉淀、记忆维护、thinking 长度、敏感信息禁写、任务进度与异常必须及时邮件汇报（scripts/mail/notify.py），以及删除… | 偏好、中文、邮件汇报

## current/ (6)
- current/tasks.md | crit | 2026-09-16 | 仍在推进/阻塞/待决策：站点发现 5 站待立项、文档发现待批量执行、腾讯文档与十项提案待确认合并、P5 灰度爬坡、误删事故收尾；长尾在 tasks-backl… | 任务、进度、待办
  ? 当前该做什么，有哪些待办
- current/open-questions.md | high | 2026-09-16 | 待裁定：站点发现 5 站立项、lzpanx robots；转存账号池续期 | 待确认、站点发现、lzpanx
  ? 当前有哪些待用户确认的问题
- current/risks.md | high | 2026-09-16 | 影响开发与运维安全的已知风险点；最高 R9 lifecycle_checker 误删 115.6 万资源（修复已上线、恢复待决策） | lifecycle_checker误删、风险、阻塞
  ? 密钥、安全相关的风险在哪看
- current/proposals-需求与优化候选.md [draft] | medi | 2026-09-16 | 12 条候选需求；09-16 用户裁定第 3~12 项已开发，取证包/软删两项未做 | 需求候选、优化提案、取证包
- current/changelog.md | low | 2026-09-16 | 按日期倒序的一句话变更流水，每条指向 session/decision 文件；回答"某事哪天做的、细节在哪 | 变更记录、changelog、历史
- current/tasks-backlog.md | low | 2026-09-16 | 从 tasks.md 拆出的低优先级/等人工/归档遗留事项：文档爬虫 FC 6 项人工步骤、归档任务遗留待办、P3 代码小修、2026-09-16 移入的 P… | backlog、P3、文档爬虫

## decisions/ (19)
- decisions/decision-2026-09-02-停止磁力资源采集.md | crit | 2026-09-02 | 项目现只采集 4 种网盘类型资源，不再采集或入库磁力/BT 资源；存量索引与接口保留 | 磁力、torrent、magnet
- decisions/decision-2026-09-03-全站扫描不在启动时触发.md | crit | 2026-09-03 | 全量扫描完成后把时间写进 redis；启动时检查该时间，有则跳过全量，只跑增量 | 全站扫描、全量、启动
- decisions/decision-2026-09-04-资源索引生命周期改造方案.md | crit | 2026-09-12 | 用短周期(cur/prev)+长周期三索引与 MySQL 分表元数据替代单大索引的失效清理方式；两套方案共存、v3 接口切换、双写保回滚 | 生命周期、lifecycle、三索引
  ? 资源生命周期改造方案是什么，为什么用三索引 / res_lc 是什么，双写和 v3 接口是怎么回事 / 索引轮换/失效检测怎么改造的
- decisions/decision-2026-09-09-配置按进程拆代码而非文件.md | crit | 2026-09-16 | 用户 2026-09-09 纠正——"配置按服务拆分"指每个进程用自己的配置结构体与 Get(), 禁止导出 config.Config, 配置文件保持一份;… | 配置拆分、拆代码、角色包
- decisions/decision-2026-09-12-记忆系统瘦身与脚本化加载.md | crit | 2026-09-12 | 记忆常驻体积曾达 5.4 万字；已执行：索引改由脚本从 Front Matter 生成、问句路由迁成 questions 字段、词法+语义混合检索、总览 4.… | 记忆系统、token、启动包
  ? 记忆太大，启动 token 太多怎么办 / mem.py 索引怎么生成
- decisions/decision-2026-09-03-下线haisou.md | high | 2026-09-15 | haisou.cc 被站点端点级拦截且单 IP 产出上限极低，决定下线；代码保留、默认不启动、探路 cron 撤除 | haisou、下线、13001
  ? haisou 为什么下线 / haisou 还能不能复活
- decisions/decision-2026-09-03-清理下线爬虫代码.md | high | 2026-09-12 | 以 `./deploy.sh ps` 的线上进程为唯一判据，删除 21 个已不在线的爬虫命令及其代码与配置，保留 haisou | 清理、下线爬虫、deploy.sh ps
  ? 哪些爬虫还在跑，怎么判断 / 某个爬虫代码去哪了，为什么被删了 / 想恢复一个老爬虫怎么办
- decisions/decision-2026-09-04-前端合并为spiderAdmin.md | high | 2026-09-04 | 两个后台子应用合并成 admin/spiderAdmin 并重做左侧栏布局，全应用只保留一条 RTC 连接 | spiderAdmin、NC-JS、子应用合并
- decisions/decision-2026-09-04-管理服务并入网关.md | high | 2026-09-04 | queue_admin 由独立进程并入 spider_gateway，日后管理类需求一律放 services/gateway 之下，不增新进程 | queue_admin、网关、进程合并
- decisions/decision-2026-09-04-队列v2统一走网关.md | high | 2026-09-16 | SPIDER 跨进程任务投递统一从直连 redis 改为经网关队列 v2；收尾无回滚路径 | 队列v2、queue_task、res_scheduler
- decisions/decision-2026-09-08-后台登录改为github-oauth.md | high | 2026-09-12 | 固定管理秘钥改为 GitHub OAuth 登录并校验 1second 组织成员身份的四个关键设计取舍与原因 | GitHub OAuth、后台登录、RtcToken
  ? 后台登录为什么改成 GitHub OAuth / 管理秘钥去哪了，needLogin/githubClientId 是什么
- decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md | high | 2026-09-12 | 用户 2026-09-12 采纳 D1~D4——旧链路失效只提前 lc 复检、重合度改语料级三项、bnd 去 has_child、门槛全过才切流；阶段 A/B… | P5、准入门槛、legacy→lc 失效同步
  ? 切 v3 前必须满足哪些门槛 / 旧链路判失效为什么只提前复检而不直接置 lc 失效 / bnd 搜索在 v3 慢的原因与修法
- decisions/decision-2026-09-12-弃用文档更新类接口.md | high | 2026-09-16 | 用户 2026-09-12 确认——report/likes/dislikes/addViews 这类频繁 update ES 文档的接口已弃用，不做 v3、… | 弃用、addViews、likes
- decisions/decision-2026-09-12-阶段D改由API侧自动灰度分流.md | high | 2026-09-15 | 用户 09-12 裁定：API 在 /api/v2/search 服务端按比例走 v3，30% 起、无异常每 100 个 v3 请求 +1% 到全量，异常自动… | 阶段D、灰度、分流
  ? 搜索流量怎么从 v2 切到 v3，谁来切 / search_canary 是什么，比例怎么涨、异常怎么回滚
- decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md | high | 2026-09-16 | cdp3 的 profile=<ns>/<name> 持久化会话（NAS 锁）、extensions= 扩展机制与 Browser.close 收尾约定 | cdp3、CDP3DATA、CDP3TEMP
  ? cdp3 的扩展和会话数据放在哪、目录怎么约定 / 调用方用 profile= 时要注意什么
- decisions/decision-2026-09-13-lint长度双阈值.md | high | 2026-09-13 | 超长改为 >12,000 触发、触发后必须压到 <6,000，9,000 起只提示；避免 8,000 单线反复报警 | lint、超长、双阈值
  ? lint 报超长该压到多少字，上限为什么不是 8000 / tasks.md 反复超长怎么办
- decisions/decision-2026-09-16-搜索p90告警关闭匿名搜索与总览数据源.md | high | 2026-09-16 | 2026-09-16 用户需求裁定：搜索总览走 SLS(SQL 优先、拉日志降级)；p90 超阈值由网关 leader 巡检→邮件+共享 redis 键关闭匿… | search_guard、匿名搜索、p90
  ? 匿名搜索为什么会被关闭, 谁关的, 怎么手动开放 / 搜索总览/Top 榜的数据从哪来, SLS SQL 不可用怎么办 / 分享链接总览的新增/检测/更新/失效各是什么口径
- decisions/decision-2026-09-16-阿里云盘空目录分享判定为有效.md | high | 2026-09-16 | 阿里云盘 file_count==0 时新旧实现结论不同，裁定判 Valid（无业务码不主动认定失效） | panvalid、阿里云盘、file_count
- decisions/decision-2026-09-04-合并sweep-guard分支冲突取舍.md | medi | 2026-09-04 | 合并遗留分支时，master 已修正的旧逻辑不应因"冲突两边都保留"而被恢复，需先判断冲突是否为真实的两个功能重叠 | sweep-guard、全量扫描守卫、merge 冲突

## procedures/ (15)
- procedures/checklist-不可逆操作上线.md | crit | 2026-09-13 | [用户确认 2026-09-13] 数据误删事故后的硬规则：任何删除/清理/判失效等无法撤销的功能，上线前必须先在线上跑 dry run，再用与新功能无关的独… | 不可逆操作、dry run、二次复核
  ? 要上线一个会删数据/判失效/清理的功能，上线前必须做什么 / dry run 的结果怎么复核，能不能用新功能自己的日志当依据 / 什么时候才允许正式开启删除类功能
- procedures/workflow-fc-chrome上线.md | high | 2026-09-16 | fc-chrome 上线链路：本机构建 → docker save/rsync → ACR 推镜像 → s deploy → 共用域名路由 → 健康检查与真实… | fc-chrome、serverless-devs、ACR
- procedures/workflow-任务进度邮件汇报.md | high | 2026-09-16 | 用户常不在电脑旁：长任务的开始/里程碑/完成、任何异常或阻塞都要主动用 scripts/mail/notify.py 发 Markdown 渲染的 HTML … | 邮件汇报、notify.py、进度
  ? 任务进行中什么时候该给用户发邮件 / 进度/异常邮件怎么写、用什么脚本发 / 用户不在电脑旁怎么通知他
- procedures/workflow-子agent任务简报.md | high | 2026-09-12 | 派子 Agent 时任务描述落盘成文件、prompt 只给路径，并列出子 Agent 的常见失败模式与提示词对策 | 子agent、任务描述、agent-tasks
  ? 我要派子 Agent，任务描述太长怎么办 / 多个 agent 上下文重复怎么解决
- procedures/workflow-并行多任务开发与合并预演.md | high | 2026-09-16 | 简报落盘 → new_worktree_all 建跨仓库 worktree → 并行派单 → 逐线验收/返工 → integration_check 合并预演… | 并行开发、worktree、合并预演
  ? 用户让我并行开发多项需求、合并前确认，标准流程是什么 / 合并前怎么提前发现冲突并验证编译
- procedures/workflow-并行开发多站点爬虫.md | high | 2026-09-15 | 一次接入多个新站点时的分工方式：worktree 隔离、共享资源集中准备、冲突面收敛、合并与验收 | 并行开发、worktree、子agent
  ? 我要一次接入多个站点，worktree 怎么分工 / 多站点并行开发怎么处理合并冲突
- procedures/workflow-文档发现.md | high | 2026-09-16 | `task doc-discovery` 的入口、验收口径、渠道性价比与硬规则；流程与脚本在 COMMON site-discovery/tools/docf… | 文档发现、doc-discovery、docfind
  ? 怎么找包含网盘链接的在线文档 / task doc-discovery / 启动文档发现任务 该怎么做 / 文档发现的候选渠道有哪些、哪个性价比高
- procedures/workflow-新站点调研.md | high | 2026-09-12 | 接到"探索某资源站并输出爬虫 PRD"时的标准步骤：先找结构化接口，再验证全量可枚举性，最后对账 | 站点调研、爬虫、PRD
  ? 我要调研一个新的资源站，怎么写爬虫 PRD / 怎么找一个站点的公开接口
- procedures/workflow-本地构建与验证.md | high | 2026-09-16 | 四仓库编译命令、CI(vet/test 白名单 + live 标签隔离连生产测试)、make proto 生成流程与验收口径 | CI、go build、go vet
  ? 编译不过，依赖报错怎么排查 / CI 怎么跑，哪些测试会连生产
- procedures/workflow-站点发现.md | high | 2026-09-16 | `task site-discovery` 的入口、候选渠道、worktree 执行方式与两轮踩坑；正文流程在 site-discovery/README.md | 站点发现、site-discovery、候选站点
  ? 怎么启动网站发现任务，在 worktree 里怎么跑
- procedures/checklist-仓库脚本清单.md | medi | 2026-09-16 | MEMORY 仓库 scripts/ 下可复用脚本一览（git-hooks 提交信息违禁词钩子、claude-rc systemd 托管 Remote Con… | scripts、邮件汇报、notify.py
- procedures/troubleshooting-代理池总览无数据.md | medi | 2026-09-16 | 后台代理池页全 0 时三步定位：网关 dataSource → 上报侧是否部署 → tools 探针 | proxy-admin-check、代理池总览、proxy_admin
- procedures/workflow-密钥治理约定.md | medi | 2026-09-16 | 四仓库密钥约定：测试凭据 *.hide.json、配置 ${VAR} 环境变量覆盖、gitleaks 三件套；自定义规则与 [extend] 同用会静默失效 | 密钥治理、gitleaks、hide.json
- procedures/workflow-带登录态的浏览器自动化.md | medi | 2026-09-12 | 如何启动/复用一个带登录态的调试Chrome并用CDP脚本驱动它, 含"默认profile会被安全策略拦截"的前提坑 | agent-browser、cdp.py、CDP
- procedures/workflow-部署.md | medi | 2026-09-16 | SPIDER deploy.sh 的常规用法、服务到主机的映射、现役服务判据、新服务选主机、配置分发与安全提醒；历次上线踩坑记录已归档到 archive/20… | auto模式、权限分类器、部署

## lessons/ (33)
- lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md | crit | 2026-09-15 | checker 用 task.Id(md5) 而非 ShareId 探测，115.5 万条 quark/ali 误删；bnd 再因「违规」tooltip 误判… | lifecycle_checker、误删、dry run
  ? lifecycle_checker 为什么把夸克资源全判失效 / 116 万条资源误删是怎么回事，怎么恢复
- lessons/failure-FC实例在WebSocket断开后立即冻结.md | high | 2026-09-16 | 客户端断开 WebSocket 后 FC 立即冻结实例，收尾/写回必须在连接内完成（拦截 Browser.close） | FC 冻结、WebSocket、Browser.close
- lessons/failure-SLS字段检索按分词匹配误命中其他stage.md | high | 2026-09-16 | SLS 检索 `field:value` 是分词匹配，同一 logstore 里 `stage=GET:/api/v2/search` 的访问日志会被 `st… | SLS、分词、字段检索
  ? 用 SLS 按 stage/字段值统计时为什么数字翻倍或出现 null 行 / SLS 检索语句怎么做字段精确匹配
- lessons/failure-link3接口按IP限流直连百次即429.md | high | 2026-09-16 | link3 no_auth/user 接口按 IP 限流，直连约 100 次即 429；批量必须走代理池，代理少时改用 search_user 关键词定向搜博主 | link3.cc、429、限流
  ? link3.cc 批量抓主页为什么 429，怎么绕 / 代理池只有几个 IP 时 link3 全量该怎么跑
- lessons/failure-ncjs构建脚本会自动上传OSS.md | high | 2026-09-04 | admin/*子应用的标准 `pnpm build` 脚本默认会把 dist 上传到生产 OSS 并改写 apps.json, 验证构建前必须先用 { dep… | NC-JS、pnpm build、mfe插件
- lessons/failure-notify脚本静默降级把原始Markdown发成邮件.md | high | 2026-09-16 | notify.py 被 miniforge python 执行时缺 markdown 模块静默降级，原文当 <pre> 发出；一律走 shebang 系统 p… | notify.py、邮件汇报、Markdown未渲染
  ? 邮件里为什么收到的是原始 Markdown 而不是渲染后的卡片 / 脚本用 env python3 有什么坑 / 依赖缺失时脚本该怎么降级才不会坑用户
- lessons/failure-proto3零值与负一哨兵冲突.md | high | 2026-09-12 | proto3 标量字段不传时零值是 0，若 0 恰好是合法业务值、而"不过滤"哨兵定成 -1，前端漏传就会静默查错数据且不报错 | proto3、零值、哨兵
  ? 筛选参数传了 0 却查不出数据 / proto3 不传字段被当成过滤条件是什么坑
- lessons/failure-qiankun子应用挂到包裹层导致样式被清空.md | high | 2026-09-12 | 子应用 Vue app.mount 直接挂 qiankun 包裹层会把 <qiankun-head> 内联的全部静态 CSS 删掉(只在线上/被 qianku… | NC-JS、qiankun、微前端
- lessons/failure-resdb的ES端点指向已下线集群.md | high | 2026-09-16 | STORAGE worker 所在 osec-resdb 的 ES 地址指向已下线集群，旧代码静默失败；排查与修法见正文 | osec-resdb、es_endpoint、ES 集群更换
- lessons/failure-v3首页重合度受前缀展开分片彩票影响.md | high | 2026-09-12 | P5 对拍首页重合度 84%<95% 的两个根因——4% 坑位是 legacy 已删 lc 未删的死链（无反向失效同步）；其余是 match_phrase_p… | P5、重合度、match_phrase_prefix
  ? P5 对拍为什么没通过，v3 首页和 v2 为什么不一样 / dfs 能不能让新旧索引排序一致 / 旧索引 url_check 删掉的文档新方案会同步失效吗
- lessons/failure-前端环境默认值写死本地.md | high | 2026-09-16 | 子应用把 gwEndpoint 默认值写死成本地地址导致线上首访连错；默认值必须由 location.hostname 推导 | gwEndpoint、gwAddrs、defaultGwAddr
- lessons/failure-品牌版Chrome禁用load-extension与userScripts二次授权.md | high | 2026-09-16 | 品牌版 Chrome 不吃 --load-extension 且 userScripts 需二次授权；改企业策略强装 + 预热 profile，@match … | Chrome、load-extension、ExtensionSettings
  ? headless Chrome 加了 --load-extension 为什么看不到扩展 / 油猴脚本装上了但页面不执行是怎么回事
- lessons/failure-把拆配置理解成拆文件.md | high | 2026-09-09 | 用户说"拆分"时先确认拆的是什么(代码结构/文件/进程); 用运行时断言或"文件里不写某项"来保证隔离, 通常说明方案层级选错了 | 需求理解、拆分对象、复述确认
- lessons/failure-握手回包附加字段被传输层丢弃.md | high | 2026-09-16 | 网关握手 403 回包的附加字段被 RTC-gRPC 传输层丢弃；附加信息要走独立通道 | RtcTransport、cancelAllPendingCalls、UnaryCallResponse
- lessons/failure-旁路能力初始化拖垮主流程.md | high | 2026-09-09 | 用会 log.Fatal/panic 的基础设施函数去初始化"可有可无"的监控, 会让每个子命令随配置缺失或 redis 抖动一起死; 以及埋点只覆盖成功路径… | db.Redis、log.Fatal、panic
- lessons/failure-本地代理池薄导致连接失败误判为站点拒绝.md | high | 2026-09-16 | 代理池薄时 code=0 像站点拒绝；直连复核 + ratetest 双出口对比，只有 403/429 才算限流 | 代理池、RemoteDisconnected、code=0
  ? 调研站点时经代理大量连接失败，怎么分辨是代理问题还是站点封锁 / 单 IP 吞吐怎么测才不被代理池噪声干扰
- lessons/failure-注入脚本用consolelog回传被页面自身替换吞掉.md | high | 2026-09-16 | 页面自身代码会整体替换 window.console.log；注入脚本必须在最开头抓原生引用回传，否则只见一条 start 后沉默 | console.log、CDP、addScriptToEvaluateOnNewDocument
  ? CDP 注入脚本为什么只打出第一条日志就沉默 / 用 console.log 回传协议什么情况会全部收不到
- lessons/failure-网关重启暴露ES集群已更换.md | high | 2026-09-12 | 线上网关自 1 月未重启，期间 ES 集群已更换；队列 v2 上线一重启就 panic。教训：长期不重启的服务会掩盖外部依赖变更，重启前先在目标主机验证配置里… | 网关、gateway、ES
  ? 网关起不来，报 no such host 怎么查 / 重启网关前要检查什么
- lessons/failure-配置v2二进制无本地回落导致老容器重启即挂.md | high | 2026-09-16 | v2 二进制只认 OSS_CONFIG_URL/LOCAL_CONFIG_PATH 不读宿主机旧配置，老容器重启即挂；需本地回落 | 配置 v2、OSS_CONFIG_URL、config.yaml
- lessons/failure-验收部署脚本时误连生产主机.md | high | 2026-09-16 | 验收 deploy.sh 时漏加 --dry-run 又用真实主机名，只读命令也真连上了生产；一律用假主机名或 --dry-run，没有只读例外 | deploy.sh、--dry-run、ssh 生产主机
  ? 验收/测试新写的部署脚本子命令要注意什么
- lessons/patterns-并行多角色开发的验收与集成.md | high | 2026-09-16 | 9 条线 5 仓库并行改造的复盘：断网跑测试、假主机名、逐线验收、合并预演；验收抓到的典型漏项（漏传字段、按字段名盘点漏值、缺 dry-run、只迁一半） | 并行开发、子agent、验收
  ? 多个子 Agent 并行改多个仓库时怎么提前发现冲突、怎么保证测试不连生产 / 验收 Agent 最常抓到开发 Agent 哪些漏项
- lessons/patterns-并行重构的分阶段切分.md | high | 2026-09-12 | 多个包同时改造且互相引用时，用"主会话先做共享契约 → 子 Agent 只加不删 → 单独清理 Agent 收尾"三阶段避免编译互锁 | 并行重构、子agent、worktree
  ? 多个包同时重构，子 Agent 怎么避免编译互锁 / Phase 0/1/2 怎么切分任务
- lessons/patterns-统计ES索引先查文档形态.md | high | 2026-09-05 | 同一索引可能混着两代写入形态；只按 join=resource 统计会漏掉三分之二资源，任何统计/迁移前先做 exists/must_not exists 对账 | ES、join、nested
- lessons/patterns-长周期生产巡检.md | high | 2026-09-15 | 派子 Agent 做数小时生产巡检的可操作清单（原 98 条经验按主题压缩）：前台等待、隧道 keepalive、复制阶段用 _count 差分而非 prog… | 巡检、bootstrap、子Agent
- lessons/success-本地代理池打通.md | high | 2026-09-15 | 本地怎么用上代理池、三个会让人查错方向的坑，以及验证方法 | 代理池、蜻蜓代理、白名单
  ? 代理池连不上怎么办，本地怎么用上代理池 / 蜻蜓白名单/出口IP不对怎么查
- lessons/success-桩网关加cdp浏览器做登录链路联调.md | high | 2026-09-12 | 涉及浏览器交互的改造仅靠静态审查+单测不足以验收, 要造一个只保留被测链路的桩服务并用带登录态的调试浏览器实测, 本次靠它抓到两个"代码看起来完全正确"的阻断… | 桩网关、stubgw、CDP
  ? 桩服务验收怎么做，为什么静态审查+单测不够
- lessons/success-爬虫保活语义.md | high | 2026-09-12 | 保活续期的唯一判据是"有新链接真正提交成功"，轮次成功不算；顺带修掉 keepalive 包读 nil channel 挂死的隐患 | keepalive、保活、CommitResLink
  ? 保活 keepalive 该在哪调 / 爬虫空跑为什么不告警
- lessons/success-爬虫联网集成测试.md | high | 2026-09-12 | 用「假 committer + 独立 redis 键前缀 + 环境变量开关」让爬虫的联网测试可重复运行且不污染线上 | 集成测试、爬虫、联网测试
  ? 我要给爬虫写测试，联网测试怎么不污染线上
- lessons/success-网盘失效判定原则.md | high | 2026-09-12 | 靠 message 文案匹配判定网盘失效必然随站点文案漂移而失灵，应改用业务码并把未知响应升级为 error | 失效判定、业务码、限流
- lessons/failure-fc-chrome上线踩坑合集.md | medi | 2026-09-16 | fc-chrome 上线一天里踩到的镜像/策略/域名/NAS/超时等坑与各自修法的合集 | /json/list、pkill -f、docker exec
- lessons/failure-端到端复用旧托管进程导致注入旧脚本.md | medi | 2026-09-16 | 2026-09-16 验证腾讯文档脚本时 fc-chrome 路径无任何回传、直连 CDP 却全通——根因是 e2e 脚本"端口有响应就复用"复用了托管旧 d… | fc-chrome、端到端验证、缓存
- lessons/success-cdp3策略强装扩展与NAS持久化profile.md | medi | 2026-09-16 | 品牌版 Chrome 用企业策略 force_installed 装扩展 + 预热 profile 存 NAS 复用登录态 | 扩展安装、ExtensionSettings、override_update_url
- lessons/success-在线文档解析优先用页面自带接口.md | medi | 2026-09-16 | 解析 SPA 文档站优先 fetch 页面自带接口：performance 资源列表 + 全局变量 + bundle 搜路径常量找到分页接口，比啃 DOM/r… | 在线文档、内部接口、performance.getEntriesByType

## knowledge/ (26)
- knowledge/architecture-系统总览.md | crit | 2026-09-02 | 从爬取到入库到检索的完整链路、各服务端口与中间件分工 | 架构、数据链路、网关
- knowledge/api-rpc契约.md | high | 2026-09-12 | COMMON 仓库中各 proto 服务的方法清单、核心消息结构与代码生成流程 | proto、gRPC、StorageRpc
  ? 我要改 gRPC 协议 / proto，改完怎么生成 / 某个 rpc 方法的入参/出参消息结构是什么 / proto 改完要同步哪些下游仓库
- knowledge/api-v3-detail-filectx兼容性分析.md | high | 2026-09-16 | lc 索引结构与 v2 detail/fileCtx 查询方式兼容（nested 父子），v3 可复用同一 bndApi | v3 detail、fileCtx、res_lc_all
- knowledge/architecture-api.md | high | 2026-09-16 | osec-resource-api 的路由表、中间件链、依赖服务与后台管理模块；另含 SPIDER 网关 LifecycleRpc 新增的 res_lc 分表… | API、osec-resource-api、gin
  ? 我要改查询接口/限流/搜索 / 后台怎么看 res_lc_* 分表数据
- knowledge/architecture-es索引现状.md | high | 2026-09-12 | 阿里云 ES 6.7 单索引的分片/容量/父子文档结构/入库增速与读写清理链路代码位置，是生命周期改造方案的事实基线 | ES、Elasticsearch、6.7
  ? 生产 ES 有多大，怎么查生产 ES / 无 join 索引和 join 父子索引的区别
- knowledge/architecture-fc-chrome文档爬虫上云.md | high | 2026-09-16 | nc-app-prod-cdp3（COMMON fc-chrome，Chrome 153 + Tampermonkey）的地址、/cdp3/* 路由、OSS … | fc-chrome、nc-app-prod-cdp3、Tampermonkey
  ? 新版 FC Chrome 部署在哪、地址、健康检查 / cdp3 的 NAS 目录/extensions=/profile= 怎么用
- knowledge/architecture-nc-js-qiankun与后台页面.md | high | 2026-09-16 | qiankun 主应用注册/子应用生命周期、本地开发流程；spiderAdmin 新增后台页面写法与落点（队列监控、资源生命周期各页、架构图页、res_lc … | qiankun、微前端、spiderAdmin
  ? 后台前端加一个页面该怎么加 / qiankun 子应用 / apps.json 是什么 / 后台哪里看 res_lc_* 分表数据
- knowledge/architecture-nc-js-网关对接.md | high | 2026-09-16 | NC-JS 后台前端与 SPIDER gateway 之间没有 REST，只有 WebRTC DataChannel 上自实现的 gRPC 传输；鉴权已改 G… | WebRTC、gRPC、protobuf-ts
- knowledge/architecture-nc-js.md | high | 2026-09-12 | NC-JS 前端 mono repo 的仓库定位、工程栈、分包布局（admin/*、packages/*）与构建/OSS/Cloudflare 部署机制；qi… | NC-JS、前端、pnpm
- knowledge/architecture-queue-admin.md | high | 2026-09-15 | 队列 v2 的监控管理系统：已并入网关进程的架构、端口、schema 解耦机制、抢主锁、巡检工具与已知数据缺口 | queue-admin、队列监控、QueueAdminRpc
  ? 队列告警怎么配，阈值多少，历史在哪看 / queue-admin 队列出问题怎么看，端口连不上怎么办
- knowledge/architecture-search-admin.md | high | 2026-09-16 | 网关 search_admin 模块（SLS 搜索日志聚合、p90 巡检→邮件+关闭匿名搜索、redis 键约定、SQL/扫描双路径）与 lifecycle.… | search_admin、SearchAdminRpc、搜索总览
  ? 后台搜索总览/Top 榜数据从哪来, source=sls-scan 是什么意思 / 匿名搜索被关闭了怎么回事, 在哪手动开放/调阈值 / 分享链接总览的检测数为什么早期是 0, 新增按来源怎么算
- knowledge/architecture-spider.md | high | 2026-09-15 | osec-spider-go 的入口子命令、目录分层、编译状态、bnd_resolver 关键类型、写新爬虫可复用要点（含配置节 yaml/Duration/… | SPIDER、osec-spider-go、爬虫
  ? 我要改爬虫/加站点，该看哪个子命令 / 新增配置节 yaml 怎么解析 Duration / 泛型队列 PushTask 怎么写，seq/永久失败是什么
- knowledge/architecture-storage.md | high | 2026-09-12 | enfi-resource-storage 的三个子命令、写入流程、ES 索引名与幂等策略 | STORAGE、enfi-resource-storage、入库
  ? 我要改入库逻辑，查资源为什么没写进去 / ES 索引幂等/version 判重是怎么回事
- knowledge/domain-在线文档免登录取数.md | high | 2026-09-16 | 腾讯 opendoc(sheet 逐 tab、zlib 分块)/飞书 SSR/石墨 lizard-api/金山 WPS JSAPI 四平台匿名取正文与修改时间… | 腾讯文档、dop-api/opendoc、金山文档
  ? 腾讯文档表格/文档怎么不登录拿到全部内容和修改时间 / 金山文档、飞书、石墨能不能免登录抓正文，各用什么接口 / 腾讯 sheet 多个子表
- knowledge/domain-站点-2609接入批次.md | high | 2026-09-15 | 本批 5 个站点的形态、子命令、规模、各自的坑与实现状态；详细规格见各自 PRD | dyyjmax、fuxipan、feikuai
  ? dyyjmax/fuxipan/feikuai/kuakes 是什么站，各自的坑是什么 / 2609 批次都接了哪些站
- knowledge/domain-网盘有效性检测.md | high | 2026-09-16 | 两套有效性检测已合并为 COMMON panvalid 一套实现（分支 feat/valid-unify，未合并 master）；本文件存历史背景，权威码表/… | panvalid、有效性检测、validShareLink
  ? 链接失效检测怎么做，validShareLink 返回 -1 是什么意思 / panvalid 是什么，和旧的两套实现什么关系
- knowledge/domain-腾讯文档表格解析.md | high | 2026-09-16 | 2026-09-16 实测：公开表格匿名可访问；同源 GET dop-api/opendoc（需页面 Cookie，t/xsrf 非必需）返回 JSONP；数… | 腾讯文档、docs.qq.com、opendoc
  ? 腾讯文档表格的单元格数据从哪个接口拿、要不要登录 / 腾讯文档 opendoc 返回的 protobuf 区块怎么解 / 为什么腾讯文档有的返回 block_datas 有的返回 JSON op 数组
- knowledge/domain-转存下载链路.md | high | 2026-09-15 | SPIDER 下载调度链路的代码结构、redis 键/MySQL 表、阿里/百度解析方式、三条下载路径，以及 2026-09-13 体检结论：链路空转，阿里 … | 转存下载、share_download、resolve_link
  ? 分享文件怎么被转存、解析成下载地址落到 OSS / 转存下载链路进程/队列/账号池在哪，怎么体检
- knowledge/domain-迅雷分享爬取.md | high | 2026-09-15 | xlLoadShare 失败率修复(09-15 已上线)：顶层文件入批次、状态码按共用码表判定、空分享永久失败；失效上报仍 dry run；接口/探针/导出重… | xlLoadShare、迅雷、xunleipan
  ? xlLoadShare 失败率高是什么原因 / 怎么直接查一个迅雷分享的结构 / 迅雷失效上报 dry run 开关在哪
- knowledge/domain-飞书文档解析.md | high | 2026-09-16 | 飞书 docx/多维表格解析依据：匿名可读、client_vars/clientvars 接口与分页、objType 映射、3000 行上限、登录墙与已删除判… | 飞书文档、feishu、多维表格
  ? 飞书文档的网盘链接用哪些接口解析、怎么分页 / 飞书 wiki 怎么区分 docx 与多维表格 / 飞书文档需登录/已删除时怎么处理
- knowledge/architecture-spider-sitecrawler骨架.md | medi | 2026-09-16 | sitecrawler 骨架接口、6 站 redis 键对照、SiteCommonConfig 内嵌避坑、EngineConfig 必填字段核对表 | sitecrawler、爬虫骨架、WrapAwareSite
- knowledge/architecture-spider-队列约定.md | medi | 2026-09-16 | SPIDER 队列 v2 的固定队列名、去重键、消费者并发度与通用队列接口约定 | 队列、队列v2、resourcePreCheck
- knowledge/concept-术语表.md | medi | 2026-09-12 | 代码里高频出现的缩写、字段含义与命名来历，避免误读 | 术语、bnd、valid
- knowledge/domain-站点-kkpans.md | medi | 2026-09-12 | kkpans 的公开 JSON API、分页陷阱、数据规模与采集范围（只采 quark/xunlei/baidu 4295 条）；爬虫已于 2026-09-0… | kkpans、KK网盘、站点调研
- knowledge/domain-站点-misoso.md | medi | 2026-09-12 | misoso.cc 实际抓取域名是 melost.cn；sitemap 有"过期快照"与"越界文件假200"两个陷阱；爬虫已于 2026-09-03 实现为 … | misoso、melost.cn、影盘社
- knowledge/reference-github-oauth配置.md | medi | 2026-09-16 | 两个 GitHub OAuth App（prod/dev）的名称、client_id 存放位置、管理页与回调地址约定 | GitHub OAuth App、client_id、redirect_uri

## sessions/ (41 个, 仅列最近 3 个; 其余用 mem.py search 找)
- sessions/2026/2026-09-05-生命周期P4启动失败.md | high | 2026-09-16 | STORAGE 双机重部并核验首写继承生效, 用新工具补齐双写窗口 3551 条文档, P4 bootstrap 启动 10 分钟后因两个实现缺陷失败并停止(… | 生命周期、P4、bootstrap
- sessions/2026/2026-09-05-生命周期P4演练.md | high | 2026-09-16 | 网关双机重部热修分支成功；缺陷 A/B 在生产验证通过；新发现 copy_child 轮询瓶颈，全量未启动 | P4、bootstrap、演练
- sessions/2026/2026-09-03-并行开发6站爬虫.md | medi | 2026-09-16 | 用 4 并发子 Agent + worktree 接入 6 个站点，5 站验收通过并合并，haisou 因站点收紧未能验收 | 并行开发、worktree、6站爬虫

## archive/ (21 个, 已归档不列出; 需要时 mem.py search --dir archive)
