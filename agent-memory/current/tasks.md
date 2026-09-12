---
title: 当前任务与进度
type: task
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T14:20:00+08:00
priority: critical
keywords: [任务, 进度, 待办, 队列v2, queue-admin, 全站扫描, fullsweep, 文档爬虫, doc-crawler, FC Chrome, 凭据轮换, 站点发现, kkpans, misoso, 有效性检测]
summary: 当前仍在推进/阻塞/待人工决策的事项；已完成并上线（或被取代不再跟进）的任务已归档到 archive/2026/tasks-2026-09-已完成.md
questions:
  - 当前该做什么，有哪些待办
load: on-demand
related:
  - agent-memory/current/risks.md
  - agent-memory/archive/2026/tasks-2026-09-已完成.md
  - agent-memory/procedures/workflow-本地构建与验证.md
---

# 当前任务与进度

> 已完成且已上线（或被后续方案取代）的任务块已原文移入 `archive/2026/tasks-2026-09-已完成.md`（P4 全量 bootstrap、配置 v2 上线、GitHub OAuth、配置按进程拆代码、管理台合并、资源生命周期改造 P0~P3 等）。本文件只留仍在推进/阻塞/待决策的事项。

## 一眼总表

| 任务 | 状态 | 阻塞/下一步 | 详情文件 |
|---|---|---|---|
| 生命周期 P4 全量 bootstrap | ✅ 已完成 | 5 提交待下次网关重启部署；2 个 `:cur` 半区窗口待决定 | 归档遗留待办 / archive「生命周期 P4」 |
| 09-08 并行四任务 | 部分已上线 | 文档爬虫 FC 自动化卡 6 项人工事项 | 本文件「2026-09-08 并行四任务」 |
| 配置 v2/OAuth/配置拆代码 | ✅ 已上线 | `LOCAL_CONFIG_PATH` 回落待修；凭据轮换待决策 | 归档遗留待办 |
| 资源生命周期改造 P0~P3 | ✅ 已上线 | es_endpoint / `resource_valid` 索引缺失等 | 归档遗留待办 |
| 管理台合并 | ✅ 已上线并核验 | ARMS 指标、浏览器实测待人工验证 | 归档遗留待办 |
| 队列 v2 上线收尾 | 进行中（人工） | A~E 步骤待用户执行 | 本文件「待办」 |
| 5 爬虫全站扫描启动行为改造 | 待办（P0） | 改为 `fullsweep:lastdone` 守卫 | 本文件「待办」 |
| 安全凭据轮换 | 待用户决策 | 多处硬编码 AK/SK/Token | 归档遗留待办 |
| 进行中 | 无 | — | — |

## 2026-09-08 并行四任务（监控增强 + 文档爬虫上云）—— 部分已上线，文档爬虫 FC 自动化待人工

四件事：①告警加入后台+附日志、队列失败率告警按队列可配（默认 10min/50%→1h/60%）；②代理池情况加入 admin 后台；③资源链接爬取路径追踪（SLS 拼时间线）；④文档爬虫 FC 自动化（新 Chrome FC 实例 + doc-crawler 进程 + 移植金山文档油猴脚本）。

- 五仓库均已 push：SPIDER `d6a4d54` / COMMON `5e5cdc1` / NC-JS `ab7753d` / API `9518bac` / userscripts `fdc884a`。
- **①②③已随 2026-09-09 网关重启（`883daeb`）一并上线**：告警后台、代理池监控 `proxy_admin`、链接追踪均生效；`spiderAdmin` 新页面已发布；爬虫容器与 `proxy` 服务均已重部，埋点数据正常。
- **④文档爬虫 FC 自动化仍未落地**，卡在以下人工事项：
  - [ ] SLS 给 `link_key` 建索引后打开 `services.queue_admin.sls.link_key_indexed`（缺省 false）
  - [ ] Tampermonkey 扩展包上传 OSS（`fc-chrome/extensions/tampermonkey.zip`），拿到实物后复核 `fc-chrome/tampermonkey.go` DOM 选择器（未验证）
  - [ ] FC 镜像构建与部署（阿里云 ACR + serverless-devs，函数名 `nc-app-prod-cdp3`），步骤见 COMMON `fc-chrome/README.md`
  - [ ] 新 FC 域名回填三处：NC-JS `CDP_ENDPOINT`、`task.ts` 的 `eps['prod-v3']`（TODO 占位）、SPIDER `services.doc_crawler.fc_endpoint`
  - [ ] 云端油猴脚本上传：userscripts `pnpm build:cloud && pnpm upload:cloud`
  - [ ] doc-crawler 部署主机待确认（`deploy.sh` 暂填 `osec-jenkins` 占位）
  - [ ] PC 端油猴调度器是否下线，由用户决定（可与 doc-crawler 并存）
- 已知取舍：代理池总览全场景去重 IP/主机数恒为空；`proxyAdminRpc` 无前端 mock；`AlertRulesResponse.global.backlogThreshold` 未暴露 `resourcePreCheck` 专用缺省；无生产凭据多项未联网验证。
- 详情：`sessions/2026/2026-09-08-并行四任务监控与文档爬虫上云.md`；`agent-tasks/2026-09-08-monitoring-and-doc-fc/`；`lessons/failure-旁路能力初始化拖垮主流程.md`。

## 归档遗留待办（原分散在已归档任务块中，仍未完结）

- [ ] **P1 生命周期 P4 收尾**：5 个未部署代码提交（`3b8cc13`/`aac5f84`/`61cf1db`/`e856540`/`93f4d38`）待下次网关重启生效；2 个 `:cur` 半区窗口（父在 long、子在 cur，21,451 子）是否处理待用户决定；P6 关双写前须补 v3 detail/fileCtx（结构兼容，见 `knowledge/api-v3-detail-filectx兼容性分析.md`）。**P5 前置未做**：bootstrap 后的 v2/v3 50 关键词重合度（≥95%）与 P99 延迟对比尚未跑。详见 `sessions/2026/2026-09-11-p4-bootstrap接管巡检与校验失败取证.md`。
- [ ] **P2 排期**：巡检守护提升到 `runBootstrapJob` 级 + heap 阈值可配（0.5~1 人日）；rollout §9 待补写。
- [ ] **P2 代码待修（配置 v2）**：`LOCAL_CONFIG_PATH` 缺省未回落宿主机 `config.yaml`；删宿主机 `config.yaml` 的时机（回滚现依赖 `spider.old`）留用户决定。
- [ ] **P2 安全（凭据轮换，待决策）**：`devops_online_env.go` 硬编码 OSS AK/SK 与 ES 口令；`pan_download`/`bnd_download` 测试文件硬编码真实 RefreshToken/BDUSS（建议迁 `.hide.json`）；ali_log ak/sk 曾明文进会话记录，建议评估轮换。
- [ ] **P1 待用户决策**：`osec-resdb` STORAGE worker 的 `es_endpoint` 指向已下线旧 ES 集群（已回滚，不影响 P3 数据正确性）。
- [ ] **既有故障**：现网 ES 无 `resource_valid` 索引（404），`checkValid`/`queryValidAndPwd` v2/v3 同样失效。
- [ ] **P2**：COMMON `common_message.proto` 的 `go_package` 仍是旧仓库名 `PPIO`，`gen.sh` 后要手工 sed；应改 proto 全自动。
- [ ] **P2**：资源生命周期 P0 基线剩余项（PRD §15.3 第 12/13 项）：bnd checker 探测吞吐与代理池配额、无 join 百度文档 `_source` 大小抽样未采。
- [ ] **P2 待人工验证（管理台合并）**：ARMS 确认 `queue_admin_*` 指标入库；浏览器实测 spiderAdmin 三组菜单/Mock 开关/各页数据。

## 待办

- [ ] **P0 队列 v2 上线收尾（用户人工执行）**：网关/全部消费者已于 2026-09-04 12:30 前上线在跑，
      剩余 A 删 jenkins `spider-xunlei_share`、B 杀两个 2023 年裸进程、C `./deploy.sh ps` 复核、
      D osec-res2 跑 `devops_migrate_legacy_queues`（先 dry-run 再 `--apply --dry-run=false`）、E 看网关 precheck 日志。
      脚本 `osec-spider-go/scripts/queue_v2_cutover_finish.sh`，文档同名 `.md`。**无回滚路径**（旧命令已删、旧 ES 已下线）。
- [ ] **P1** 删除已合并的 6 个 worktree/分支 `spider-wt-queue-v2-*`（`git merge-base --is-ancestor` 确认后 `git worktree remove` + `git branch -d`）。
- [ ] **P1** `keyword_funletu` 上线后每个任务都因 TLS 证书不匹配失败：`v.funletu.com` 返回的证书签给 `bq.funletu.com`。
      站点侧问题（2026-09-04 上线时发现，与队列 v2 无关）。要么改请求域名/加 SNI，要么确认站点已换域名；
      长期失败考虑按 `decision-2026-09-03-清理下线爬虫代码.md` 的口径下线。
- [ ] **P1 待确认** API 仓库 `osec-resource-api/config.yaml` 的 ES 主机 `es-cn-oew1qf4gx000pr1ap` 与 STORAGE/网关现用的
      `es-cn-vcg4txxrn00021s9s` 不一致，可能同样是过期集群（见 `lessons/failure-网关重启暴露ES集群已更换.md`）。
- [ ] **P2** 网关 `initEs()` 连不上 ES 直接 panic，导致单个依赖故障拉不起网关；考虑改为重试+告警（待用户决定）。
- [ ] **P2** res_scheduler 补 ListTask/队列长度观测 RPC（队列 v2 的可观测性缺口）。
- [ ] **P2** `devops_check_and_push_clear_queue`（线上 4 台）仍用 `queue_task.Queue2` 直连 redis，可迁网关。
- [ ] **P3** `illuminate/queue-task/queue_test.go` 的 `TestGetTimeoutKeys`/`TestRePush` 既有失败（时间戳断言误差 ~10s）。
- [ ] **P3** `services/aliyun-drive` 的 `checkRecentUpdate` 用分享 id 而非 `md5(shareLink)` 查 STORAGE，疑似历史 bug，待确认。

- [ ] **P3 清理** 蜻蜓代理的**现行**凭据在 `services/proxy-provider/change_proxy_config.go`，
      该文件是 gitignore 的（未提交，处理得当）。但仓库里仍留着**过期**凭据：
      `proxy-provider.go` 硬编码的 `qtWhitelistLink` 与两份 `config*.yaml` 的
      `providers[].conf`。这些死值会误导排查（我就据此误判过"凭据全过期"），
      建议清掉或改成从环境变量读。
- [ ] **P1** 按新口径（单 IP ≥10 条分享链接/分钟）复议 4 个站点：
      `www.pioz.cn`（最有希望：14.6 万条、100% 夸克、免登录，原因只是 10 并发触发 Turnstile）、
      `1.star2.cn`、`tv.yydsys.top`、`xsayang.fun`。见 `site-discovery/history.md` 标注的「待复议」。

- [ ] **P0** 按 `decisions/decision-2026-09-03-全站扫描不在启动时触发.md` 改造 5 个爬虫的
      启动行为：`bbs_kkpans` / `bbs_dyyjmax` / `bbs_fuxipan` / `bbs_misoso` / `bbs_kuakes`
      现在都是**启动即全站扫描**。改为全量整轮成功后写 redis `<site>:fullsweep:lastdone`，
      启动时读该键，未超 `FullSweepInterval` 就跳过全量只跑增量。
      `bbs_feikuai` 的游标分批全量天然合规，可作参照。
      ⚠️ 这 5 个已经上线在跑，每次重启/重新部署都会重扫全站，优先级高。
- [ ] **P1 待用户手动执行** 清理遗留 ②：用户已确认 `osec-resdb` 上两个废弃容器**不需要了**，
      但删除命令需要 `sudo`（`pplabs` 直连 docker.sock 是 permission denied），
      被 Claude Code 自动模式安全策略拦截，需要人工在终端跑：

      ```bash
      ssh pplabs@osec-resdb "sudo docker rm -f \
        spider-share_download_push_resolve_alipan_241226 \
        spider-share_download_push_resolve_qb-250225"
      ```

      ⚠️ 只删这两个，**不要动** `spider-share_download_push_resolve_ali_250918`
      （对应 `deploy.sh` 的 `dl_push`，仍在服役）。
- [ ] **P2** misoso 上线前待确认（PRD §9）：一轮全量遍历真实耗时未知（影响 `SeenTTL`）、
      626 万条去重键的 redis 容量评估。
- [ ] **P2** 各站遗留的待确认项：dyyjmax 全量精确对账未实跑（命令已就绪，约 1 小时）、
      feikuai 的 `ali-share` 分支无样本未端到端验证、kuakes 的 ajax `code≠0` 业务语义无样本、
      fuxipan 的 `Crawl-delay:10` 归属有歧义（当前按实测 4 req/s 执行）。
- [ ] **P2** 把夸克业务码 `41031`（分享者被封）补进两处生产 checker 的 `quarkInvalidCodes`：
      `osec-resource-api/services/valid/quark-api.go`、`osec-spider-go/services/gateway/valid/quark_checker.go`。
      现在只靠 message 兜底正则命中，依赖文案不变，很脆弱。
- [ ] **P1** 夸克/阿里有效性检测修复**上线后**观察 `/v2/validShareLink` 的 `-1` 比例是否下降；
      同时确认 `clear_expire` 没有出现异常的批量删除。
- [ ] **P2** 百度（`bnd`）、迅雷（`xunleipan`）的 checker 仍是纯中文文案匹配，
      有和夸克同样的漏判风险，下次动到时按 `lessons/success-网盘失效判定原则.md` 改造。
- [ ] **P1** kkpans 爬虫上线后核对验收项 #5：ES 中能按 `client=www.kkpans.com` 检索到资源。
      部署命令 `./deploy.sh kkpans`，然后 `./deploy.sh ps` / `./deploy.sh log kkpans`。
- [ ] **P1** STORAGE 上线前做运行时回归：`go mod tidy` 顺带升级了 aws-sdk-go(1.25→1.40)、
      logrus(1.6→1.8.1)、go-sql-driver/mysql(1.5→1.7)、easyjson，且 `go` 指令从 1.22.0 提到 1.23。
      编译通过不等于行为不变，重点看 S3 上传（save-torrent）与日志输出格式。
- [ ] **P2** COMMON `Makefile` 的 protoc 目标已过期（路径与实际 proto 文件名不符，新增的 5 个 proto 未纳入）。
- [ ] **P3** `bnd_resolver_check.go:160` 的 `go vet` 告警（`storage.Resource` 按值传递，含 `sync.Mutex`）。
      根因是 `resource.SaveBaiduResource` 的全局签名，要改得整体改。
- [ ] **P3** `devops_res_reindex` 若要在非本地环境跑，需先约定导出目录挂载点（当前直接 panic 退出）。

## 进行中

- 无
