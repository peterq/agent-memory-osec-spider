---
title: 当前任务与进度
type: task
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-12T23:25:00+08:00
priority: critical
keywords: [任务, 进度, 待办, P5, 队列v2, queue-admin, 全站扫描, fullsweep, 文档爬虫, doc-crawler, FC Chrome, 凭据轮换, 站点发现, kkpans, misoso, 有效性检测]
summary: 仍在推进/阻塞/待决策的事项（P0：checker 误删事故修复已上线、恢复待决策；P5 顺序 阶段C→A'→阶段D）；已上线任务在 archive
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
| **🔴 lifecycle_checker 误删事故** | 止血待人工 | ① 人工 `docker stop` ② 部署 `b888846` ③ 恢复方案待用户决策 | 本文件「进行中」/ `lessons/failure-lifecycle_checker误传资源md5…` |
| 生命周期 P4 全量 bootstrap | ✅ 已完成 | 2 个 `:cur` 半区窗口 09-12 取证**无需处理**（父子都在 cur） | archive「生命周期 P4」 |
| **生命周期 P5 准入** | 阶段 A/B 已上线；被事故阻塞 | 修复版 checker 上线 → 阶段 C 复测 → A' 投递 → 阶段 D 灰度（API 侧分流，开发中） | 本文件「进行中」 |
| 09-08 并行四任务 | 部分已上线 | 文档爬虫 FC 自动化卡 6 项人工事项 | `current/tasks-backlog.md` |
| 配置 v2/OAuth/配置拆代码 | ✅ 已上线 | `LOCAL_CONFIG_PATH` 回落待修；凭据轮换待决策 | 归档遗留待办 |
| 资源生命周期改造 P0~P3 | ✅ 已上线 | es_endpoint / `resource_valid` 索引缺失等 | 归档遗留待办 |
| 管理台合并 | ✅ 已上线 | ARMS 指标、浏览器实测待人工 | 归档遗留待办 |
| 队列 v2 上线收尾 | 人工进行中 | A~E 待用户执行 | 本文件「待办」 |
| 5 爬虫全站扫描启动行为改造 | 待办（P0） | 改为 `fullsweep:lastdone` 守卫 | 本文件「待办」 |
| 安全凭据轮换 | 待用户决策 | 多处硬编码 AK/SK/Token | 归档遗留待办 |

> 09-08 并行四任务（文档爬虫 FC 自动化 6 项人工事项）与 P3 低优先级待办已移至 `current/tasks-backlog.md`。

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

## 进行中

- [ ] **🔴 P0 lifecycle_checker 误删事故（09-12 22:17 发现）**——正本 SPIDER rollout §15；经验 `lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md`。
  - ✅ ①② 09-12 23:05~23:11 用户授权执行：止血 → 部署 `b888846` → 发现 bnd「违规」tooltip 误判 930 条再停 → 修复 `06ef50d` 重新部署（rollout §15.5）。23:11~23:15 观察：bnd valid 2,086 / invalid 0 / error 468（error 主要是代理 need verify 9019）；quark/ali/xunlei 队列暂无任务（bnd 积压 20 万先消化，≈31k/h）。**`e16bd98`（errno 145/「链接不存在」判失效）已 push 待部署**，未部署前真失效 bnd 只会报错不会被清。
  - ③ **恢复待决策**：Mongo `share_files` 回灌工具（≈1 人日）→ 删 `invalid_link_*` 对应行 → `UpsertResource` → 修复版 `TriggerCheck(force)` 复检；范围 **1,156,201**（quark 1,115,264 / ali 40,007 / bnd 930，res_id 从 `res_lc_event` 取）。
  - ⑤ **P1** API `services/valid/bnd-api.go` 按 SPIDER `classifyBndShare` 对齐（仍拿「不存在」匹配整页）；网关下次发版带上 `06ef50d`（url_check 共用 valid 包）+ `b888846` 告警护栏。
  - ④ 修复上线后消化 bnd `dueBacklog` 52.8 万（8 天零有效检测）。
- [ ] **P0 生命周期 P5 准入**（阶段 A/B 已上线 09-12 16:34；**顺序因事故调整**）——决策 `decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md`、`decision-2026-09-12-阶段D改由API侧自动灰度分流.md`。
  - 下一步按序：① 事故止血 + 修复上线；② 09-13 ≥16:34 跑 rollout §14.3 观察项 + 阶段 C 复测 p5-plan §4；③ A' 投递：只读探测 `scripts/lc_legacy_probe_all.sh _note/p5-aprime`——xunlei 已完成（235,205 行、缺失 357=0.15%，`_note/p5-aprime/xunlei_*.ids`）；ali/quark/bnd 09-12 23:20 起本机后台跑（`driver.log`，断点续跑，预计数小时）→ 完成后 `lc-check -trigger-check` 每天 ≤20 万（checker 修复已上线，可投递）；④ 阶段 D：`search_canary` **已开发完成** API `6bbbfb8`（缺省关闭），门槛全过后 `enabled: true` + `notify_url` 重部 API；上线前决定 `step_every_v3_requests`（缺省 100 会在几十分钟内涨满）。
  - 已核：`url_check` 近乎空转，旧索引删除来自 API v2 `validShareLink`（G3 修复点 API 侧 `ReportInvalid`，已上线）**以及本次事故的 lcClear→clearExpire**。
- [ ] **P2 代理池口径**（09-10 待确认项，Agent 自主判断）：`lifecycle_checker_*` ok=0 已归因为事故（非口径问题）；`keyword_upyunso/funletu/pansearch_me` 近 24 h 仍 ok=0（几乎全 ipUnusable/other），按 `decision-2026-09-03-清理下线爬虫代码.md` 口径列为下线候选，待修复版 checker 上线后再看一次代理池再定。
