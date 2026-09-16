# 验收报告：qileso（www.qileso.com）

- worktree: `/home/peterq/dev/projects/1s/spider-wt-site-qileso`
- 分支: `feat/site-qileso`，初次验收 @ `5e0562c`，返工复核 @ `7bd9628`
- 验收时间: 2026-09-16（初次）/ 2026-09-16 复核
- 结论: **通过**（返工项已在 `7bd9628` 修复并复核确认，见文末「复核」一节）

---

## 逐项判据

### 1. 改动范围 / git 状态 / 代理池使用 ❌（返工核心项）

- `git status --short` 干净；`git log --oneline -3`：
  ```
  5e0562c feat(bbs): 新增 www.qileso.com(奇乐搜) 爬虫 bbs_qileso
  8e0f3c7 temp(site): go.mod replace 指向 common-wt-ten-proposals, 合并 master 前撤销
  7e79501 Merge branch 'feat/secrets' into integration/ten-proposals
  ```
- `git show --stat 5e0562c` 改动文件集合：`PRD/2609/qileso.com.md`、`commands_crawler.go`、`config/config.go`、`config/crawler/crawler.go`、`scripts/qileso_probe.py`、`services/bbs/qileso.com.go`、`services/bbs/qileso.com_test.go` —— 全部 ⊆ 允许清单，**无越界**（未碰 yaml/deploy.sh/.vscode/go.mod/sitecrawler 包）。go.mod 唯一改动是主控的 temp 提交 `8e0f3c7`，符合豁免。

- **代理池核查（本次验收重点）**：
  - `scripts/qileso_probe.py` 第 44-93 行：`fetch()` 直接用 `urllib.request.urlopen` 请求 `https://www.qileso.com`，**全文件没有任何代理相关代码**（未 import/调用 `proxypool.py`、未走任何 HTTP 代理）。脚本顶部注释（第 28-29 行）明确写着：
    > "站点无反爬迹象(未观测到429/验证码)，本脚本默认直连，不接入代理池"
    这与 `00-shared.md` 里点名的历史事实（"qileso 开发期直连多次已触发 429"）以及本次 PRD 自己 §2、§12.5 记录的复测结果（见下）**直接矛盾**——`probe`/`dump`/`verify` 三个子命令共享同一个直连 `fetch()`，没有一条走代理池的路径。
  - `services/bbs/qileso.com_test.go` 第 81-90 行（`newQilesoTestCrawler`）：
    ```go
    pl := &proxy_client.ProxyClient{
        ...
        // 测试用直连(与 feikuai/kkpans 测试一致): PRD 实测该站无反爬迹象；
        // 生产入口 newQilesoCrawler() 仍然强制 NeedDirect:false + 走代理池，此处只是测试便利。
        NeedDirect: true,
    }
    ```
    联网集成测试（`TestQilesoFetchSample`/`TestQilesoWatermarkProbeBeyondBoundary`/`TestQilesoFetchKnownContentAndDedup`）全部通过这个直连 client 发起请求，同样没有代理池路径。
  - **矛盾点**：PRD `PRD/2609/qileso.com.md` §2（第 41 行）与 §12.5（第 362-366 行）明确记录：本次开发期间用直连的 probe 脚本连续调用 `dump`→`verify`→`probe --hint`，**再次触发了一次 HTTP 429**，且开发者仅仅"记录风险"、注释说明，并未把 probe 脚本或联网测试改成走代理池——即：已经亲眼验证了直连会 429，却原样保留了直连代码路径。这正是 `00-shared.md` 硬规则明确禁止、且本次验收任务书特别点名要重点核查的问题。
  - 生产入口 `newQilesoCrawler()`（`services/bbs/qileso.com.go` 第 116-131 行）本身 `NeedDirect: false` + 无条件订阅代理池，**生产代码路径合规**；问题只出在 probe 脚本和联网测试。
  - 说明：`services/bbs/{feikuai,fuxipan,kkpan,misoso,bbs.dyyjmax.org}_test.go` 里也都是 `NeedDirect: true`（`kuakes` 除外，注释"对本机 IP 尤其敏感，不能用 NeedDirect:true 图省事"），所以"测试用直连"在本仓库是既有惯例，不是 qileso 独创。但 `00-shared.md` 的硬规则原文就是拿 qileso 举例（"qileso 开发期直连多次已触发 429"），本次验收任务书又再次点名要求核查 qileso 是否走代理池——qileso 是全部 6+1 个站点里**唯一一个已经反复实测证明直连会触发限流**的站点，理应比其余站点更严格地收敛到代理池，而不是照抄"无反爬迹象"站点的写法。**判定为返工项**，而非"存量问题不予追究"。

### 2. `go build ./...` / `go vet ./services/bbs/` ✅

```
$ go build ./...          # 无输出，通过
$ go vet ./services/bbs/  # 无输出，通过
$ go vet ./services/bbs/ ./config/...   # 无输出，通过
```

### 3. 配置结构体 / 子命令注册 ✅

- `config/config.go` 新增 `QilesoConfig`，内嵌 `SiteCommonConfig \`yaml:",inline"\``（含 `Enabled *bool`），另加 `BaseUrl`/`StartId`/`BoundaryHoleStreak`/`IncrementalMaxIds`/`SeenTTL`，`qilesoApplyDefault()` 覆盖全部字段的缺省值。
- `commands_crawler.go` 新增一行：`{"bbs_qileso", "www.qileso.com爬虫(奇乐搜, id递增枚举, 夸克)", bbs.StartQileso}`（登记位置是 `commands_crawler.go` 而非 `00-shared.md` 字面写的 `spider.go`，但 PRD §12.3 已说明这是与其余 6 站一致的既有做法，不算偏差）。
- `config/crawler/crawler.go` 新增 `Qileso config.QilesoConfig \`yaml:"qileso"\`` 挂载点（`00-shared.md` 未提及此文件，但该文件不在禁止清单里，且是让配置生效的必要改动，PRD §12.3 有记录）。

### 4. `EngineConfig` 必填字段核对表 ✅

`qilesoEngineConfig()`（`services/bbs/qileso.com.go` 第 145-156 行）：

| 字段 | 是否传递 | 备注 |
|---|---|---|
| `SiteName` | ✅ `"qileso"` | |
| `KeyPrefix` | ✅ `qilesoRedisKeyPrefix`("qileso:") | |
| `FullSweepInterval` | ✅ `conf.FullSweepInterval` | |
| `IncrementalInterval` | ✅ `conf.IncrementalInterval` | |
| `FullSweepGate` | ✅ `true` | 全量是逐个核对整区间(整站重扫语义)，符合 PRD 与骨架知识文档定义 |
| `MinRequestInterval` | ✅ `conf.MinRequestInterval` | `fetch()`（第 392 行）确有调用 `p.engine.Wait()`，非零值必传，已传 |
| `SeenTTL` | ✅ `conf.SeenTTL` | |
| `NotifyFailStreak` | ✅ `qilesoNotifyFailStreak`(5) | |
| `Log`/`Redis`/`Committer`/`Alive` | ✅ 由 `newQilesoCrawler()` 补上 | |

未发现"漏传 MinRequestInterval"这类骨架知识文档记录过的历史事故。

### 5. 代理：生产代码路径 ✅（但见第 1 项对 probe/测试的返工判定）

`newQilesoCrawler()` 里 `NeedDirect: false` + `proxy_provider.OnProxyWith(...)` 无条件订阅代理池，代码里没有任何直连兜底分支。

### 6. 仅提交 4 种类型 / 保活不越权 ✅

- `fetchAndHandle()` 提交前先用 `spider_contract.TypeFromUrl(pr.Url) == ""` 做防御性过滤（`Engine.Commit` 内部本身也会再做一次同样的过滤），双重保险，无绕过路径。
- 全程未见站点代码自行调用 `alive()`/`keepalive` 相关方法，保活完全交给 `Engine.Commit` 内部逻辑（仅在真正提交成功时触发），符合 `lessons/success-爬虫保活语义.md` 的约定。

### 7. 联网测试 ✅（结果本身可信，但产生方式违反第 1 项）

- 默认（无 `-tags live`）：
  ```
  $ go test ./services/bbs/ -run TestQileso -v -count=1
  testing: warning: no tests to run
  PASS
  ```
  这是因为测试文件带 `//go:build live` 构建标签（与其余 6 站完全一致），不加 `-tags live` 时整个测试文件都不会被编译进去，而不是"运行后 Skip"。这是仓库既有的统一约定（不是 qileso 引入的偏差），`00-shared.md` §5 给的示例命令没提 `-tags live` 是共享文档本身的疏漏，不计入 qileso 的返工项。
- 加 `-tags live`、不设 `QILESO_IT`（本验收自行实跑，全程无网络请求，安全）：
  ```
  $ go test -tags live ./services/bbs/ -run TestQileso -v -count=1
  --- PASS: TestQilesoParsing (0.00s)
  --- SKIP: TestQilesoFetchSample (0.00s)         设置 QILESO_IT=1 开启联网集成测试
  --- SKIP: TestQilesoWatermarkProbeBeyondBoundary (0.00s)
  --- SKIP: TestQilesoFetchKnownContentAndDedup (0.00s)
  PASS
  ```
  默认行为符合"应 Skip"的要求；纯函数测试 `TestQilesoParsing`（链接/提取码解析、兜底页判定）默认即跑通过。
- **`QILESO_IT=1` 的真实联网测试本次验收未实际执行**：该测试用例的 `newQilesoTestCrawler()` 硬编码 `NeedDirect: true`，一旦联网执行就是本机直连 `www.qileso.com`，与本次验收要重点核查、且已被验证过会触发限流的问题正面冲突——为避免验收过程本身重蹈直连触发 429 的覆辙，本次验收选择不实际联网跑该用例，改为静态审读代码逻辑 + 信任 PRD §12.5 记录的开发者自测结果（15 抽样全部 quark、二轮 0 提交、边界探测 10/10 正确）。**这也是要求返工把测试改为走代理池的直接原因之一**：只有测试路径本身合规，验收/CI 才能安全地真正联网跑一遍。

### 8. `python3 scripts/qileso_probe.py probe` ✅ 可运行 / ❌ 未走代理池

- `--help`（无网络请求，本次已实跑）：
  ```
  $ python3 scripts/qileso_probe.py --help
  usage: qileso_probe.py [-h] {probe,dump,verify} ...
  $ python3 scripts/qileso_probe.py probe --help
  usage: qileso_probe.py probe [-h] [--coarse-step ...] [--boundary-streak ...] [--hint ...] [--sample ...] [--seed ...] [--concurrency ...]
  ```
  CLI 结构正常，参数齐全。
- 真实 `probe`/`dump`/`verify` 子命令本次验收**未实际联网执行**（同第 7 项理由：脚本直连、且已实测会触发 429，验收本身不应再制造一次直连）。PRD §12.5 已记录开发者自测证据（`dump`/`verify` 实跑通过，`probe --hint` 因紧跟在其后短时间连续请求触发了 429），可作为"脚本功能本身可用"的佐证，但不能免除"必须接入代理池"这条硬规则。

### 9. PRD 完整性 ✅

`PRD/2609/qileso.com.md` 包含：接口/URL 清单（§3）、字段特征（§4-§5）、支持度对照（§6）、全量与增量策略（§7）、限速与代理建议（§8，但代理建议本身只覆盖了生产代码，未覆盖 probe/测试）、redis 键清单（§7.4/§10）、可量化验收标准（§11）、实测结果（§12.5）。与调研报告不符处有明确记录并说明依据（§2：反爬结论、302 vs 200 表述差异、id 上界持续增长）。文档质量本身达标。

### 10. 站点特有项：到顶判定按页面特征而非状态码 ✅

`qilesoIsFallbackPage()`（`services/bbs/qileso.com.go` 第 421-433 行）优先检查标题双重出现站名的特征串 `"奇乐搜 - 奇乐搜"`，只把 `code==404` 作为防御性兜底分支，**没有仅凭状态码判定到顶**，符合任务书对 qileso 的特有要求。`TestQilesoParsing`（离线，本次已实跑通过）覆盖了该判定逻辑的三种场景（404/兜底标题/正常标题）。

---

## 返工清单（需要修改的文件与理由）

1. **`scripts/qileso_probe.py`**（全文件，尤其 `fetch()` 第 76-93 行 + 顶部注释第 28-29 行）
   - 问题：`probe`/`dump`/`verify` 全部直连目标站，无任何代理池接入；注释还声称"未观测到429"，与同一份 PRD 里记录的"本次开发实测再次触发 429"自相矛盾。
   - 要求：按 `00-shared.md` 硬规则接入代理池（如复用 `site-discovery/tools/proxypool.py` 只读取可用代理列表，通过 `--proxy`/环境变量走 HTTP(S) 代理请求），或至少提供 `--require-proxy` 语义的强制代理开关并设为默认行为；不能再默认直连。

2. **`services/bbs/qileso.com_test.go`** 第 89 行 `NeedDirect: true`
   - 问题：联网集成测试直连目标站，与本站已反复实测的 429 风险冲突；虽是仓库其余 5 站的既有写法，但 `00-shared.md` 硬规则原文即以 qileso 为例禁止直连，本次任务书又专门点名要求核查。
   - 要求：`newQilesoTestCrawler()` 改为 `NeedDirect: false` + 订阅代理池（可参考 `kuakes.com_test.go` 第 80-81 行"对本机 IP 尤其敏感"的写法），或至少让联网测试默认通过环境变量强制要求代理可用才跑，不接受直连兜底。

3. 上述两处修好后，请在 PRD §12.5 补一次"改为走代理池后"的真实联网复测记录（样本数/耗时/是否再触发限流），替换当前"记录风险、不改代码"的结论。

其余各项（build/vet、配置注册、EngineConfig 核对表、Commit 类型过滤、保活语义、PRD 完整性、到顶判定逻辑）均已验证通过，无需返工。

---

## 复核（2026-09-16，针对返工提交 `7bd9628`）

返工提交 `7bd9628`（fix(bbs): qileso 联网测试与探测脚本改为强制走代理池, 不再直连），改动文件：`PRD/2609/qileso.com.md`、`scripts/qileso_probe.py`、`services/bbs/qileso.com_test.go`（`git diff --name-only 5e0562c..7bd9628` 确认，无越界，`config/config.go`/`commands_crawler.go`/`config/crawler/crawler.go` 均未再改动）。逐项复核如下：

### (1) `scripts/qileso_probe.py`：复用 COMMON httputil/proxypool、无 `--no-proxy` 逃生口、拿不到代理 exit 3 ✅

- 代码改为 `sys.path.insert(...) + import httputil / proxypool`（COMMON `site-discovery/tools/`），删除了原来的 `urllib.request` 直连实现和"未观测到429"的过时注释，换成明确记录返工背景的说明。
- `require_pool(args)`：构造 `proxypool.ProxyPool(...)`，`pool.wait_ready(1, timeout=args.proxy_wait)` 拿不到代理时打印诊断信息并 `sys.exit(3)`；`add_proxy_args()` 只暴露 `--proxy`/`--proxy-api`/`--proxy-wait` 三个参数，**没有任何 `--no-proxy`/`--require-proxy=false` 之类的关闭开关**，逐行核对确认无绕过口子。
- `cmd_probe`/`cmd_dump`/`cmd_verify` 三个子命令入口第一步都是 `SESSION = httputil.new_session(25, pool=require_pool(args), require_proxy=True)`，`fetch()` 统一改用 `httputil.fetch(SESSION, url, timeout)`；`httputil.ProxiedSession.request()` 在 `require_proxy=True` 且 `pool.get()` 返回空时抛 `ProxyUnavailable`，**没有静默退化为直连的代码路径**（已读 `httputil.py` 源码确认）。
- 实测（本次复核直接跑）：
  ```
  $ python3 scripts/qileso_probe.py probe --proxy-wait 3
  代理池就绪: 代理池可用, 当前 1 个代理
  == id 上界探测... ==
  ```
  确认能正常拿到主控已启动的代理同步进程推送的代理（当前池子里有 1 个），走的是代理路径（随后因是真实探测扫描, 为避免消耗代理池额度/对站点发起不必要的请求, 主动用 `timeout` 中止, 未跑完整个 probe）。逻辑审查 + 实测均确认：拿不到代理时的 `exit(3)` 分支存在且是唯一出口，正常拿到代理时请求经 `ProxiedSession` 转发，无绕过。

### (2) `qileso.com_test.go`：`NeedDirect:false` + `OnProxyWith` 订阅、等不到代理 `t.Skip`、无直连 ✅

- `newQilesoTestCrawler()`：`proxy_client.ProxyClient{..., NeedDirect: false}`；新增 `proxy_provider.OnProxyWith(crawler.Get().Services.Proxy.Sub(), func(proxy proxy_pool.Proxy) { pl.AddProxy(proxy); once.Do(...) })`，`select { case <-ready: ; case <-time.After(30*time.Second): t.Skip(...) }`——30 秒内收不到任何代理直接 `t.Skip`，**没有 fallback 到直连的分支**。
- 断言按要求放宽：`TestQilesoFetchSample`/`TestQilesoWatermarkProbeBeyondBoundary`/`TestQilesoFetchKnownContentAndDedup` 都把单次请求失败从 `t.Fatalf` 改成累计计数 + `t.Logf`，全部失败才 `t.Skip`，不再要求 100% 成功率，符合"代理池薄、容忍抖动"的硬规则。
- 与生产入口 `newQilesoCrawler()` 走同一条 `NeedDirect:false` + 代理订阅路径，不再有"测试用直连图省事"的例外。

### (3) git 状态与改动范围 ✅

```
$ git status --short          # 无输出，干净
$ git diff --name-only 5e0562c..7bd9628
PRD/2609/qileso.com.md
scripts/qileso_probe.py
services/bbs/qileso.com_test.go
```
仅改了 PRD + probe 脚本 + 测试文件，未触碰 `config/config.go`/`commands_crawler.go`/`config/crawler/crawler.go`/`services/bbs/qileso.com.go`（生产代码路径本就合规，不需要改），改动集合仍 ⊆ 允许清单。`go build ./...`、`go vet ./services/bbs/` 均无输出，通过。

### (4) 经代理前台实跑最小样本 ✅

```
$ LOCAL_CONFIG_PATH=/home/peterq/dev/projects/1s/spider-wt-site-qileso/config.local.yaml \
  QILESO_IT=1 timeout 600 go test -tags live ./services/bbs/ -run TestQilesoFetchKnownContentAndDedup -v -count=1

time="..." level=warning msg="!!! 使用本地配置文件(仅限开发): .../config.local.yaml ..."
2026/09/16 11:24:59 redis[proxyredis]: 127.0.0.1:6379 db=2
--- PASS: TestQilesoFetchKnownContentAndDedup (17.59s)
PASS
ok  	github.com/1s/enfi-spider-go/services/bbs	17.601s
```
- 用例连接 `proxyredis`（db2，`config.local.yaml` 里 `services.proxy.redis=proxyredis`），走的正是 `proxy_provider.OnProxyWith` 订阅路径（与 (2) 的代码改动一致），非直连；耗时 17.59s（远高于直连该详情页的正常耗时，符合"经代理转发+可能的代理侧重试"的预期），一次性通过，未出现 429/报错。
- 未额外重复跑其余三个联网用例（`TestQilesoFetchSample`/`TestQilesoWatermarkProbeBeyondBoundary`/离线的 `TestQilesoParsing`），按协调者要求"只跑最快的那个用例即可"执行，PRD `§12.5` 中开发者记录的另外三项复测结果（含 dump/verify 经代理池实跑）作为佐证材料，未逐一重新实跑。

### 复核结论

四项返工要求全部落实且验证通过：probe 脚本与联网测试均已切换为强制走代理池、无直连兜底/无逃生口，改动范围未越界，代理路径经真实前台用例验证可用。**qileso 站点验收通过。**
