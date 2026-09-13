---
title: 当前任务与进度
type: task
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-13T17:50:00+08:00
priority: critical
keywords: [任务, 进度, 待办, P5, 队列v2, queue-admin, 全站扫描, fullsweep, 文档爬虫, doc-crawler, FC Chrome, 凭据轮换, 站点发现, kkpans, misoso, 有效性检测]
summary: 仍在推进/阻塞/待决策的事项（P0 误删事故重爬中；P5 顺序 阶段C→A'→阶段D）；已上线任务在 archive
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
| 配置 v2/OAuth/配置拆代码 | ✅ 已上线 | `LOCAL_CONFIG_PATH` 回落待修；凭据轮换待决策 | `current/tasks-backlog.md` |
| 资源生命周期改造 P0~P3 | ✅ 已上线 | es_endpoint / `resource_valid` 索引缺失等 | `current/tasks-backlog.md` |
| 管理台合并 | ✅ 已上线 | ARMS 指标、浏览器实测待人工 | `current/tasks-backlog.md` |
| 队列 v2 上线收尾 | 人工进行中 | A~E 待用户执行 | 本文件「待办」 |
| 5 爬虫全站扫描启动行为改造 | 待办（P0） | 改为 `fullsweep:lastdone` 守卫 | 本文件「待办」 |
| 安全凭据轮换 | 待用户决策 | 多处硬编码 AK/SK/Token | `current/tasks-backlog.md` |

> 09-08 并行四任务（文档爬虫 FC 自动化 6 项人工事项）与 P3 低优先级待办已移至 `current/tasks-backlog.md`。

> 「归档遗留待办」（P4 收尾/配置 v2 回落/凭据轮换/resdb ES 端点/resource_valid 缺失/proto go_package/管理台人工验证）已移至 `current/tasks-backlog.md`。

## 待办

- [ ] **P2 cdp3 profile= 调用方接入**（2026-09-13 上线后遗留）：NC-JS `task.ts`/SPIDER `doc_crawler` 若要用 `profile=`，结束时必须先发 CDP `Browser.close` 等响应再断开（rod/puppeteer 的 `browser.Close()` 即可），否则最多丢 20 s；被占直接 409 需客户端退避重试（≥3 s） → `decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md`。NAS `profiles/osec/` 下的 `e2e`（旧目录格式）、`freeze1.tar.new-*`（冻结残留）、`h1.tar` 是测试产物，可删。
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
  - ✅ ①② 09-12 23:05~23:11 用户授权执行：止血 → 部署 `b888846` → 发现 bnd「违规」tooltip 误判 930 条再停 → 修复 `06ef50d` 重新部署（rollout §15.5）。`e16bd98`（errno 145 判失效）23:34 已部署；观察数据见 rollout §15.5。
  - ③ **恢复 = 重爬**（用户确认 Mongo 无数据）：导出脚本 `scripts/lc_false_invalid_export.sh` → 投递工具 `tools/lc-recrawl`（SPIDER `240a71a`，dry-run 过：1,152,617 条、6,129 个脏 pwd 归一化为空）限速推 `resourcePreCheck`；运行方式：本机 `LOCAL_CONFIG_PATH=<scratchpad>/spider.recrawl.yaml`（`spider_gateway` 指向隧道 127.0.0.1:18082）`go run ./tools/lc-recrawl -file _note/lc-recrawl/all.tsv -rate 10 -state _note/lc-recrawl/state`；导出完成 `_note/lc-recrawl/all.tsv` **1,152,617** 行（quark 1,111,741 / ali 39,946 / bnd 930；比事件数少 3.6k 为同 share_id 去重与已复活行）；[用户确认 09-12 23:33] 节奏按建议：23:34 试点前 1,000 条（`-rate 10`，`_note/lc-recrawl/pilot.log`），1 分钟内 ES 已见 `client=lc-recrawl-2609` 文档；试点结果（00:00）：投递 1000/1000 零失败、队列清空、**498 条回库复活（status=1）**，其余 502 条为解析器判真失效（近 45 min 夸克解析失败码：41031 封禁 645 / 41004 不存在 513 / 41012 取消 288 / 41011 过期 134）→ 预期恢复率 ≈50%。**00:05:58 全量开始**（`_note/lc-recrawl/full.log`，≈31 h），持久 Monitor 每 30 min 上报。00:30~00:47 隧道掉线 302 行记失败（`failed-round1.tsv` 已补投）；工具加断连熔断 `77e92bb`，00:43 续投；隧道改由守护脚本（scratchpad `tunnel-18082.sh`）自动重连。09-13 07:40 进度 263,231/1,152,617（≈23%，≈35k/h，预计还需 ≈25 h），`state.failed` 305 条待补投。`e16bd98` 已于 23:34 部署 checker。
  - ✅ **[用户要求 09-13 13:50] 解析器判失效部分抽 1,000 条走云端 Chrome（CDP）实测**：样本 `_note/lc-recrawl/cdp-sample-1000.tsv`（41031 655 / 41012 157 / 41004 101 / 41011 47 / 41019 20 / 41010 20），工具 `tools/quark-cdp-verify`（SPIDER `badf831`，并发 20）14:07 跑完：**1,000/1,000 一致、0 不一致**（3 条超时重测后同样 41031），CDP 业务码与解析器逐条相同 → 解析器判失效可信。报告 `_note/lc-recrawl/cdp-verify/report.md`、rollout §15.6。
  - 修复版 checker 可信度核验：23:21~23:32 判失效的 4,713 条 quark 中抽 4 条交解析链路（`client=lc-verify-2609`），解析器同样返回 41031 → 判定正确；近 1 h `valid1h=23,308 / invalid1h=5,942`（ratio 0.20，基线 0.98 会在 7 天内自然回落）。
  - ✅ ⑤ API `bnd-api.go` 已对齐 SPIDER `classifyBndShare`（API `0ad7bb3`，未部署；v3 复用同一 bndApi）。待办：API 与网关下次发版带上（网关 `06ef50d`/`e16bd98` url_check 共用 valid 包 + `b888846` 告警护栏）。
  - ④ 修复上线后消化 bnd `dueBacklog` 52.8 万（8 天零有效检测）。
- [ ] **P0 生命周期 P5 准入**（阶段 A/B 已上线 09-12 16:34；**顺序因事故调整**）——决策 `decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md`、`decision-2026-09-12-阶段D改由API侧自动灰度分流.md`。
  - 下一步按序：① ✅ 事故止血 + 修复上线；② **阶段 C 复测改到重爬结束后（预计 09-14 上午）**——重爬期间 ES 持续写入、解析器满负荷，延迟对拍会失真；③ ✅ A' 只读探测 09-13 16:12 完成：64 桶 4,342 万行、缺失 **84,871（0.20%）**（quark 66,358 / bnd 9,698 / ali 8,458 / xunlei 357，远低于 170 万估计），16:50~17:35 `lc-check -trigger-check` **425/425 批成功**，`manual_check` 事件 84,791（quark 66,358 / bnd 9,618 / ali 8,458 / xunlei 357；80 条 bnd 已非 status=1 跳过）→ 由 checker 按队列复检，G3 存量部分收口；④ 阶段 D：`search_canary` 已开发（API `6bbbfb8`），阶段 C 通过后启用。
- [ ] **P2 代理池口径**（09-10 待确认项，Agent 自主判断）：`lifecycle_checker_*` ok=0 已归因为事故（非口径问题）；`keyword_upyunso/funletu/pansearch_me` 近 24 h 仍 ok=0（几乎全 ipUnusable/other），按 `decision-2026-09-03-清理下线爬虫代码.md` 口径列为下线候选，待修复版 checker 上线后再看一次代理池再定。
