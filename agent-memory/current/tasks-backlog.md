---
title: 任务后备清单（低优先级 / 等人工事项）
type: task
status: active
created_at: 2026-09-12T22:36:00+08:00
updated_at: 2026-09-16T08:50:00+08:00
priority: low
keywords: [backlog, P3, 文档爬虫, FC, 人工事项]
questions:
  - 文档爬虫 FC 自动化还差哪些人工步骤
  - 有哪些 P3 低优先级待办
summary: 从 tasks.md 拆出的低优先级/等人工/归档遗留事项：文档爬虫 FC 6 项人工步骤、归档任务遗留待办、P3 代码小修、2026-09-16 移入的 P1/P2 长尾（站点复议、checker 业务码、STORAGE 回归等）
load: rarely
related:
  - agent-memory/current/tasks.md
---

# 任务后备清单

## 2026-09-08 并行四任务（监控增强 + 文档爬虫上云）—— 部分已上线，文档爬虫 FC 自动化待人工

①告警后台/队列告警可配 ②代理池后台 ③链接路径追踪 **已随 09-09 网关重启上线**（五仓库均已 push，详情见 session）。
- **④文档爬虫 FC 自动化——2026-09-13 新版 FC 已上线**（`knowledge/architecture-fc-chrome文档爬虫上云.md`、流程 `procedures/workflow-fc-chrome上线.md`，过程 `agent-tasks/2026-09-13-fc-chrome-online/99-notes.md`）：
  Tampermonkey 包/云端脚本已上 OSS，镜像经 jenkins 推 ACR，`nc-app-prod-cdp3` 部署，共用域名 `/cdp3/*` 路由生效，三处地址回填已提交；`inject=1` 路径线上对真实文档全通。
  - [x] Tampermonkey 原生路径 11:41 线上终验通过（根因 `@match` 缺 `account.kdocs.cn`）；doc-crawler 两条路径都可用，仍建议默认 `inject=1`（更快、不依赖扩展状态）
  - [ ] SLS 给 `link_key` 建索引后打开 `services.queue_admin.sls.link_key_indexed`（与 FC 无关，仍待人工）
  - [用户确认 2026-09-13] PC 端油猴调度器**不下线**，与云端 doc-crawler 并存；doc-crawler 部署主机仍待定（`deploy.sh` 占位 `osec-jenkins`）
  - [用户确认 2026-09-13] `nc-app-prod-cdp-driver` 的 `CDP_ENDPOINT` **暂不切**到新实例，继续指旧 v2；新实例先由 doc-crawler/`prod-v3` 入口使用
- 详情：`sessions/2026/2026-09-08-并行四任务监控与文档爬虫上云.md`；`agent-tasks/2026-09-08-monitoring-and-doc-fc/`；`lessons/failure-旁路能力初始化拖垮主流程.md`。


## 归档遗留待办（原分散在已归档任务块中，仍未完结）

- [ ] **P1 生命周期 P4 收尾**：2 个 `:cur` 半区窗口已于 09-12 关闭（30/30 抽样父子均在 cur、long=0，「父在 long」前提不成立，不搬）；P6 关双写前须补 v3 detail/fileCtx（结构兼容，`knowledge/api-v3-detail-filectx兼容性分析.md`）；P5 进度见「进行中」。
- [ ] **P2 排期**：巡检守护提升到 `runBootstrapJob` 级 + heap 阈值可配（0.5~1 人日）；rollout §9 待补写。
- [ ] **P2 代码待修（配置 v2）**：`LOCAL_CONFIG_PATH` 缺省未回落宿主机 `config.yaml`；删宿主机 `config.yaml` 的时机（回滚现依赖 `spider.old`）留用户决定。
- [ ] **P2 安全（凭据轮换，待决策）**：`devops_online_env.go` 硬编码 OSS AK/SK 与 ES 口令；`pan_download`/`bnd_download` 测试文件硬编码真实 RefreshToken/BDUSS（建议迁 `.hide.json`）；ali_log ak/sk 曾明文进会话记录，建议评估轮换。
- [ ] **P1 待用户决策**：`osec-resdb` STORAGE worker 的 `es_endpoint` 指向已下线旧 ES 集群（已回滚，不影响 P3 数据正确性）。
- [ ] **既有故障**：现网 ES 无 `resource_valid` 索引（404），`checkValid`/`queryValidAndPwd` v2/v3 同样失效。
- [ ] **P2**：COMMON `common_message.proto` 的 `go_package` 仍是旧仓库名 `PPIO`，`gen.sh` 后要手工 sed；应改 proto 全自动。
- [ ] **P2**：资源生命周期 P0 基线剩余项（PRD §15.3 第 12/13 项）：bnd checker 探测吞吐与代理池配额、无 join 百度文档 `_source` 大小抽样未采。
- [ ] **P2 待人工验证（管理台合并）**：ARMS 确认 `queue_admin_*` 指标入库；浏览器实测 spiderAdmin 三组菜单/Mock/各页。

## P3 低优先级待办

- [ ] **P3** `illuminate/queue-task/queue_test.go` 的 `TestGetTimeoutKeys`/`TestRePush` 既有失败（时间戳断言误差 ~10s）。
- [ ] **P3** `services/aliyun-drive` 的 `checkRecentUpdate` 用分享 id 而非 `md5(shareLink)` 查 STORAGE，疑似历史 bug，待确认。
- [ ] **P3 清理** 蜻蜓代理的**现行**凭据在 `services/proxy-provider/change_proxy_config.go`，
      该文件是 gitignore 的（未提交，处理得当）。但仓库里仍留着**过期**凭据：
      `proxy-provider.go` 硬编码的 `qtWhitelistLink` 与两份 `config*.yaml` 的
      `providers[].conf`。这些死值会误导排查（我就据此误判过"凭据全过期"），
      建议清掉或改成从环境变量读。
- [ ] **P3** `bnd_resolver_check.go:160` 的 `go vet` 告警（`storage.Resource` 按值传递，含 `sync.Mutex`）。
      根因是 `resource.SaveBaiduResource` 的全局签名，要改得整体改。
- [ ] **P3** `devops_res_reindex` 若要在非本地环境跑，需先约定导出目录挂载点（当前直接 panic 退出）。

## 2026-09-16 从 tasks.md 移入的 P1/P2 长尾

- [ ] **P1** `keyword_funletu` 每个任务因 TLS 证书不匹配失败（`v.funletu.com` 证书签给 `bq.funletu.com`）：改域名/SNI 或按下线口径处理。
- [ ] **P1** 按新口径（单 IP ≥10 条/分钟）复议 4 站：`www.pioz.cn`（14.6 万条、100% 夸克、免登录，仅 10 并发触发 Turnstile）、`1.star2.cn`、`tv.yydsys.top`、`xsayang.fun`（`site-discovery/history.md`「待复议」）。
- [ ] **P1** kkpans 上线验收 #5：ES 能按 `client=www.kkpans.com` 检索到资源（`./deploy.sh kkpans` → `ps`/`log kkpans`）。
- [ ] **P1** STORAGE 上线前运行时回归：`go mod tidy` 升级了 aws-sdk-go/logrus/mysql/easyjson 且 go 1.22→1.23，重点看 S3 上传（save-torrent）与日志格式。
- [ ] **P2** 网关 `initEs()` 连不上 ES 直接 panic → 改重试+告警（待用户决定）。
- [ ] **P2** res_scheduler 补 ListTask/队列长度观测 RPC；`devops_check_and_push_clear_queue`（4 台）仍直连 redis `Queue2`，可迁网关。
- [ ] **P2** misoso：一轮全量真实耗时（影响 `SeenTTL`）、626 万去重键 redis 容量。dyyjmax 全量对账未实跑（≈1 h）、feikuai `ali-share` 分支无样本、kuakes ajax `code≠0` 语义、fuxipan `Crawl-delay:10` 归属歧义。
- [ ] **P2** 夸克业务码 `41031` 补进 `osec-resource-api/services/valid/quark-api.go` 与 `osec-spider-go/services/gateway/valid/quark_checker.go` 的 `quarkInvalidCodes`（现靠文案兜底）。
- [ ] **P2** 百度/迅雷 checker 仍是纯文案匹配，按 `lessons/success-网盘失效判定原则.md` 改造。
- [ ] **P2** COMMON `Makefile` protoc 目标过期（新增 5 个 proto 未纳入）。
- [ ] **P2 代理池口径**：`keyword_upyunso/funletu/pansearch_me` 近 24 h ok=0，列为下线候选，看一次代理池再定。
