---
title: SPIDER 爬虫通用骨架 sitecrawler(提案11 crawler-skeleton)
type: knowledge
status: active
created_at: 2026-09-16T08:32:00+08:00
updated_at: 2026-09-16T09:35:00+08:00
priority: medium
keywords: [sitecrawler, 爬虫骨架, WrapAwareSite, SiteCommonConfig]
questions:
  - services/bbs 爬虫的通用骨架长什么样
  - 6 站迁移到 sitecrawler 后行为有没有变、redis 键有没有变
  - misoso 的"整轮 wrap"全量语义是怎么塞进骨架的
  - SiteCommonConfig 为什么不放在 sitecrawler 包里
  - EngineConfig 漏传字段(MinRequestInterval 事故)怎么发现和防回归的
summary: sitecrawler 骨架接口设计(含 WrapAwareSite)、6 站迁移前后 redis 键逐一对照、SiteCommonConfig 内嵌避坑、EngineConfig 漏字段事故与防回归测试
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
「提案11 crawler-skeleton」把这套逻辑抽成通用骨架 `osec-spider-go/services/spider-common/sitecrawler`，
**6 站全部迁移完成**。

顺带核实了一个记忆过期问题: `agent-memory/current/tasks.md` 长期把
"5 爬虫全站扫描启动行为改造(decision-2026-09-03)"标成"待办 P0", 但代码里核查发现
kkpans/dyyjmax/fuxipan/kuakes/misoso **在本任务开始前就已经全部改造完成**(`fullSweepStartupSkip`
/`fullsweep:lastdone` 均已存在于 git 历史里, 早于本次十项提案批次)。该决策的落地状态在此之前
从未被写回总览/tasks, 是一次纯记忆滞后, 不是代码缺陷；本次骨架迁移只是把已经正确的行为
统一收敛到一份实现里。

## sitecrawler 包设计

路径 `osec-spider-go/services/spider-common/sitecrawler`，四个文件：

- `sitecrawler.go`：`Site` 接口——`Name() string`、`FullSweep(ctx, *Stat) error`、
  `Incremental(ctx, *Stat) error`。骨架**不管分页/游标**，站点自己决定怎么翻页/怎么并发/
  怎么记游标(通过 `Engine.Redis()`/`Engine.KeyPrefix()` 自己读写)，骨架只管轮次调度这类
  跨站点一致的部分——这是迁移风险能大幅降低的关键：迁移只需要把"调度胶水代码"换掉，
  站点的请求/解析/分页逻辑完全不动。
  另有可选扩展接口 `WrapAwareSite`(见下「misoso 的整轮 wrap」一节)。
- `stat.go`：`Stat` 是线程安全的命名计数器(`map[string]int` + mutex)，取代了各站各自的
  `xxxStat` 结构体(有的用 mutex 有的用 atomic int64)，`Inc`/`Add`/`Get`/`Snapshot`/
  `MaybeProgressDue` 覆盖原来 `dataMap()`/`maybeProgressDue()` 的用法。`Get` 对不存在的键
  返回零值，比"整张 map 转 `interface{}` 再断言 `.(int)`"更安全(后者在计数器从未被
  触发时会拿到 nil 断言 panic)。
- `engine.go`：`Engine`——`Serve()`(全量/增量两个 goroutine + `select{}`)、`RunRound(mode, fn)`
  (跑一轮+统计日志+失败退避告警)、`FullSweepStartupSkip`/`GetFullSweepLastDone`/
  `SetFullSweepLastDone`(decision-2026-09-03 的启动跳过判定，逐字复刻自 kkpans 原实现)、
  `Wait()`(全局最小请求间隔限速，`MinRequestInterval<=0` 时空操作)、`Seen`/`SeenChanged`
  (去重，前者存在性判断/后者内容变化判断，键为 `KeyPrefix+"seen:"+key`)、`SeenTTL()`
  (供站点自己实现 Seen/SeenChanged 覆盖不了的去重语义时复用同一份 TTL 配置)、`Commit(link)`
  (过滤不支持网盘类型 + 提交 + 成功时触发保活，语义对齐
  `lessons/success-爬虫保活语义.md`：只有真正提交成功才 `alive()`)。

三个可配置开关/接口处理了 6 站实测到的三种真实差异：

- `FullSweepGate bool`：`true`(kkpans/dyyjmax/fuxipan/kuakes/misoso 用)启用
  decision-2026-09-03 的启动跳过检查、读写 `fullsweep:lastdone`；`false`(feikuai 用)则
  全量 goroutine 单纯"跑一轮睡一个 FullSweepInterval"——feikuai 的"全量"是按批次巡检
  `[StartId,水位线]`区间的游标断点续跑，天然不是"整站重扫"，不需要也不应该套用这层跳过
  判断（fullsweep 键干脆不写）。
- `IncrementalImmediate bool`：`false`(默认，kkpans/dyyjmax/fuxipan/kuakes/misoso 风格)
  增量 goroutine 先睡一个 `IncrementalInterval` 再第一次跑，避免和启动全量抢跑；
  `true`(feikuai 风格)立刻跑一次再睡——feikuai 首次运行水位线为 0，增量本身就承担
  "一次性建档"的职责，不应该被延迟。这是从两种原实现里实测到的真实差异，骨架用一个字段
  兼容，而不是强行统一成一种行为。
- `WrapAwareSite` 接口(可选，misoso 用)：见下一节。

单测 `engine_test.go` 用假 `Site`/`fakeWrapSite` + 本机 redis db15(连不上跳过，仓库没引入
miniredis)覆盖：启动跳过全量(键不存在/未超期/已超期三态)、全量整轮成功才写 lastdone、
增量不受 FullSweepGate 影响永远照跑、Seen/SeenChanged 去重、限速生效与否、committer
类型过滤、Commit 只在成功时触发保活、`IncrementalImmediate` 两种启动时序、
`WrapAwareSite` 只在 `FullSweepWrapped()==true` 时才落 lastdone。

## misoso 的"整轮 wrap"全量语义: WrapAwareSite

misoso(626 万条，规模最大)的全量不是"一次 FullSweep 调用=整站扫一遍"，而是
"cursor 从 0 断点续跑推进到 maxN 又归零才算一整轮"；单次 `FullSweep` 调用可能因为
`MISOSO_FULL_SWEEP_ITEM_LIMIT` 截断或某个 disk 文件拉取失败而提前返回 `nil`(不是错误，
只是"这次先做这么多")。如果直接套用 Engine 默认的"FullSweep 成功返回=整轮完成，立即落
fullsweep:lastdone"，会导致游标其实还没跑完整轮时，启动跳过全量的窗口就被错误打开。

解法是新增可选接口(`sitecrawler.WrapAwareSite`)：

```go
type WrapAwareSite interface {
    Site
    FullSweepWrapped() bool // 最近一次 FullSweep 是否恰好让 cursor 完整推进到底又归零
}
```

`Engine.Serve()` 在 `FullSweep` 成功返回后，用类型断言检查站点是否实现了该接口：实现了
就只在 `FullSweepWrapped()==true` 时才 `SetFullSweepLastDone`；没实现(kkpans/dyyjmax/
fuxipan/kuakes/feikuai)保持"成功即落"的默认语义，完全不受影响。

misoso 的 `misosoCrawler` 用一个加锁的 `lastWrapCompleted bool` 字段实现该接口：
`fullSweepRound(st)` 一进入先 `setWrapCompleted(false)`，只有在
`completedAll && cursor >= maxN && maxN > 0`(原 `markFullSweepDone()` 调用点)时才
`setWrapCompleted(true)`；`FullSweepWrapped()` 读这个字段。单测
`TestServeWrapAwareSiteOnlyMarksDoneOnWrap`(sitecrawler 包)用假 `Site` 验证了这套机制。

⚠️ **一次性行为差异(已知，可接受)**：迁移前 misoso 自己把 `fullsweep:lastdone` 存成
`time.RFC3339Nano` 字符串；Engine 统一用 Unix 秒(`strconv.FormatInt`)编码，与其余 5 站
一致。键名不变(`misoso:fullsweep:lastdone`)，但**部署后第一次**读取线上遗留的旧格式值会
解析失败，`GetFullSweepLastDone` 返回 `ok=false`，效果等价于"从未完成过全量"——即上线后
第一次启动不会跳过全量。失败方向是安全的(宁可多跑一次全量，不会误跳过或丢数据)，且
影响仅限一次性: 下一次真正跑完整轮就会写回新格式，此后与其余 5 站完全一致。

## SiteCommonConfig：为什么放在 config 包而不是 sitecrawler 包

设计之初曾把"6 站共有的配置字段"命名为 `sitecrawler.CommonConfig`，打算内嵌进
`config.KkpansConfig` 等结构体。实测会导致**编译期循环依赖**：
`config`(顶层包) → `sitecrawler` → `services/spider-common` → `config/crawler` → `config`。
`config/crawler` 需要引用顶层 `config` 包里的 `KkpansConfig` 等类型，而
`services/spider-common` 又被 `sitecrawler`(committer/去重/保活等)依赖，闭环无法打破。

解法：把这个纯配置结构体直接定义**在 `config` 包本身**（`config/config.go`），改名
`SiteCommonConfig`，字段 `Enabled *bool` / `FullSweepInterval` / `IncrementalInterval` /
`Concurrency` / `MinRequestInterval` / `Redis`（均带原有 yaml 键的 tag）。5 站
(kkpans/dyyjmax/feikuai/fuxipan/kuakes)的配置结构体改成匿名内嵌
`SiteCommonConfig \`yaml:",inline"\``，misoso 因为 `FullSweepWrapInterval` 语义与
`FullSweepInterval`(整站重扫周期) 不同、混用会引起误解，**未内嵌**，保持自己独立的字段。

yaml.v2(本仓库解码用的库)对匿名内嵌字段自动"打平"，这不是新发明的模式——
`config/internal/loader/loader_test.go` 里 `config.Common \`yaml:",inline"\`` 早就是
既有写法；`config/crawler` 的 `TestProdShapedYaml` 直接断言了
`c.Services.Kkpans.Concurrency == 2`（来自内嵌 `SiteCommonConfig` 的字段提升），
证明内嵌前后 yaml 键、字段访问方式(`conf.FullSweepInterval` 等)完全不变，线上配置
文件不需要跟着改。

`Engine` 本身不依赖 `SiteCommonConfig` 类型——各站 `newXxxCrawler()` 仍是把已经
`applyDefault` 过的具体值填进 `sitecrawler.EngineConfig{FullSweepInterval: conf.FullSweepInterval, ...}`，
两者是完全解耦的两层：`SiteCommonConfig` 解决"配置结构体字段重复"，`EngineConfig`
解决"运行时调度逻辑重复"。

## 6 站迁移前后 redis 键逐一对照

全部 6 站均已核对：**键名与迁移前完全一致**（misoso 的 `fullsweep:lastdone`
除值编码方式外，见上文说明）。

| 站点(键前缀) | 全量完成时间戳 | 去重 | 增量水位线 | 全量游标 |
|---|---|---|---|---|
| kkpans(`kkpans:`) | `fullsweep:lastdone` | `seen:<id>`(值=站点 updated_at, `Engine.SeenChanged`) | `watermark:updated_at:<platform>` | 不适用(整站重扫无游标) |
| dyyjmax(`dyyjmax:`) | `fullsweep:lastdone` | `seen:<discussionId>`(值=lastPostedAt, `Engine.SeenChanged`) | `watermark:lastPostedAt` | 不适用 |
| fuxipan(`fuxipan:`) | `fullsweep:lastdone` | `seen:<docId>`(值=lastmod, 单调时间戳比较——新值早于/等于旧值即跳过, 非简单值比较, `Engine.SeenChanged` 语义不贴合, 站点自管) | `watermark:lastmod` | 不适用 |
| kuakes(`kuakes:`) | `fullsweep:lastdone` | `seen:<pid>`(值=sitemap lastmod, `Engine.SeenChanged`) | 无独立水位线键(增量靠 `sitemap-lastmod:<sitemapLoc>` 文件级缓存判断是否需要重新下载) | 不适用 |
| feikuai(`feikuai:`) | 无(迁移前后都没有，`FullSweepGate=false`) | `seen:<id>`(值=逗号拼接的已提交链接集合，`diffAndMarkSeen` 用 `Engine.Redis()`/`Engine.KeyPrefix()` 维护，"多链接合并去重"语义不贴合 `Engine.Seen*`，站点自管) | `watermark:maxId` | `fullsweep:cursor` |
| misoso(`misoso:`) | `fullsweep:lastdone`(⚠️ 值编码从 RFC3339Nano 改为 Unix 秒，见上文) | `seen:<diskFileN>`(redis hash, field=docId/value=lastmod, `HGet`/`HSet`+`Expire` 滑动过期，站点自管，骨架没有 hash 型去重原语) | 无独立水位线键(只看 sitemap 尾部最新 1 个 disk 文件) | `fullsweep:cursor` |

## 测试基础设施修复(不改生产代码路径)

6 站 `_test.go` 原来 `newXxxTestCrawler`/`TestXxxFullSweepStartupSkip` 直接调用
`db.Redis(conf.Redis)`，在没有 `LOCAL_CONFIG_PATH` 的 go test 环境里会因取不到 redis
配置节 `log.Fatal` 直接 `os.Exit`，**拖死同一个 `bbs` 包测试二进制里的所有其他测试**。
统一改为本机 redis db15 + 连不上跳过，对齐 `services/gateway/search_admin/guard_test.go`
的既有写法。`go test ./services/bbs/... ./services/spider-common/sitecrawler/... ./config/...`
现在全绿(IT 用例按各自开关正常 skip)。

## 验收发现的真实事故：4 站漏传 MinRequestInterval

09-16 验收(6 站迁移完成后)发现 `bbs.dyyjmax.org.go`/`fuxipan.com.go`/`kuakes.com.go`/
`misoso.cc.go` 四处 `sitecrawler.EngineConfig{...}` 字面量都漏传了
`MinRequestInterval: conf.MinRequestInterval`(只有 kkpans 传了；feikuai 本来就不需要，
见下表)，导致 `Engine.Wait()` 因 `MinRequestInterval<=0` 变成空操作——**四站原有的
全局最小请求间隔被静默关闭**，编译器对这类"结构体字面量漏了一个字段"完全不会报错。

**根因**：迁移时手写字面量、逐站复制粘贴，容易漏字段；此前的单测只覆盖了
`FullSweepStartupSkip`/`Seen*`/`Commit` 这几个直接影响正确性的行为点，没有专门核对
"EngineConfig 里每个该传的字段是不是都传了"。

**修复**：
1. 四处补上 `MinRequestInterval: conf.MinRequestInterval`。
2. 把每站 `newXxxCrawler()` 里拼 `EngineConfig` 的逻辑抽成纯函数
   `<site>EngineConfig(conf config.XxxConfig) sitecrawler.EngineConfig`(不含
   `Log`/`Redis`/`Committer`/`Alive` 这几个需要连活体依赖的字段，由 `newXxxCrawler()`
   在拿到返回值后再补上)。这样防回归单测能直接调用生产代码的同一份映射逻辑，而不是
   像 `newXxxTestCrawler` 那样另外手写一份 `EngineConfig` 字面量——那样两份独立维护的
   拼装逻辑各自漏字段互相测不出来。
3. 新增 `services/bbs/sitecrawler_engine_config_test.go`:
   `TestEngineConfigMinRequestIntervalNotDropped` 对 6 站各调用一次
   `<site>EngineConfig(conf)`(`conf` 来自 `crawler.Get().Services.Xxx` + 对应
   `xxxApplyDefault`)，断言 `MinRequestInterval` 等于站点配置值；feikuai 单独放行
   并在用例里写明原因。该测试不连 redis/代理池，可以在没有 `LOCAL_CONFIG_PATH` 的
   普通 `go test` 环境下跑。已实测：临时删掉 kuakes 的这一行会让测试正确失败
   (`kuakes: EngineConfig.MinRequestInterval=0, 期望等于...`)，恢复后转绿，
   证明测试确实能拦住这一类回归。

### EngineConfig 必填字段核对表(以后新迁移站点时逐项核对)

| 字段 | 来源 | 6 站是否一致传递 |
|---|---|---|
| `SiteName` | 站点名字符串常量 | ✅ 6/6 |
| `Log`/`Redis`/`Committer`/`Alive` | 由 `newXxxCrawler()` 在纯函数返回后补上(需要活体依赖) | ✅ 6/6 |
| `KeyPrefix` | `<site>RedisKeyPrefix` 常量 | ✅ 6/6 |
| `FullSweepInterval` | `conf.FullSweepInterval`(misoso 是 `conf.FullSweepWrapInterval`) | ✅ 6/6 |
| `IncrementalInterval` | `conf.IncrementalInterval` | ✅ 6/6 |
| `FullSweepGate` | kkpans/dyyjmax/fuxipan/kuakes/misoso=`true`, feikuai=`false` | ✅ 6/6(按站点语义) |
| **`MinRequestInterval`** | `conf.MinRequestInterval` | ⚠️ **本次事故点**：迁移时 4/6 站漏传，已修复；feikuai 故意不传(见下) |
| `SeenTTL` | 各站公式不同(见 `Seen*`/`SeenTTL()` 用法) | ✅ 6/6 |
| `NotifyFailStreak` | `<site>NotifyFailStreak` 常量 | ✅ 6/6 |
| `IncrementalImmediate` | 仅 feikuai=`true`，其余默认 `false` | ✅ 6/6 |
| `WrapAwareSite`(可选接口，非 EngineConfig 字段) | 仅 misoso 实现 | ✅ |

**`MinRequestInterval` 该不该传，唯一的判断依据是站点是否调用 `p.engine.Wait()`**：
kkpans/dyyjmax/fuxipan/kuakes/misoso 的 `fetch()` 里都调用了 `p.engine.Wait()`，必须传
非零值；feikuai 的限速完全交给 `proxy_client.MinIntervalPerProxyEveryTowReq`(按代理
限速)，`fetch()` 不调用 `engine.Wait()`，传了也不会生效，留空(0)是有意为之。
以后新迁移站点/新增字段时，照这张表逐项核对，比"肉眼比对 6 份字面量"更可靠。

## 如果还要往骨架加能力

- 目前只有 misoso 用到 `WrapAwareSite`；如果未来新站点也是"断点续跑、多次调用才算一轮"
  的结构，直接实现这个接口即可，不需要改 Engine。
- `SiteCommonConfig` 目前只有 6 个字段，故意保持最小——新字段先看是否真的所有站点都需要，
  不要为了"以防万一"塞进去。
- misoso 的 hash 型去重(`HGet`/`HSet`+`Expire`)和 fuxipan 的单调时间戳去重、feikuai 的
  多链接合并去重，都是"骨架现有 Seen/SeenChanged 语义不贴合、故意保留站点自管"的例子——
  不要强行把这些也塞进 Engine，两个去重原语已经覆盖了最常见的场景(存在性/值变化)，
  更复杂的语义交给站点直接用 `Engine.Redis()`/`Engine.KeyPrefix()`/`Engine.SeenTTL()`
  自己拼是更清晰的做法。
