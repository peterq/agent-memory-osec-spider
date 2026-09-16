---
title: 当前任务与进度
type: task
status: active
created_at: 2026-09-02T10:50:00+08:00
updated_at: 2026-09-16T11:45:00+08:00
priority: critical
keywords: [任务, 进度, 待办, 五站爬虫, 站点发现, 腾讯文档, 十项提案, P5灰度, lifecycle_checker, xlLoadShare, 队列v2]
summary: 仍在推进/阻塞/待决策：五站爬虫待确认合并、站点发现收尾、文档发现待批量执行、腾讯文档与十项提案待确认合并、P5 灰度爬坡、误删事故收尾；长尾在 tasks-backlog
questions:
  - 当前该做什么，有哪些待办
load: on-demand
related:
  - agent-memory/current/risks.md
  - agent-memory/current/tasks-backlog.md
  - agent-memory/archive/2026/tasks-2026-09-16-压缩前快照.md
  - agent-memory/archive/2026/tasks-2026-09-已完成.md
---

## 一眼总表

| 任务 | 状态 | 阻塞/下一步 | 详情 |
|---|---|---|---|
| **五站爬虫**（duanjuso/xiaozi/qileso/jsnoteclub/ddys） | ✅ 09-16 12:13 [用户裁定「合并上线」] 已合入 SPIDER master（`70bb955`）并 push，5 容器上线：duanjuso/jsnoteclub@jenkins、xiaozi/qileso@res2、ddys@res1 | 首日观察：类型分布、duanjuso 抓取速率偏慢（代理链路 1 req/s 级）、qileso 增量 10 min 首跑；存量 6 站测试是否也改走代理池待定 | `knowledge/domain-站点-260916接入批次.md`、`sessions/2026/2026-09-16-五站爬虫并行开发.md` |
| **站点发现第二轮** | ✅ 09-16 完成并已合入 COMMON master（`cd85518`） | lzpanx robots `Crawl-delay:20` 是否遵守；1~2 周后复核 xiaojiwo.top | `sessions/2026/2026-09-16-站点发现第二轮.md`，正本 COMMON `site-discovery/history.md` + `260916/` |
| **云端文档脚本迁入 NC-JS** | 🟢 09-16 11:45 用户确认后已合入 nc-js main、SPIDER master 并 push，worktree/分支已删 | **待人工**：NC-JS `apps/doc-cloud-spider` `pnpm build && pnpm upload`（个人仓库副本不删、PC 油猴插件暂不动，[用户裁定]） | `decisions/decision-2026-09-16-云端文档脚本迁入NC-JS.md` |
| **腾讯文档(docs.qq.com)表格解析** | 🟢 09-16 10:45 用户确认后已合入 userscripts master@7af9776、nc-js main@997836b（已 push） | **待人工**：云端脚本构建上传（迁移合并后在 NC-JS `apps/doc-cloud-spider` 做 `pnpm build && pnpm upload`）、spiderAdmin `pnpm build` 发版（自动模式拦截生产部署/推送） | `agent-tasks/2026-09-16-qqdoc-sheet/`，知识 `knowledge/domain-腾讯文档表格解析.md` |
| **文档发现任务（在线文档网盘链接）** | 🟢 09-16 首轮完成：渠道链路+工具打通，达标 29 篇 | 待执行批量抓取（HTTP 122 / 浏览器 591 / 重试 88，命令在 COMMON `site-discovery/doc-discovery/260916/报告.md` §4）；达标文档待提交文档爬虫 | `procedures/workflow-文档发现.md`、`sessions/2026/2026-09-16-文档发现任务.md` |
| **十项提案并行开发** | 🟢 09-16 12:00 [用户裁定「合并上线」] 四仓库 + NC-JS 已合入主分支并 push，四仓 `scripts/ci.sh` 全过 | **代码已合、服务未重部**：网关/API/STORAGE/NC-JS 重部前先做 `95-merge-plan.md`「上线前置项」（GitHub secrets、FC 函数 OSS 变量、网关容器 OSS 变量、熔断器 dry_run） | `agent-tasks/2026-09-16-ten-proposals/95-merge-plan.md` |
| **P5 阶段 D 灰度** | 🟡 API `search_canary` 爬坡中 | 09-16 06:3x 改每 500 个 v3 请求 +2%，≈9 h 到 100%，全量后再观察 3 天即 P5 完成 | rollout §16/§17；`decisions/decision-2026-09-12-P5切v3准入门槛与失效同步.md` |
| **🔴 lifecycle_checker 误删事故** | 修复已上线，重爬终态回库 ≈56% | 剩余 quark 真失效不可恢复；bnd 积压告警阈值放宽待用户定 | rollout §15；`lessons/failure-lifecycle_checker误传资源md5导致116万有效资源误删.md` |
| xlLoadShare 修复 | ✅ 09-15 三机上线 | 失效上报 dry run → 抽样复核 → 用户拍板开启 | `knowledge/domain-迅雷分享爬取.md` §5/§6 |
| P6 分享链接/搜索总览 + p90 关匿名 | ✅ 09-16 上线 | 观察防护巡检一周；ES 父文档过滤线上对拍 | `knowledge/architecture-search-admin.md` |
| 队列 v2 上线收尾 | 人工进行中 | A~E 待用户执行（`scripts/queue_v2_cutover_finish.sh`），**无回滚路径** | 快照 archive「待办」 |
| 5 爬虫全站扫描启动行为改造 + 6 站骨架迁移 | ✅ 已完成 | 决策早于十项提案已落地；骨架迁移 6/6 站全部完成 | `knowledge/architecture-spider-sitecrawler骨架.md` |
| 其余长尾待办 | 见 backlog | 凭据轮换/站点复议/checker 业务码/STORAGE 回归等 | `current/tasks-backlog.md` |

## 进行中

- [ ] **五站爬虫上线观察（09-16 12:07~12:13 部署）**：SPIDER master `70bb955`（五站）+ `7e4206c`（deploy.sh 映射），用新版 deploy.sh（releases/current 布局，jenkins/res2/res1 三机首次迁移）逐站部署，健康检查全过，均已开始提交链接。线上无 5 站配置节，全部按内置缺省值跑（`Enabled` nil 视为开）。观察项：duanjuso 5 分钟仅 12 条（代理链路 + `MinRequestInterval` 1 s），存量 150 万按此要数月，视情况提并发；qileso 全量区间初始为空、靠增量 10 min 后从 StartId 上探；bnd/ali/xunlei 类型分布。worktree/分支已清理。
- [x] **站点发现第二轮**：COMMON worktree 已合入 master `cd85518` 并 push，worktree/分支已删。待裁定 lzpanx.com robots；1~2 周后复核 xiaojiwo.top。
- [x] **飞书文档解析接入（2026-09-16 已合并）**：[用户裁定 09-16 合并] userscripts master `bf4c36d`、NC-JS main `39c145a`、SPIDER master `bc4b25f` 均已 fast-forward 合入（未 push），worktree 已删。**待人工**：userscripts `pnpm build:cloud && pnpm upload:cloud`（OSS doc-cloud.user.js + 旧名 kdoc.user.js）、spiderAdmin 发布、三仓库 push；PC 端油猴调度器仍不过滤飞书任务。→ `knowledge/domain-飞书文档解析.md`

- [ ] **P1 腾讯文档表格解析（09-16，已合并并 push，待人工上传/发版）**：方案 = 同一份云端脚本（现 NC-JS `apps/doc-cloud-spider`，原 userscripts `src/cloud/`）按 host 分派，页面内同源 fetch `dop-api/opendoc` 解两种格式（3.0.0 protobuf 区块 / 2.x JSON op），前端 `spiderUtil.ts` 识别 `docs.qq.com/sheet/*`；网关/doc-crawler/契约不改。工作树 `userscripts-wt-qqdoc`(`feat/qqdoc-cloud`)、`ncjs-wt-qqdoc`(`feat/qqdoc`)。上线动作：合并 → `pnpm build:cloud && pnpm upload:cloud`（覆盖线上 `fc-chrome/userscripts/kdoc.user.js`）→ 前端发版。本地 fc-chrome 端到端方法见 `procedures/workflow-fc-chrome上线.md`。
- [ ] **P1 十项提案并行开发（09-16 全部完成，待用户确认合并）**：9 条线 + NC-JS 前端全部交付并验收通过（4 条经返工）；四仓库集成分支 `integration/ten-proposals`（COMMON `c0dca69`/SPIDER `7e79501`/API `6c413b6`/STORAGE `1a47033`）+ nc-js `feat/health-observe`(`66ec854`) 断网 CI 全绿。合并步骤、上线前置项（GitHub 4 个 secret、FC 函数 OSS 环境变量、restest 演练 deploy.sh、熔断器 dry_run 观察）见 `agent-tasks/2026-09-16-ten-proposals/95-merge-plan.md`。**09-16 12:00 已按计划合入四仓库主分支并 push（COMMON `0ead6c0`、SPIDER `7acb24a`、API `7154290`、STORAGE `3e0d490`、NC-JS `3ccd25d`），CI 全过；相关服务未重部，上线前置项未做。**
- [ ] **P0 P5 阶段 D**：阶段 C 复测 09-15 通过（G1 字面超限用户接受）；灰度 09-15 08:1x 起 30%，09-16 改 `step_every_v3_requests: 500 / step_percent: 2`（两台 res-api 宿主机 `config.yaml` + restart）。半小时邮件由 API `scripts/search_canary_report.sh 30` 发。09-16 白天 35→43%；**10:51 误回落 0%**（v3 错误 1/597 = 深翻页 page=3678 触发 ES max_result_window，v2 同样 500），11:00 用 res2 上的 `search-canary -config config.yaml -set 43 -resume` 恢复；防复发方案待用户定（open-questions）。A' 存量复检 84,791 条已入队完成。过程原文见快照 archive。
- [ ] **🔴 P0 误删事故收尾**：重爬 1,152,617 条 09-14 10:21 终态回库 637,886（quark 56.2%），解析器判失效经 1,000 条 CDP 复核 100% 一致；bnd 并发按类型拆分（`consumer_number_by_type`，bnd 150）与按类型背压均已上线。待办：API `0ad7bb3`（bnd 判定对齐）下次发版带上；告警阈值放宽待用户决定。
- [ ] **P1 xlLoadShare 收尾**：`submitInvalidDryRun=true` 日志清单 → `scripts/xl_share_probe.sh` 抽样 → 用户拍板改 false 重部；6h 后 `tools/xl-fail-export` 补投。

## 待办（P0/P1）

- [ ] **P0 队列 v2 收尾（用户人工）**：A 删 jenkins `spider-xunlei_share`、B 杀两个 2023 裸进程、C `./deploy.sh ps` 复核、D osec-res2 跑 `devops_migrate_legacy_queues`（先 dry-run）、E 看网关 precheck 日志。
- [x] ~~P0 5 爬虫全站扫描改造~~：09-16 核实**这 5 站在本任务开始前已经全部改造完成**(代码里
      `fullSweepStartupSkip`/`fullsweep:lastdone` 均已存在, 早于十项提案批次), 本文件之前的
      "待办 P0" 是过时记录, 未反映实际代码状态。09-16 提案 11(crawler-skeleton)已把 **6 站
      全部**(kkpans/dyyjmax/fuxipan/feikuai/kuakes/misoso)迁移到新抽取的通用骨架
      `services/spider-common/sitecrawler`(行为/redis 键名不变；misoso 全量是"cursor 断点
      续跑"语义，新增 `sitecrawler.WrapAwareSite` 可选接口支持，`fullsweep:lastdone` 值编码
      从 RFC3339Nano 改成 Unix 秒，上线后第一次可能多跑一次全量，安全方向可接受)。
      `SiteCommonConfig` 内嵌进 5 站配置结构体(misoso 语义不同未内嵌)。
      09-16 验收发现并修复一处系统性遗漏：dyyjmax/fuxipan/kuakes/misoso 迁移时漏传
      `EngineConfig.MinRequestInterval`，导致这 4 站的全局限速被静默关闭；已修复 + 补了
      防回归单测 `TestEngineConfigMinRequestIntervalNotDropped`(`services/bbs/sitecrawler_engine_config_test.go`)。
      详见 `knowledge/architecture-spider-sitecrawler骨架.md`。
- [ ] **P1** 删除已合并的 6 个 `spider-wt-queue-v2-*` worktree/分支；十项提案与腾讯文档任务合并后同样清理。
- [ ] **P1 待用户手动** `osec-resdb` 删两个废弃容器（需 sudo，命令见快照 archive「待办」）；**不要动** `..._ali_250918`。
- [ ] **P1** 夸克/阿里有效性检测修复上线后观察 `/v2/validShareLink` 的 `-1` 比例；确认 `clear_expire` 无异常批量删除。
- [ ] **P1 待确认** API `config.yaml` 的 ES 主机与 STORAGE/网关不一致，可能是过期集群。
- [ ] **P2 cdp3 `profile=` 调用方接入**：结束前必须发 CDP `Browser.close` 等响应；409 需退避重试 → `decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md`。

> 其余 P1/P2 长尾（funletu TLS、initEs panic、res_scheduler 观测、devops_check 迁网关、4 站点复议、misoso/dyyjmax/feikuai/kuakes 待确认、夸克 41031 业务码、bnd/xunlei checker 文案匹配、kkpans #5、STORAGE 依赖升级回归、COMMON Makefile、代理池口径）已移至 `current/tasks-backlog.md`。
