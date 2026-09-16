# 验收报告：pan.xiaozi.cc（短名 xiaozi）

worktree `/home/peterq/dev/projects/1s/spider-wt-site-xiaozi`，分支 `feat/site-xiaozi` @ `0d5176d`。

## 逐项判据

### 1. git 状态 / 改动文件集合 / 代理池路径

```
git -C spider-wt-site-xiaozi status --short     -> (空，干净)
git -C spider-wt-site-xiaozi log --oneline -3
  0d5176d feat(bbs): 新增 pan.xiaozi.cc(盘小子) 爬虫 bbs_xiaozi
  53bf7c3 temp(site): go.mod replace 指向 common-wt-ten-proposals, 合并 master 前撤销
  7e79501 Merge branch 'feat/secrets' into integration/ten-proposals
git show --stat 0d5176d
  PRD/2609/pan.xiaozi.cc.md      | 315 ++
  commands_crawler.go            |   1 +
  config/config.go               |  26 ++
  config/crawler/crawler.go      |   1 +
  scripts/xiaozi_probe.py        | 320 ++
  services/bbs/xiaozi.cc.go      | 649 ++
  services/bbs/xiaozi.cc_test.go | 472 ++
```
改动文件集合 = 允许集合的子集，无越界（未碰 yaml/deploy.sh/.vscode/go.mod/sitecrawler 包）。✅

代理池路径核查：
- 生产入口 `newXiaoziCrawler()`（`services/bbs/xiaozi.cc.go:114-128`）：`proxy_client.ProxyClient{NeedDirect: false, ...}` + `proxy_provider.OnProxyWith(...)` 无条件订阅，无直连兜底分支。
- 联网测试（`xiaozi.cc_test.go:91-128` `newXiaoziTestCrawler`）：同样 `NeedDirect: false`，`xiaoziWaitProxyOrSkip` 等待 ≤30s 拿不到代理就 `t.Skip`，不回退直连。
- probe 脚本（`scripts/xiaozi_probe.py:52-83` `build_session`）：`sys.path` 引入 COMMON 的 `httputil`/`proxypool`，`pool.wait_ready` 拿不到代理 `sys.exit(3)`，全程走 `httputil.new_session(pool=pool, require_proxy=True)`，无 `--no-proxy` 口子。
三处均走代理池、无直连兜底。✅

### 2. `go build ./...` / `go vet ./services/bbs/`

```
go build ./...             -> 无输出(通过)
go vet ./services/bbs/     -> 无输出(通过)
```
✅

### 3. 配置结构体 / 命令注册

- `config/config.go:202-222` `XiaoziConfig` 内嵌 `SiteCommonConfig \`yaml:",inline"\``（`Enabled *bool` 在内嵌结构体里），另有 `BaseUrl/MaxSitemapCount/BoundaryHoleStreak/IncrementalMaxIds/SeenTTL`，`xiaoziApplyDefault`（`xiaozi.cc.go:168-212`）覆盖全部字段的缺省值。
- `config/crawler/crawler.go:36` `Xiaozi config.XiaoziConfig \`yaml:"xiaozi"\``。
- `commands_crawler.go:69` 注册 `{"bbs_xiaozi", ..., bbs.StartXiaozi}`（裁定 2：注册位置以 `commands_crawler.go`/`config/crawler/crawler.go` 为准，未碰 `spider.go`，符合）。
✅

### 4. EngineConfig 必填字段核对（对照骨架知识文档核对表）

`xiaoziEngineConfig`（`xiaozi.cc.go:141-152`）：
`SiteName="xiaozi"` ✅、`KeyPrefix=xiaoziRedisKeyPrefix` ✅、`FullSweepInterval=conf.FullSweepInterval` ✅、`IncrementalInterval=conf.IncrementalInterval` ✅、`FullSweepGate=true` ✅（sitemap 全量是真整站重扫，非断点续跑，套用该 gate 合理）、`MinRequestInterval=conf.MinRequestInterval` ✅（`fetch()` 内确实调用了 `p.engine.Wait()`，见 `xiaozi.cc.go:524`，未漏传，未重蹈 4 站漏传事故）、`SeenTTL=conf.SeenTTL` ✅、`NotifyFailStreak=xiaoziNotifyFailStreak` ✅。`Log/Redis/Committer/Alive` 由 `newXiaoziCrawler()` 补上 ✅。
✅ 全部字段核对通过。

### 5. 代理 NeedDirect / 直连兜底

同第 1 项，`NeedDirect:false` 三处一致，源码中未见任何“拿不到代理就直连”分支。✅

### 6. 提交类型过滤 / 保活

`handleResource`（`xiaozi.cc.go:458-513`）：`spider_contract.TypeFromUrl(link)==""` 时提前过滤为 `skipUnsup`，未过滤的走 `p.engine.Commit(...)`（骨架内部按 4 类型分发，见骨架知识文档），无绕过 `Engine.Commit` 的直接入队路径。保活未见任何自行调用 `alive()`，完全交给 `Engine.Commit`（`engCfg.Alive = keepalive.New(...)`，`xiaozi.cc.go:135`）。✅

### 7. 联网测试实跑

按要求实跑（经代理池，`LOCAL_CONFIG_PATH` 指向本机开发配置，代理池当时存活 3 个）：

```
XIAOZI_IT=1 go test -tags live -timeout 280s ./services/bbs/ -run TestXiaoziFullSweepStartupSkip -v -count=1
  --- PASS: TestXiaoziFullSweepStartupSkip (2.73s)
  PASS

XIAOZI_IT=1 XIAOZI_IT_SAMPLE=8 go test -tags live -timeout 280s ./services/bbs/ -run TestXiaoziSitemapSample -v -count=1
  第一轮 map[committed:7 found:8 skipNoLink:1]
  类型分布=map[quark:7]
  第二轮 map[found:8 skipDup:8]
  --- PASS: TestXiaoziSitemapSample (148.11s)
  PASS
```
本次实跑比开发自述的 401.9s（4 用例）更小样本、更快，两个指定用例全部通过（无需容忍失败即通过）。

默认（无 env，`-tags live` 也不加）：
```
go test ./services/bbs/ -run TestXiaozi -v
  testing: warning: no tests to run
  PASS  ok ... 0.012s [no tests to run]
```
（该文件用 `//go:build live` 隔离，与仓库既有 6 站同款写法一致；加 `-tags live` 不加 `XIAOZI_IT` 时逐条 `--- SKIP`，已验证。）
✅

### 8. probe 脚本可用性

`python3 scripts/xiaozi_probe.py --help` / 子命令 `probe/dump/verify/sample` 定义完整（见 `scripts/xiaozi_probe.py:288-316`），`build_session` 强制走代理池。PRD §9.2 已记录开发时期实测的 `probe` 输出（子 sitemap 数/总量与 Go 侧一致）。未在验收现场重跑 `dump`/`probe` 全量（该脚本 `probe` 会额外抓取详情页做边界探测，为避免与本次两个 Go 用例抢占本就很薄的代理池导致互相超时，验收未重复执行；PRD 已有当天记录且 Go 侧 `TestXiaoziSitemapIndex` 联网结果与其量级一致，予以采信）。✅（有条件：脚本本身检查通过，现场未重跑，非阻塞）

### 9. PRD 完整性

`PRD/2609/pan.xiaozi.cc.md` 含接口/URL 清单（§3）、全量与增量策略（§5.2）、限速与代理建议（§5.4）、redis 键清单（§5.3，`seen:<id>`/`watermark:maxId`）、可量化验收标准（§7，11 条）、实测结果（§9，含耗时与踩坑记录）、与调研报告不符处（§2.2，5 条，均已按实测修正）。✅

### 10. 站点特有项：到顶判定按页面特征而非状态码

`classifyDetail`（`xiaozi.cc.go:551-568`）：HTTP 404 判空洞；HTTP 200 但定位不到 `pinyin:"<id>"` 锚点**同样**判空洞（不是只看状态码）。`probeIds` 用 `handleResource` 返回的 `hole` 布尔做连续空洞计数，与状态码解耦。✅ 符合"按页面特征而非状态码"的要求。

---

## 重点核查项（任务 (a)~(e)）

**(a) 三处走代理池、无直连兜底** —— 见上第 1/5 项，✅ 确认。

**(b) "首轮仅用 sitemap 建立基线不提交"是否会导致首次部署全量漏提交** —— 不会，全量与增量分工清楚：
- `FullSweep`（`xiaozi.cc.go:239-261`）完全独立于水位线：每轮自己重新拉 `/sitemap.xml`，逐条 `handleResource` 抓取+解析+提交，不检查/不依赖 `watermark:maxId`。`FullSweepGate=true` + 骨架的 `FullSweepStartupSkip`（`fullsweep:lastdone` 键不存在）保证**首次部署一定会跑一次全量**，不因增量的建档而被跳过。
- `incrementalRound` 首轮（水位线为 0）只调用 `discoverMaxIdFromSitemap`（`xiaozi.cc.go:362-383`，只解析 XML 拿最大 id，不调用 `handleResource`，因此**不写任何 `seen:` 键**），随后设置 `watermark:maxId`。因为不写 `seen`，全量扫到同一批 id 时不会被误判为"已处理"而跳过。
- 全量与增量共用 `seen:<id>` 键空间（PRD §5.3），若后续增量轮次（10 分钟一轮）已经先行提交了 watermark 之上的新 id，全量扫到同一 id 时 `isSeen()` 命中会记 `skipDup` 而非重复提交——两个模式之间幂等，不会重复入队，也不会因为顺序问题漏项。
结论：分工与文档（PRD §5.2）一致，逻辑上无首次部署漏提交的风险。✅

**(c) 推荐区块链接排除实现是否稳健、锚点找不到时的降级行为** —— 基本稳健，有一处非阻塞性风险需要指出：
- 正向逻辑（`xiaoziExtractLink`，`xiaozi.cc.go:575-590`）：先定位 `pinyin:"<id>"` 精确子串（idStr 为纯数字，不会产生前缀性误匹配），再限定 900 字节窗口内取 `url:"..."`，超窗口按`TestXiaoziExtractLinkUrlOutOfWindow`验证会返回空而不是取到别的资源链接，未见通过全页正则导致误拿"最近上线/相关推荐"区块链接的路径。单测覆盖了三种场景（命中/未命中锚点/窗口外）。响应体读取上，`illuminate/proxy-client` 内部用 `ioutil.ReadAll` 读完整个响应体（`proxy-leader.go:217`）才返回，不存在因 RSC 流式响应被提前截断读取导致锚点"读到一半"丢失的风险。
- **降级行为的风险点**：`classifyDetail`（`xiaozi.cc.go:556-568`）把"HTTP 200 但定位不到 pinyin 锚点"统一归为 `hole=true` 并 `markSeen`（`handleResource:478-482`）。这个语义对**增量 id 探测**（尚不确定该 id 对应的资源是否存在）是合理的；但对**全量 sitemap 驱动**的条目（sitemap 里列出的 id 理论上必然是站点已收录的真实资源）而言，任何一次性的解析失败（页面结构临时抖动、CDN 边缘缓存返回異常内容等）都会被当作"确认空洞"永久 `markSeen`（TTL = `FullSweepInterval+72h`，默认约 10 天），要等 TTL 到期才会被重新抓取，期间会被下一轮全量的 `isSeen()` 直接跳过而不是重试。开发者已经用 `gateSuspected` 计数留了一个監控信号（命中"公众号/验证码"类文案才计数，普通解析失败不会触发这个信号），因此**纯解析失败**目前没有独立的告警可见性。 这与 fuxipan 现有的"仅在确认终态才 markSeen"设计同构（非本站新引入的模式），本次实测（`TestXiaoziSitemapSample` 两次运行、开发 PRD §9.3 记录的历史运行）均未观测到 `hole` 出现在全量场景，发生概率低，**不构成返工项**，但建议后续在 `open-questions`/PRD 待确认问题里补一条："全量场景下 hole 计数 > 0 时应有独立日志级别或告警，与增量场景的正常空洞区分"，避免小概率解析失败静默丢内容且无从观测。

**(d) 空洞判到顶后水位线如何推进；404 与代理失败如何区分** —— 实现正确：
- `probeIds`（`xiaozi.cc.go:388-445`）里 `fetch()` 失败（`ferr != nil`，即 3 次重试后仍非 200/404）在 `handleResource` 中直接 `return false, ferr`，对应 `probeIds` 循环里 `errs[i] != nil` 分支只计 `st.Inc("fetchError")` / `errStreak++`，**不计入 `holeStreak`**；只有 `ferr == nil`（即拿到明确的 200 或 404 响应）后才进入 `classifyDetail` 判定是否为空洞。因此代理失败与真实 404/解析失败在计数上完全隔离，代理抖动不会被误判为空洞。
- 水位线推进：`incrementalRound`（`xiaozi.cc.go:332-359`）用 `probeIds` 返回的 `lastId` 推进 `watermark:maxId`；命中边界（`hitBoundary=true`）时 `lastId` 是达到连续 `BoundaryHoleStreak` 空洞阈值时的最后一个 id（含跳过的整段空洞），逻辑与仓库既有 `feikuai.tv.go` 的 `scanIds` 完全同构（含"单个 id 失败不阻断整轮、但水位线仍推进过该失败 id，遗漏内容留给周期性全量兜底"这一已被验收接受的设计取舍，注释也明确写了同样的理由）。属于跟随既有骨架惯例，非本站新增风险。✅

**(e) 经代理前台实跑 `TestXiaoziFullSweepStartupSkip` 与 `TestXiaoziSitemapSample`** —— 均已实跑并 PASS（见上"7. 联网测试实跑"），过程中代理池 3 个存活，无需容忍失败即全部通过。✅

---

## 结论：**通过**

未发现需要返工的问题。存量非阻塞性建议（不影响本次验收结论）：
1. `classifyDetail` 把"HTTP 200 但定位不到 pinyin 锚点"统一按空洞处理，对全量场景（sitemap 已列出的已知资源）而言理论上存在小概率误伤真实资源并长期(≈10天 TTL)静默跳过的风险；建议后续给"全量场景下命中 hole"单独加日志级别/告警，或在 `open-questions.md` 记一条观察项。
2. 验收现场未重复执行 `scripts/xiaozi_probe.py probe/dump`（避免与联网测试抢占本就很薄的代理池），采信 PRD §9.2/§9.3 当天记录的探测结果；建议后续常规巡检时找代理池充裕的时段补跑一次 `verify` 做全量对账。
