# 任务 90 结果：旧索引问题路由迁成 questions 字段

## 处理规模
- 旧 `01-index.md`「关键词索引」共 **45 个 `###` 小节**，逐节核对落点后全部处理完毕（无遗漏）。
- 实际改动 **48 个文件**（`00-overview.md`、`01-index.md` 之外；`01-index.md` 已跑 `mem.py index --write` 重新生成）。
  部分小节因同一目标文件被多个问法指向，做了合并去重；部分小节（如资源生命周期大节）拆给了多个细分目标文件。
- 在 **10 个文件**末尾追加了「## 代码位置」小节（原正文没有的旧路由代码路径，原样保留描述）：
  - `decisions/decision-2026-09-09-配置按进程拆代码而非文件.md`（补 `config_show` 用法）
  - `knowledge/architecture-queue-admin.md`（补 `alert_rules.go`/`alert_history.go`/`alert_logs.go`/`fail_window.go`/`trace.go`）
  - `procedures/troubleshooting-代理池总览无数据.md`（补 `proxy-client/{hook.go,classify.go}`、`proxy-monitor`、`proxy_admin_rpc` 契约）
  - `sessions/2026/2026-09-08-并行四任务监控与文档爬虫上云.md`（补 `trace.go`、`fc-chrome`、`doc_crawler`、`05-doc-fc-contract.md`、`fc-entry`）
  - `knowledge/architecture-spider-队列约定.md`（补 `funletu.go`）
  - `procedures/workflow-部署.md`（补 `queue_v2_cutover_finish.sh`）
  - `lessons/patterns-并行重构的分阶段切分.md`（补 `spider-common.go`/`StartQueueRemoteConsumer`）
  - `lessons/success-爬虫保活语义.md`（补 `keepalive.go`）
  - `procedures/workflow-带登录态的浏览器自动化.md`（补 `tools/stubgw`）
  - `knowledge/architecture-nc-js-qiankun与后台页面.md`（补 `packages/catalyst`）
  - 其余文件旧路由里的代码路径检查后**已在正文存在**，未重复追加。

## 落点核对方式
用 `mem.py search`/`grep -rl` 逐条确认现在的落点，主要迁移结果：
- `architecture-spider.md` §队列约定 → 已拆到独立文件 `knowledge/architecture-spider-队列约定.md`（沿用该拆分，问法按内容分流到两个文件）。
- `architecture-nc-js.md` §7、§5 → 已拆到 `architecture-nc-js-qiankun与后台页面.md`、`architecture-nc-js-网关对接.md`，问法按内容分流。
- `haisou_probe.py`/`haisou_client_context.py`/`haisou_watch.py` 等代码引用、`notify_admin` 邮件通道示例 → 已随 haisou 下线归档到 `archive/2026/haisou-代码落地与探路记录.md`，questions 加在此文件而非仍在用的 `lessons/failure-haisou搜索接口收紧.md`（后者只留复现/归因类问法）。
- `sessions/2026-09-08-res_lc数据纳入后台.md` 一节：确认任务 80 已把内容提炼进 `knowledge/architecture-api.md` 与 `knowledge/architecture-nc-js-qiankun与后台页面.md`，本次只需给这两个文件补 `questions`，未再改 session 文件本身。
- 资源生命周期大节按子问法拆给了 9 个具体文件（决策、ES 现状、3 个 bootstrap 失败经验，未额外改 3 个 P4 sessions——它们已被同名 lesson 文件覆盖，判断为冗余未加 questions）。

## 待提炼清单（找不到专门知识文件，只能挂在会话记录上）
两类问法目前没有独立的 knowledge/procedures 文件承接，questions 与代码位置都加在了
`sessions/2026/2026-09-08-并行四任务监控与文档爬虫上云.md` 上：
1. **链接追踪**（一条链接为什么没入库/完整时间线）——`trace.go` 已实现但 `architecture-queue-admin.md` 正文未提；本次只补了代码位置，未把机制写进正文（超出本任务允许改动范围）。
2. **云端 Chrome / FC 上跑浏览器 / 文档爬虫上云**（doc_crawler/fc-chrome）——同样没有专门的架构文件。
建议后续任务把这两块从会话记录提炼成独立 `knowledge/` 文件，再把 questions 迁过去。

次优但可用的落点（未列为"待提炼"，仅记录取舍）：
- "代理池监控 / Scene 是什么" 系列问法落在 `procedures/troubleshooting-代理池总览无数据.md`（偏故障排查向），因为目前没有独立的代理池架构知识文件；已顺带补全该文件缺的代码位置（hook.go/classify.go/契约包）。

## 未找到落点的小节
无（45 个小节全部找到了现存文件或会话文件承接）。

## 校验
- 48 个改动文件 Front Matter 用 `python3 -c yaml.safe_load(...)` 全部校验通过，`questions` 均为 3~6 条以内的列表（多数 2~5 条）。
- `python3 scripts/mem/mem.py index --write`：已重新生成 `01-index.md`（17669 字，108 文件）。
- `python3 scripts/mem/mem.py lint`：剩 2 条，均非"元数据缺失"/"悬空引用"（本任务的硬性红线）：
  - `[常驻超长] 01-index.md: 17669 字 > 15000`（索引是生成物，字数随全库 questions/关键词增长，超出范围不在本任务可处理）
  - `[超长] knowledge/architecture-nc-js-qiankun与后台页面.md: 8148 字 > 8000`（本次只追加了 questions + 1 行代码位置约 150 字，把该文件从临界值推过阈值；未做正文改动/拆分，超出本任务授权范围，留给后续瘦身任务处理）

## 疑问/取舍
- 部分文件（如 `current/risks.md`、`current/open-questions.md`）questions 只写了 1 条——原路由本身问法单一，未强行凑够 3 条。
- `decisions/decision-2026-09-04-队列v2统一走网关.md` 与 `lessons/patterns-并行重构的分阶段切分.md` 都涉及 `spider-common.go`/`CommitResLink`，代码位置只补在了后者（原路由该代码路径明确挂在"多个包同时重构"一节下）。
