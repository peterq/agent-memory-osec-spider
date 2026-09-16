# 验收报告：ddys.io（短名 ddys，子命令 bbs_ddys）

验收对象：worktree `/home/peterq/dev/projects/1s/spider-wt-site-ddys`，分支 `feat/site-ddys` @ `4617930`。
验收时间：2026-09-16。验收方式：全部命令实跑（含一次经代理池的联网集成测试 + 一次 probe 实跑），不改代码。

## 逐项结果

### 1. 改动范围与代理池路径

```
$ git status --short          # 空
$ git log --oneline -5
4617930 feat(ddys): 新增 ddys.io(低端影视)爬虫 bbs_ddys
9ffc3de temp(site): go.mod replace 指向 common-wt-ten-proposals, 合并 master 前撤销
7e79501 Merge branch 'feat/secrets' into integration/ten-proposals
...
$ git show --stat HEAD
 PRD/2609/ddys.io.md          | 327 ++
 commands_crawler.go          |   1 +
 config/config.go             |  13 +
 config/crawler/crawler.go    |   1 +
 scripts/ddys_probe.py        | 402 ++
 services/bbs/ddys.io.go      | 579 ++
 services/bbs/ddys.io_test.go | 437 ++
```

工作区干净，改动文件集合 = `{PRD/2609/ddys.io.md, services/bbs/ddys.io.go, services/bbs/ddys.io_test.go, scripts/ddys_probe.py, config/config.go, config/crawler/crawler.go, commands_crawler.go}` ⊆ 允许清单（另有主控的 `9ffc3de temp go.mod` 提交，不属本站改动）。无 yaml/deploy.sh/.vscode/go.mod/sitecrawler 包越界改动。

代理池路径核查（`grep NeedDirect` / 原始 http client 用法 / probe 脚本直连关键字）：

```
services/bbs/ddys.io.go:156:      NeedDirect: false,
services/bbs/ddys.io_test.go:89:  NeedDirect: false,
# http.Get / http.DefaultClient / 裸 http.Client{} 用法：services/bbs/ddys.io.go、_test.go 均无匹配
# scripts/ddys_probe.py：无 urllib/requests.get/http.client 关键字
```

`services/bbs/ddys.io.go::fetch()` 是唯一发起 HTTP 的地方，只经 `p.client.Do()`（`proxy_client.ProxyClient`，`NeedDirect:false`）；测试 `newDdysTestCrawler` 同款；`scripts/ddys_probe.py` 全程用 `httputil.new_session(pool=pool, require_proxy=True)`（COMMON 封装），无 `--no-proxy` 逃生口。**结论：生产入口/测试/probe 三处均无直连代码路径。✅**

### 2. `go build ./...` / `go vet ./services/bbs/`

```
$ go build ./...          # 无输出，通过
$ go vet ./services/bbs/  # 无输出，通过
$ go vet -tags live ./services/bbs/   # 无输出，通过（PRD §9.3 第9项自述一致）
```
✅

### 3. 配置结构体 / 注册

- `config/config.go:157` `DdysConfig` 内嵌 `SiteCommonConfig \`yaml:",inline"\``（`Enabled *bool`/`FullSweepInterval`/`IncrementalInterval`/`Concurrency`/`MinRequestInterval`/`Redis` 全部继承），自有字段 `BaseUrl`/`IncrementalHeadWindow`；`ddysApplyDefault()` 对全部字段（含继承字段）给了缺省值，开关 `Enabled` 为 `*bool`。✅
- `commands_crawler.go:63` 注册 `{"bbs_ddys", ..., bbs.StartDdys}`；`config/crawler/crawler.go:29` 挂载 `Services.Ddys config.DdysConfig`。符合 99-notes.md 裁定2（注册位置以 `commands_crawler.go`/`config/crawler/crawler.go` 为准，`spider.go` 不动）。✅

### 4. EngineConfig 必填字段核对（对照骨架知识文档核对表）

`ddysEngineConfig()`（`services/bbs/ddys.io.go:176`）逐项核对：

| 字段 | 传递值 | 判定 |
|---|---|---|
| SiteName | `"ddys"` | ✅ |
| KeyPrefix | `ddysRedisKeyPrefix`="ddys:" | ✅ |
| FullSweepInterval | `conf.FullSweepInterval` | ✅ |
| IncrementalInterval | `conf.IncrementalInterval` | ✅ |
| FullSweepGate | `true`（ddys 全量=整站重扫，语义对应） | ✅ |
| MinRequestInterval | `conf.MinRequestInterval` | ✅ 且 `fetch()` 内确有调用 `p.engine.Wait()`（line 440），非零值必要且已传 |
| SeenTTL | `conf.FullSweepInterval+240h` | ✅ |
| NotifyFailStreak | `ddysNotifyFailStreak`=5 | ✅ |
| Log/Redis/Committer/Alive | `newDdysCrawler()` 拿到返回值后补上 | ✅ |
| IncrementalImmediate | 未设置(默认false)，符合"仅feikuai=true" | ✅ |
| WrapAwareSite | 未实现，ddys 全量不是断点续跑型，不需要 | ✅ |

未发现"4站漏传MinRequestInterval"类的回归。✅

### 5/6. 代理与提交类型过滤

`NeedDirect:false` + `proxy_provider.OnProxyWith` 无条件订阅，代码里无"拿不到代理就直连"的兜底分支。链接提交只经 `p.engine.Commit(&spider_common.ResLink{...})`（唯一调用点，line 404），按 `CommitCommitted`/`CommitUnsupported`/其它 三态处理，无绕过 Engine 的直接入库路径；保活只在 `engCfg.Alive = keepalive.New(...)` 里配置一次，未见站点代码里手动调用 alive。✅

### 7. 联网集成测试——本次验收实跑

默认（无 env，且不带 `-tags live`）：

```
$ go test ./services/bbs/ -run TestDdys -v
testing: warning: no tests to run
ok  	github.com/1s/enfi-spider-go/services/bbs	0.011s [no tests to run]
```
说明：ddys 测试文件用 `//go:build live`（与仓库既有 fuxipan/feikuai/kuakes 三站同款约定，非 ddys 独有），不带 `-tags live` 时测试文件不参与编译，属预期行为，不是回归。

经代理池实跑（本机 `LOCAL_CONFIG_PATH` 指向开发者随附、已 gitignore 的 `config.local.yaml`；`proxypool.py status` 确认当时 1~3 个代理存活）：

```
$ LOCAL_CONFIG_PATH=.../config.local.yaml DDYS_IT=1 timeout 900 \
  go test -tags live ./services/bbs/ -run TestDdys -v -count=1
--- PASS: TestDdysExtractLinks (纯函数, 5子用例全过)
--- PASS: TestDdysPwdExtract
--- PASS: TestDdysSlugFromUrl
--- PASS: TestDdysMovieSitemapFilter
--- PASS: TestDdysSitemapStructure (44.18s)   movies-1=5000条 movies-2=2237条
--- PASS: TestDdysHandleEntrySample (200.83s) 12条样本: found=12 committed=21 失败率0%
                                               类型分布 bnd:4 quark:10 xunleipan:7
                                               第二轮复跑: committed=0 skipDup=12(全部命中去重)
--- PASS: TestDdysIncrementalHeadWindow (26.42s) head=6: scanned=6 found=6 committed=11
--- PASS: TestDdysFullSweepSkipWait (1.02s)   三态(键不存在/未超期/已超期)全过
PASS  ok  272.462s
```

8 个用例（4 纯函数 + 4 联网 IT）全部通过，与开发 agent 自述"4 用例通过"一致（本次实际成功率甚至优于其 30% 失败容忍上限，波动属代理池抖动正常范围）。✅

### 8. probe 脚本实跑

```
$ python3 scripts/ddys_probe.py --help   # 正常显示 probe/dump/verify/sample/watermark-check
$ python3 scripts/ddys_probe.py probe
代理池就绪: 代理池可用, 当前 3 个代理
movies sitemap: [sitemap-movies-1.xml, sitemap-movies-2.xml]
  sitemap-movies-1.xml 条目=5000 lastmod范围=2026-03-02 ~ 2026-09-15
  sitemap-movies-2.xml 条目=2237 lastmod范围=2026-03-02 ~ 2026-03-02   # 与PRD"已冻结"结论一致
movies 详情页合计 = 7237
抽样3条详情页均正确解出 atob 链接(bnd+quark)
```
✅ 与 PRD §2.2/§9 结论完全吻合。

### 9. PRD 完整性

`PRD/2609/ddys.io.md` 含：接口/URL 清单(§3)、全量与增量策略(§4.2)、限速与重试(§4.4)、redis 键清单(§6)、可量化验收标准(§7，9条)、实测结果(§9，逐条对照)。与调研报告不符处已记录并解释（§2.2/§9.4：两个 movies sitemap 语义不对称，movies-2 是冻结批次而非"新批次"，与常见 sitemap 追加在末尾的惯例相反）。✅

### 10. 站点特有项重点核查

**(a) 反爬三处全走代理池，无直连**：见上第1项核查，生产入口 `newDdysCrawler`/测试 `newDdysTestCrawler`/`scripts/ddys_probe.py` 三处均 `NeedDirect:false` 或 `require_proxy=True`，未发现任何直连兜底代码路径。✅

**(b) atob 解码 + spider_contract 正则 + 非法 base64 静默跳过**：
`ddysExtractLinks()`（line 522）先用 `ddysAtobReg` 提取全部 `atob('...')` 载荷，逐个 base64 解码；`base64.StdEncoding.DecodeString` 出错（非法 base64）直接 `continue` 跳过，不中断其它载荷（line 542-545）；解码结果不以 `http(s)://` 开头的也静默跳过（line 546-550）。解码成功的候选统一交给 `spider_contract.TypeFromUrl(url) != ""` 判定 `Supported`（line 530），命中不支持类型仍上报（`skipUnsup`，不误判为无链接）。单测 `TestDdysExtractLinks` 覆盖"非法base64静默跳过"/"不支持类型(UC)"两个子用例并本次实跑通过；联网测试与 probe 实跑均验证了对真实站点 atob 载荷解码正确（quark/bnd/xunleipan 链接均正确还原）。✅

**(c) 连接失败重试上限**：`fetch()`（line 430）用固定 `backoffs = []time.Duration{3s,6s,12s,24s}`，循环 `for i := 0; i <= len(backoffs); i++`，即最多 1 次首发 + 4 次退避重试 = 5 次尝试封顶，超过后返回 `lastErr`，不会无限重试单次请求。404 直接返回 `errDdysNotFound` 不重试；非200(含403/429/5xx)和网络错误(EOF/超时/RemoteDisconnected/Bad Gateway)统一计入退避重试。本次联网实跑中实际观测到 `context deadline exceeded`/`EOF`/`unexpected EOF`/`Bad Gateway` 等错误均按此退避处理，最终仍收敛(0%~8.3%失败率区间)。✅ 上限明确，符合"最多4次"的自述。

**(d) 失败不标记已见 → 是否会导致无限重试**：
`isSeen()`(line 480) 只读不写，`markSeen()`(line 491) 只在处理到终态(全部链接提交成功/命中不支持/无链接/404)时调用；`handleEntry()` 里 `fetch` 失败(`commitError`)或任意链接提交失败(`anyFailed`)时直接 `return`，不调用 `markSeen`，因此该 slug 下一次被扫描到时会重新走一遍完整流程——**单次调用内有明确上限(见(c)，最多5次尝试)，跨轮次没有"总重试次数"计数器，理论上一个持续失败的 slug 会被反复重试直到成功或人工介入**，这点已被验收简报点名要求核查。

评估该实现的实际风险后判定**可接受、不算返工项**，理由：
1. 这是有意识的设计权衡，代码注释（line 353-357）与 PRD §4.3/§5.3 均已明确写出原因：page 级失败不标记，是为了避免"部分链接因页面级失败被永久跳过"，已成功提交的链接由下游 `CommitResLink`/`InputTask` 的 `ErrDupTask` 兜底去重，重试代价可接受。
2. 重试**不是紧循环**，而是"下一次该 slug 被扫描到"才重试一次(仍受(c)的单次5次尝试上限约束)，两种触发路径都有天然节流：
   - 全量：整站扫描周期 `FullSweepInterval`=240h(10天)一次，即使某 slug 永久失败，10天才会被重新尝试一次，量级可忽略。
   - 增量：只扫 `sitemap-movies-1.xml` **固定窗口**开头 `IncrementalHeadWindow`(默认100)条，窗口大小恒定，不会因为历史失败项累积而单调增长请求量；一个失败 slug 最多占用窗口内1个位置，直到被更新内容挤出窗口(该 sitemap 按 lastmod 降序、新内容持续追加在开头)。
   - 因此不存在"失败列表无限累积、请求量随时间发散"的情况，符合验收简报"应有上限或按轮次"里"按轮次"的语义(退避在单次调用内封顶，跨轮次的再次尝试受调度周期天然限流)。
3. 本次联网实跑不管是 12 条采样(0%~8.3%失败)还是既有其余 5 站的迁移基线（架构文档记录的 fuxipan 同样是"只在终态标记"），都是同一模式，风险可控。

**不算通过项但需记录的观察点(非阻塞)**：如果生产环境代理池长期极薄导致某些 slug 连续多轮全部失败，目前没有"失败N轮后强制标记跳过/告警"的兜底，只能靠 `NotifyFailStreak`(5，仅用于整轮成功率层面的告警)间接发现。建议后续可选增强（不要求本次改）：给 `markSeen` 增加一个"失败计数"字段，达到阈值后也标记已见并单独告警，但当前实现下窗口天然有界，暂不阻塞验收。

**(e) 最小样本经代理前台实跑一次联网测试**：本次验收已实跑（见第7项），8/8 用例通过，允许部分失败的用例(TestDdysHandleEntrySample)实际0%失败。✅

## 结论

**通过**，无返工项。

- 反爬三处(生产/测试/probe)均确认无直连路径。
- atob 解码 + spider_contract 分类 + 非法base64静默跳过均已验证(单测+联网实跑)。
- 连接失败退避重试有明确上限(最多4次退避/5次尝试)。
- "失败不标记已见"的跨轮次重试没有显式计数上限，但受限于全量10天周期与增量固定窗口大小，不会导致请求量发散，评估为可接受设计，非阻塞项；已记录一条非阻塞的后续增强建议（失败计数兜底）供后续迭代参考。
- `go build`/`go vet`(含 `-tags live`)、8个测试用例(4纯函数+4联网IT)、probe 实跑，本次验收全部重新实跑通过，PRD 记录完整，改动范围严格限定在允许清单内。
