# 角色 80：爬虫通用骨架 + 启动不重扫全站（提案 11）

短名 `crawler-skeleton`。worktree：`spider-wt-crawler-skeleton`（分支 `feat/crawler-skeleton`）。只改 SPIDER。

## 目标

`services/bbs/` 下 6 个站点爬虫（kkpans/dyyjmax/feikuai/fuxipan/kuakes/misoso）各自实现了轮次调度、全量/增量、去重键、限速、进度统计、保活、代理池订阅；抽成通用骨架 `services/spider-common/sitecrawler`，
6 个爬虫改为「站点适配器 + 骨架」，并一次性落实决策「全站扫描不在启动时触发」：全量整轮成功写 redis `<site>:fullsweep:lastdone`，启动时未超 `FullSweepInterval` 就跳过全量只跑增量。

## 必读

1. `agent-memory/decisions/decision-2026-09-03-全站扫描不在启动时触发.md`（口径）；`agent-memory/current/tasks.md` 「P0 按决策改造 5 个爬虫」。
2. `agent-memory/lessons/success-爬虫保活语义.md`（keepalive 只在 `CommitResLink` 返回 nil 时续期）；`agent-memory/procedures/workflow-并行开发多站点爬虫.md` §5（`NeedDirect:false`、无条件订阅代理池、只采 4 种网盘、`committer` 接口化、redis 键前缀结构体字段）。
3. `services/bbs/kkpan.com.go`（已有 `fullSweepLastDone`/`fullSweepStartupSkip`，**是参照实现**）、`feikuai.tv.go`（游标分批全量，天然合规）、其余 4 个爬虫与各自 `_test.go`；`services/spider-common/` 现有公共包；`config/` 里各站配置结构体与 `applyDefault`。
4. `agent-memory/knowledge/domain-站点-kkpans.md`、`domain-站点-misoso.md`、`domain-站点-2609接入批次.md`（各站特有约束：限速、Crawl-delay、SeenTTL）。

## 设计

- `sitecrawler` 包：
  - `Site` 接口：`Name()`, `Incremental(ctx, *Stat) error`, `FullSweep(ctx, *Stat) error`（内部自己分页/游标，可通过 `Progress` 回调持久化游标）, 可选 `Resumable`（全量游标断点）。
  - 骨架负责：轮次循环与间隔、全量/增量调度与 `fullsweep:lastdone` 启动跳过、去重键（`seen:<site>:<key>` + TTL）、限速器（每站 `rps`）、代理池订阅、`committer` 接口（过滤非 4 种网盘）、保活续期语义、统计与结构化日志（沿用现有 `Stat.dataMap` 风格）、失败退避。
  - 配置：`SiteCommonConfig{RoundInterval, FullSweepInterval, SeenTTL, Rps, Enabled *bool ...}` 内嵌到各站配置，缺省值内置；各站原有字段保持兼容（yaml 键不变，线上配置不改也能跑）。
  - 单测：用假 `Site` 验证「启动跳过全量」「全量成功才写 lastdone」「增量照跑」「去重」「限速」「committer 过滤」。
- 6 个爬虫迁移：**行为不变**（请求、解析、限速数值、redis 键名**必须保持**，否则线上去重键/游标丢失重扫）；每站迁移后跑其现有 `_test.go`。迁移顺序：kkpans（最接近）→ feikuai → 其余；若某站结构差异大迁不动，保留原实现但至少补上启动跳过全量，并在汇报说明。
- 命令表 `commands_crawler.go` 不改名，`Start*` 入口保留。

## 文件所有权

`services/spider-common/sitecrawler/**`、`services/bbs/**`、`config/` 中 6 站配置结构体所在文件（只加内嵌字段/缺省值）。不动 `spider.go`、`commands_crawler.go`（除非必须，须在汇报说明）。

## 验证

`go build ./...`；`go vet`/`go test ./services/spider-common/sitecrawler/... ./services/bbs/...`（不带联网 IT 标签）；对每站列出「迁移前后 redis 键名对照表」证明未变。

## 交付

分支/提交、骨架接口说明、6 站迁移状态表（完成/保留原实现+仅加启动跳过）、键名对照表、测试输出。
