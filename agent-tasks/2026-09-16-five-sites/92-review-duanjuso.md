# 验收报告：duanjuso（www.duanjuso.cc，短剧搜）

- worktree: `/home/peterq/dev/projects/1s/spider-wt-site-duanjuso`
- 分支: `feat/site-duanjuso` @ `c547a5c`
- 验收时间: 2026-09-16
- 结论: **返工**（唯一返工项：联网测试 + probe 脚本未接入代理池，属 `99-notes.md` 裁定1 点名的全 5 站通用返工项，与 qileso 同类问题；开发 agent 据主控通知正在返工中，本报告不重复验证，其余各项均已核实通过）

---

## 逐项判据

### 1. 改动范围 / git 状态 / 代理池使用

- `git status --short` 输出为空，工作区干净。
- `git log --oneline -5`：
  ```
  c547a5c feat(bbs): 新增 www.duanjuso.cc(短剧搜) 爬虫
  d8c4e83 temp(site): go.mod replace 指向 common-wt-ten-proposals, 合并 master 前撤销
  7e79501 Merge branch 'feat/secrets' into integration/ten-proposals
  ...
  ```
- `git diff --stat d8c4e83..c547a5c`（即本站自己的提交，剔除主控 temp 提交与继承自 integration 分支的历史）：
  ```
  PRD/2609/duanjuso.cc.md          | 383 ++++++
  commands_crawler.go              |   1 +
  config/config.go                 |  15 +
  config/crawler/crawler.go        |  21 +-
  scripts/duanjuso_probe.py        | 294 ++++++
  services/bbs/duanjuso.cc.go      | 632 +++++++++
  services/bbs/duanjuso.cc_test.go | 370 ++++++
  ```
  改动文件集合 = `{PRD/2609/duanjuso.cc.md, commands_crawler.go, config/config.go, config/crawler/crawler.go, scripts/duanjuso_probe.py, services/bbs/duanjuso.cc.go, services/bbs/duanjuso.cc_test.go}`，**完全 ⊆ 允许清单**；go.mod 唯一改动是主控的 temp 提交 `d8c4e83`，符合豁免。未触碰 yaml/deploy.sh/.vscode/sitecrawler 包，**无越界**。

- **代理池核查（本次验收重点，任务书 (a)(b)(c) 三问）**：

  **(a) 生产代码路径 ✅ 合规**：`services/bbs/duanjuso.cc.go` 第 169-183 行 `newDuanjusoCrawler()`：
  ```go
  pl := &proxy_client.ProxyClient{
      ...
      NeedDirect: false,
      Scene:      "bbs_duanjuso",
  }
  pl.Init()
  proxy_provider.OnProxyWith(crawler.Get().Services.Proxy.Sub(), func(proxy proxy_pool.Proxy) {
      pl.AddProxy(proxy)
  })
  ```
  `NeedDirect: false` + 无条件订阅代理池；已委托 Explore 子 agent 核实 `illuminate/proxy-client` 的 `NeedDirect` 语义：`NeedDirect:false` 时代理池永远不会加入 "direct" 伪代理，`Do()` 本身没有针对代理池耗尽的直连兜底分支，池空时是 1 分钟超时报错而非静默直连。`fetch()`（第 531-575 行）全程只经 `p.client.Do(...)`，未见任何绕开 `p.client` 的 `http.Get`/`http.Client{}` 直连路径。**生产路径无静默直连兜底，判定通过。**

  **(b) 测试里的直连是否显式开关、默认不生效 —— 是，但不满足本批次更严格的裁定**：`services/bbs/duanjuso.cc_test.go` 第 71-79 行 `newDuanjusoTestCrawler()`：
  ```go
  pl := &proxy_client.ProxyClient{
      ...
      // 测试直连即可（生产代码路径 NeedDirect:false 已由 newDuanjusoCrawler 覆盖测试）
      NeedDirect: true,
  }
  ```
  该文件带 `//go:build live` 标签且联网用例内部 `duanjusoSkipUnlessIT(t)` 需要 `DUANJUSO_IT=1` 才会真正发起请求，**是显式的测试专用开关，默认（无 tag / 无 env）不生效**，不影响生产路径。但按 Explore 子 agent 的结论，`NeedDirect:true` 不是"代理耗尽兜底"而是让 "direct" 伪代理参与正常请求分发的随机竞争，联网跑起来时**确实会真实直连目标站**。PRD `PRD/2609/duanjuso.cc.md` §9.3/§9.4 明确记录本次开发实测联网测试是"直连站点，未经代理池"完成的。这正是 `agent-tasks/2026-09-16-five-sites/99-notes.md` 「裁定1」（2026-09-16 11:50，因 qileso 验收触发、**适用全部 5 站**）要求收敛的问题：本批次要求联网测试改为 `NeedDirect:false` + 正常订阅代理池，不再沿用存量 6 站"测试直连"的历史惯例。

  **(c) probe 脚本是否走代理池 —— 否**：`scripts/duanjuso_probe.py` 第 49、75-96 行 `fetch()` 直接用标准库 `urllib.request.urlopen`，全文件未 import/调用 `site-discovery/tools/proxypool.py` 或 `httputil`，`probe`/`dump`/`verify`/`search` 四个子命令共享同一个直连 `fetch()`，没有任何代理路径。同样属于裁定1点名的返工范围。

  **协调说明**：据主控通知，开发 agent 已针对本项在返工中（与 qileso 同一裁定），本报告不再实际发起联网测试或 probe 请求去复现/验证该问题（避免验收本身又制造一次直连），**直接记「返工中」**，其余各项按静态审读 + 可离线执行的命令验证。

### 2. `go build ./...` / `go vet` ✅

```
$ go build ./...                       # 无输出，通过
$ go vet ./services/bbs/               # 无输出，通过（默认不含 live 标签的测试文件）
$ go vet -tags live ./services/bbs/    # 无输出，通过（含测试文件，零告警）
```

### 3. 配置结构体 / 命令注册 ✅

- `config/config.go` 新增 `DuanjusoConfig`，内嵌 `SiteCommonConfig \`yaml:",inline"\``（含 `Enabled *bool` 等全部公共字段），另加 `BaseUrl`/`MaxSitemapCount`/`Keywords`/`IncrementalShareTime`/`IncrementalPageSize`/`IncrementalMaxPagePerKeyword`，`duanjusoApplyDefault()` 覆盖全部字段缺省值（第 224-270 行）。
- `config/crawler/crawler.go` 的 `Services` 结构体新增 `Duanjuso config.DuanjusoConfig \`yaml:"duanjuso"\`` 挂载点（`00-shared.md`/裁定2 确认的必需步骤）。
- `commands_crawler.go` 新增一行：`{"bbs_duanjuso", "www.duanjuso.cc(短剧搜)爬虫(夸克/百度/阿里, sitemap全量+搜索接口增量)", bbs.StartDuanjuso}`，登记位置符合裁定2「注册位置以仓库实际为准」。

### 4. `EngineConfig` 必填字段核对表 ✅

`duanjusoEngineConfig()`（`services/bbs/duanjuso.cc.go` 第 196-208 行）：

| 字段 | 是否传递 | 备注 |
|---|---|---|
| `SiteName` | ✅ `"duanjuso"` | |
| `KeyPrefix` | ✅ `duanjusoRedisKeyPrefix`("duanjuso:") | |
| `FullSweepInterval` | ✅ `conf.FullSweepInterval` | |
| `IncrementalInterval` | ✅ `conf.IncrementalInterval` | |
| `FullSweepGate` | ✅ `true` | 全量是 sitemap 存量清单的整站重扫语义，符合骨架知识文档定义 |
| `MinRequestInterval` | ✅ `conf.MinRequestInterval` | `fetch()` 第 537 行确有调用 `p.engine.Wait()`，非零值必传，已传（未重蹈骨架知识文档记录的"4 站漏传"事故） |
| `SeenTTL` | ✅ `conf.FullSweepInterval + 240*time.Hour` | |
| `NotifyFailStreak` | ✅ `duanjusoNotifyFailStreak`(5) | |
| `Log`/`Redis`/`Committer`/`Alive` | ✅ 由 `newDuanjusoCrawler()` 补上 | |
| `IncrementalImmediate` | 未显式设置（零值 false） | 与 kkpans/dyyjmax/fuxipan/kuakes/misoso 一致的默认风格，非 feikuai 风格，合理 |

### 5. 代理：生产代码路径 ✅（问题仅在测试/probe，见第 1 项）

同第 1 项 (a)：`NeedDirect: false` + 无条件订阅代理池，代码里无任何直连兜底分支。

### 6. 只提交 4 种类型 / 保活不越权 ✅

- `handleEntry`（全量）：`duanjusoExtractLink` 返回 `supported=false` 时提前 `skipUnsup`，不调用 `Commit`；`handleSearchItem`（增量）：显式 `spider_contract.TypeFromUrl(item.Link) == ""` 判空后 `skipUnsup` 提前返回。两条通道均在调用 `Engine.Commit` 前做防御性过滤，`Engine.Commit` 内部本身也会再过滤一次，双重保险，无绕过路径。
- 全程未见站点代码自行调用 `alive()`/`keepalive`，保活完全交给 `Engine.Commit` 内部在提交成功时触发，符合 `lessons/success-爬虫保活语义.md`。

### 7. 联网测试 ⏳（结果记录可信，但产生方式属返工项，本次未重跑）

- 默认（无 `-tags live`）：`go test ./services/bbs/ -run TestDuanjuso -v -count=1` → `no tests to run / PASS`（测试文件带 `//go:build live`，未加 tag 时不参与编译，符合 5+1 站既有约定，`00-shared.md` §5 示例命令未提 `-tags live` 是共享文档本身的疏漏，不计入本站返工项，与 qileso 验收结论一致）。
- `-tags live` 不设 `DUANJUSO_IT`（本次已实跑，全程无网络请求，安全）：
  ```
  --- PASS: TestDuanjusoExtractLink (含5个子用例)
  --- PASS: TestDuanjusoDocIdFromUrl
  --- PASS: TestDuanjusoPwdFromLink
  --- SKIP: TestDuanjusoSearchSample       设置 DUANJUSO_IT=1 开启联网集成测试
  --- SKIP: TestDuanjusoDetailSample
  --- SKIP: TestDuanjusoIncrementalSample
  --- SKIP: TestDuanjusoFullSweepSkipWait
  ```
  纯函数测试全部通过，联网用例默认正确 Skip。
- `DUANJUSO_IT=1` 的真实联网测试**本次验收未实际执行**：`newDuanjusoTestCrawler()` 硬编码 `NeedDirect: true`，联网跑起来会直连 `www.duanjuso.cc`，与本次验收要点名核查、且已被主控裁定要收敛的问题正面冲突。为避免验收过程本身重蹈直连覆辙，改为静态审读代码逻辑 + 信任 PRD §9.3/§9.4 记录的开发者自测结果（全量 10 条抽样 `found=10 committed=10`，二轮 `skipDup=10`；增量两关键词各1页 `found=100 committed=97 skipDup=3`，二轮 `skipDup=100`，逻辑自洽）。**待开发 agent 把测试改为走代理池后需重新联网实跑一遍并更新 PRD。**

### 8. `python3 scripts/duanjuso_probe.py probe` ✅ 结构可运行 / ❌ 未走代理池

- `--help`（无网络请求，本次已实跑）：
  ```
  $ python3 scripts/duanjuso_probe.py --help
  usage: duanjuso_probe.py [-h] {probe,dump,verify,search} ...
  $ python3 scripts/duanjuso_probe.py probe --help
  usage: duanjuso_probe.py probe [-h]
  ```
  CLI 结构正常。
- 真实 `probe`/`dump`/`verify`/`search` 子命令本次验收**未实际联网执行**（理由同第 7 项：脚本全程直连 `urllib.request`，验收本身不应再制造一次直连）。PRD §9.2/§9.3 已记录开发者自测证据（sitemap 结构、搜索接口字段抽样均正常返回），可作为"脚本功能本身可用"的佐证，但不满足裁定1"必须接入代理池"的硬性要求。

### 9. PRD 完整性 ✅

`PRD/2609/duanjuso.cc.md` 包含：接口/URL 清单（§3）、字段映射（§4）、爬虫设计/全量增量策略（§5）、配置项（§6）、可量化验收标准（§7）、风险（§8）、实测结果（§9）。与调研报告不符的两处发现（sitemap-index 含 movie-1.xml、search 接口 order 参数无效）在 §2.1 有详细记录并说明对代码的影响；`size>=60` 静默降级为 10 的发现同样记录在 §2.1 第3条与 §6 配置项注释。**文档质量达标，但 §2/§3.2/§9.3/§9.4 多处用"直连站点验证"字样描述实测过程，与本批次代理池硬规则冲突，返工后需要同步更新措辞与实测记录。**

### 10. 站点特有项：duanjuso 增量走搜索接口且不抓详情页 ✅

`handleSearchItem`（`services/bbs/duanjuso.cc.go` 第 336-377 行）逐条核对：类型过滤 → `Engine.Seen(docId)` 去重 → 直接用响应自带的 `item.Link`/`item.DiskPass` 构造 `ResLink` 提交，**全程未调用 `p.fetch()` 抓 `/doc/<id>` 详情页**，与全量通道（`handleEntry`，需要抓详情页解析 `jump-link`）完全独立、共享同一 `Engine.Seen` 去重命名空间。符合任务书对 duanjuso 的特有要求。

---

## 已核对：两处报告不符发现是否写入 PRD 并在代码处理

| 发现 | PRD 记录位置 | 代码处理 |
|---|---|---|
| sitemap-index 实际含 32 个子 sitemap（31 个 disk-N.xml + 1 个 movie-1.xml，非报告猜测的"disk-32不存在"） | §2.1 第1条、§3.1、§7验收标准第2条 | `handleEntry` 第 429-439 行：按 `strings.Contains(e.Loc, "/doc/")` 过滤而非硬编码"32个"或"disk-32不存在"，非 doc 条目计入 `skipNonDoc`，不当错误处理；`TestDuanjusoDetailSample` 测试逻辑显式跳过非 `/disk-` 子 sitemap |
| 搜索接口 `order` 参数对排序无效 | §2.1 第2条、§3.2、§5.2模式B、§8风险第1条 | `incrementalSweep`/`searchKeyword`（第 304-334 行）放弃水位线早停，改为固定翻 `IncrementalMaxPagePerKeyword` 页 + `Engine.Seen(doc_id)` 去重，注释详细说明原因 |
| `size>=60` 被静默降级为10 | §2.1 第3条、§6配置项 | `duanjusoApplyDefault` 第 257-260 行：`IncrementalPageSize` 缺省取 50，并有注释警示不建议调大 |

三处均已按要求写入 PRD 且在代码中妥善处理，**判定通过**。

---

## 返工清单

1. **`services/bbs/duanjuso.cc_test.go` 第 78 行 `NeedDirect: true`**
   - 问题：`newDuanjusoTestCrawler()` 联网测试直连目标站，与 `99-notes.md` 裁定1（因 qileso 触发、适用全部 5 站）冲突。
   - 要求：改为 `NeedDirect: false` + 正常订阅代理池（与生产入口同一条路径）；测试开始先等代理就绪（≤30s），等不到就 `t.Skip("代理池为空")`；断言用比例/下限而非 100% 成功率。
   - 状态：**据主控通知，开发 agent 正在返工中**，本报告未重复验证。

2. **`scripts/duanjuso_probe.py`**（`fetch()` 第 75-96 行）
   - 问题：`probe`/`dump`/`verify`/`search` 全部用 `urllib.request` 直连，无任何代理池接入。
   - 要求：复用 `site-discovery/tools/proxypool.py`/`httputil`，`--require-proxy` 语义为默认行为（裁定1给出了标准代码模板）。
   - 状态：**返工中**，未重复验证。

3. 上述两处修好后，需要重新联网跑一遍 `DUANJUSO_IT=1 go test -tags live ./services/bbs/ -run TestDuanjuso -v` 与 `python3 scripts/duanjuso_probe.py probe`（经代理），把结果更新进 PRD §9（当前 §2/§3.2/§9.3/§9.4 多处"直连站点验证"的措辞与实测记录需要同步替换为代理池路径下的复测结果）。

其余各项（改动范围/越界检查、build/vet、配置注册、`EngineConfig` 核对表、生产代码代理路径、4类型过滤、保活语义、增量不抓详情页、PRD 记录的两处报告不符发现的代码处理）均已验证通过，无需返工。
