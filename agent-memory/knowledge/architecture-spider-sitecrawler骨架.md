---
title: SPIDER 爬虫通用骨架 sitecrawler(提案11 crawler-skeleton)
type: knowledge
status: active
created_at: 2026-09-16T08:32:00+08:00
updated_at: 2026-09-16T08:32:00+08:00
priority: medium
keywords: [sitecrawler, 爬虫骨架, kkpans, feikuai]
questions:
  - services/bbs 爬虫的通用骨架长什么样
  - kkpans/feikuai 迁移后行为有没有变
  - 6 站哪些迁移了骨架、哪些没有
summary: sitecrawler 骨架接口设计、kkpans/feikuai 迁移前后 redis 键对照、6 站迁移状态
load: on-demand
related:
  - agent-memory/decisions/decision-2026-09-03-全站扫描不在启动时触发.md
  - agent-memory/lessons/success-爬虫保活语义.md
  - agent-memory/procedures/workflow-并行开发多站点爬虫.md
  - agent-memory/knowledge/architecture-spider.md
---

# SPIDER 爬虫通用骨架 sitecrawler

## 背景

`services/bbs/` 下 6 个爬虫(kkpans/dyyjmax/fuxipan/feikuai/kuakes/misoso)各自重复实现了
轮次调度、全量/增量、去重键、限速、进度统计、保活、代理池订阅。2026-09-16 十项提案批次的
「提案11 crawler-skeleton」把这套逻辑抽成通用骨架 `osec-spider-go/services/spider-common/sitecrawler`。

顺带核实了一个记忆过期问题: `agent-memory/current/tasks.md` 长期把
"5 爬虫全站扫描启动行为改造(decision-2026-09-03)"标成"待办 P0", 但代码里核查发现
kkpans/dyyjmax/fuxipan/kuakes/misoso **早在本任务开始前就已经全部改造完成**(`fullSweepStartupSkip`
/`fullsweep:lastdone` 均已存在于 git 历史里, 早于本次十项提案批次)。该决策的落地状态在此之前
从未被写回总览/tasks, 是一次纯记忆滞后, 不是代码缺陷。

## sitecrawler 包设计

路径 `osec-spider-go/services/spider-common/sitecrawler`，四个文件：

- `sitecrawler.go`：`Site` 接口——`Name() string`、`FullSweep(ctx, *Stat) error`、
  `Incremental(ctx, *Stat) error`。骨架**不管分页/游标**，站点自己决定怎么翻页/怎么并发/
  怎么记游标(通过 `Engine.Redis()`/`Engine.KeyPrefix()` 自己读写)，骨架只管轮次调度这类
  跨站点一致的部分——这是迁移风险能big大幅降低的关键：迁移只需要把"调度胶水代码"换掉，
  站点的请求/解析/分页逻辑完全不动。
- `stat.go`：`Stat` 是线程安全的命名计数器(`map[string]int` + mutex)，取代了各站各自的
  `xxxStat` 结构体(有的用 mutex 有的用 atomic int64)，`Inc`/`Add`/`Get`/`Snapshot`/
  `MaybeProgressDue` 覆盖原来 `dataMap()`/`maybeProgressDue()` 的用法。
- `config.go`：`CommonConfig`(yaml 内嵌用，字段 `Enabled/FullSweepInterval/IncrementalInterval/
  Concurrency/MinRequestInterval/SeenTTL/Redis`)——**本次未实际内嵌进任何站点的 `config.KkpansConfig`
  等结构体**，因为 kkpans/feikuai 的 `Engine` 是从各站已 `applyDefault` 过的具体值构造
  (`sitecrawler.EngineConfig{FullSweepInterval: conf.FullSweepInterval, ...}`)，不需要
  struct embedding 就能复用；该类型留作以后其余 4 站真正迁移时的内嵌蓝图，embedding 后
  yaml 键不变(yaml.v2 对匿名字段自动打平)。
- `engine.go`：`Engine`——`Serve()`(全量/增量两个 goroutine + `select{}`)、`RunRound(mode, fn)`
  (跑一轮+统计日志+失败退避告警)、`FullSweepStartupSkip`/`GetFullSweepLastDone`/
  `SetFullSweepLastDone`(decision-2026-09-03 的启动跳过判定，逐字复刻自 kkpans 原实现)、
  `Wait()`(全局最小请求间隔限速，`MinRequestInterval<=0` 时空操作)、`Seen`/`SeenChanged`
  (去重，前者存在性判断/后者内容变化判断，键为 `KeyPrefix+"seen:"+key`)、`Commit(link)`
  (过滤不支持网盘类型 + 提交 + 成功时触发保活，语义对齐
  `lessons/success-爬虫保活语义.md`：只有真正提交成功才 `alive()`)。

两个可配置开关处理了 6 站中已观察到的两种真实差异：

- `FullSweepGate bool`：`true`(kkpans 用)启用 decision-2026-09-03 的启动跳过检查、
  读写 `fullsweep:lastdone`；`false`(feikuai 用)则全量 goroutine 单纯"跑一轮睡一
  个 FullSweepInterval"——feikuai 的"全量"是按批次巡检 `[StartId,水位线]`区间的游标
  断点续跑，天然不是"整站重扫"，不需要也不应该套用这层跳过判断（fullsweep 键干脆不写）。
- `IncrementalImmediate bool`：`false`(默认，kkpans 风格)增量 goroutine 先睡一个
  `IncrementalInterval` 再第一次跑，避免和启动全量抢跑；`true`(feikuai 风格)立刻跑一次
  再睡——feikuai 首次运行水位线为 0，增量本身就承担"一次性建档"的职责，不应该被延迟。
  这是从两站原实现里实测到的真实差异，骨架用一个字段兼容，而不是强行统一成一种行为。

单测 `engine_test.go` 用假 `Site` + 本机 redis db15(连不上跳过，仓库没引入 miniredis)覆盖：
启动跳过全量(键不存在/未超期/已超期三态)、全量整轮成功才写 lastdone、增量不受
FullSweepGate 影响永远照跑、Seen/SeenChanged 去重、限速生效与否、committer 类型过滤、
Commit 只在成功时触发保活、`IncrementalImmediate` 两种启动时序。

## kkpans / feikuai 迁移前后 redis 键对照

两站均**逐一核对键名与迁移前完全一致**，未变化：

| 用途 | kkpans(键前缀 `kkpans:`) | feikuai(键前缀 `feikuai:`) |
|---|---|---|
| 全量整轮完成时间戳 | `kkpans:fullsweep:lastdone`(不变) | 无(迁移前后都没有，`FullSweepGate=false`) |
| 去重 | `kkpans:seen:<id>`(值=站点 updated_at，`Engine.SeenChanged`) | `feikuai:seen:<id>`(值=逗号拼接的已提交链接集合，站点自己在 `diffAndMarkSeen` 里用 `Engine.Redis()`/`Engine.KeyPrefix()` 维护，未接入 `Engine.Seen*`——语义是"多链接合并去重"而非单值比较，骨架的两个去重原语都不贴合，保留站点自管) |
| 增量水位线 | `kkpans:watermark:updated_at:<platform>` | `feikuai:watermark:maxId` |
| 全量游标 | 不适用(整站重扫无游标) | `feikuai:fullsweep:cursor` |

## 6 站迁移状态

| 站点 | 是否迁移到 sitecrawler | 说明 |
|---|---|---|
| kkpans | ✅ 完全迁移 | 参照实现，`FullSweepGate=true` |
| feikuai | ✅ 完全迁移 | `FullSweepGate=false`、`IncrementalImmediate=true` |
| dyyjmax | ⬜ 保留原实现 | 结构与 kkpans 接近但未迁移(时间预算内优先保证 kkpans/feikuai 迁移质量与测试覆盖)；**已具备**启动跳过全量逻辑，合规 |
| fuxipan | ⬜ 保留原实现 | 同上；sitemap 分片游标结构与 kkpans/feikuai 均不同 |
| kuakes | ⬜ 保留原实现 | 同上 |
| misoso | ⬜ 保留原实现 | 全量是"cursor 从 0 推进到 maxN 又归零"的整轮语义(`FullSweepWrapInterval`)，与 kkpans/feikuai 都不同，需要专门设计骨架的"整轮 wrap"支持才好迁移 |

四个未迁移站点的 `_test.go` 顺带做了一处**纯测试基础设施修复**(不改生产代码路径)：
原来 `newXxxTestCrawler`/`TestXxxFullSweepStartupSkip` 直接调用 `db.Redis(conf.Redis)`，
在没有 `LOCAL_CONFIG_PATH` 的 go test 环境里会因取不到 redis 配置节 `log.Fatal` 直接
`os.Exit`，**拖死同一个 `bbs` 包测试二进制里的所有其他测试**(包括新增的 kkpans/feikuai
测试)。改为本机 redis db15 + 连不上跳过，对齐 `services/gateway/search_admin/guard_test.go`
的既有写法。`go test ./services/bbs/... ./services/spider-common/sitecrawler/...` 现在
全绿(IT 用例按各自开关正常 skip)。

## 后续如果要迁移剩余 4 站

1. 先把该站 `config.go` 里的通用字段替换成内嵌 `sitecrawler.CommonConfig`(yaml 键不变)。
2. 把 `serve()`/`runRound`/`onRoundSuccess`/`onRoundFail`/去重/限速/保活相关代码整块删掉，
   改成 `sitecrawler.New(c, sitecrawler.EngineConfig{...})` + 在爬虫结构体上实现
   `Name()`/`FullSweep()`/`Incremental()`。
3. misoso 需要先确认"整轮 wrap"语义要不要提炼进骨架(目前骨架没有这个抽象，可能需要
   `Engine` 新增一个可选的"轮次冷却"字段，或维持 misoso 站点自己在 `FullSweep()`
   内部处理 wrap 判断，骨架只当作普通一轮)。
4. 迁移后必须重新核对该站全部 redis 键名不变，并跑通其现有 `_test.go`。
