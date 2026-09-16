# 验收报告：jsnoteclub.com（灵犀笔记）

worktree: `/home/peterq/dev/projects/1s/spider-wt-site-jsnoteclub`，分支 `feat/site-jsnoteclub` @ `57ccff8`。

## 逐项判据

### 1. 文件范围 / 代理池 / 越界检查 ✅

```
git -C /home/peterq/dev/projects/1s/spider-wt-site-jsnoteclub status --short   # 空，干净
git -C ... log --oneline -3
  57ccff8 feat(bbs): 新增 jsnoteclub.com(灵犀笔记)爬虫, sitemap-posts枚举+/yunpan/汇总页
  08896b8 temp(site): go.mod replace 指向 common-wt-ten-proposals, 合并 master 前撤销
  ...
git show --stat 57ccff8
  PRD/2609/jsnoteclub.com.md | services/bbs/jsnoteclub.com.go | services/bbs/jsnoteclub.com_test.go |
  scripts/jsnoteclub_probe.py | config/config.go | config/crawler/crawler.go | commands_crawler.go
git show --stat 08896b8
  go.mod | 2 +-   （主控的 temp 提交，允许）
```

改动文件集合 = `{PRD/2609/jsnoteclub.com.md, services/bbs/jsnoteclub.com.go, services/bbs/jsnoteclub.com_test.go, scripts/jsnoteclub_probe.py, config/config.go, config/crawler/crawler.go, commands_crawler.go}` + 主控 temp go.mod 提交，**完全 ⊆ 允许集合，无越界**（未碰 yaml/deploy.sh/.vscode/sitecrawler 包）。

代理池核查：
- `scripts/jsnoteclub_probe.py`：`sys.path.insert(...site-discovery/tools)` 复用 COMMON `httputil`/`proxypool`，`main()` 里 `pool.wait_ready` 拿不到代理 `sys.exit(3)`，`httputil.new_session(require_proxy=True)` 全程无直连分支（第42-47、262-274行）。实测 `python3 scripts/jsnoteclub_probe.py probe` 两次调用：第一次因代理池太薄(1个存活)3次重试后失败并 `RuntimeError` 退出（未回退直连，符合预期）；第二次(代理刷新后)成功，输出与 PRD §2.2/§2.5 完全一致（sitemap 1448 条、`/yunpan/` 271 条 quark184/xunleipan63/bnd24）。
- `services/bbs/jsnoteclub.com_test.go`：`newJsnoteclubTestCrawler` 里 `NeedDirect: false`，`proxy_provider.OnProxyWith` 订阅，30s 等不到任何代理 `t.Skip`（第84-100行），无直连代码路径。
- 生产入口 `newJsnoteclubCrawler()`（jsnoteclub.com.go 第140-154行）同样 `NeedDirect: false` + 无条件订阅代理池，无兜底直连分支。

**结论：✅ 全部经代理池，无直连兜底，无越界。**

### 2. build / vet ✅

```
go build ./...                     # 通过，无输出
go vet ./services/bbs/             # 通过，无输出
go vet -tags live ./services/bbs/  # 通过，无输出（覆盖 _test.go）
```

### 3. 配置结构体 / 命令注册 ✅

- `config/config.go`：`JsnoteclubConfig` 内嵌 `SiteCommonConfig \`yaml:",inline"\``（含 `Enabled *bool`），另有 `BaseUrl`/`YunpanPath`/`MaxPosts`，全部在 `jsnoteclubApplyDefault`（jsnoteclub.com.go 第249-280行）里有缺省值，可脱离线上 yaml 独立跑起来。
- `config/crawler/crawler.go`：`Services` 结构体新增 `Jsnoteclub config.JsnoteclubConfig \`yaml:"jsnoteclub"\``。
- `commands_crawler.go`：新增 `{"bbs_jsnoteclub", ..., bbs.StartJsnoteclub}`（按 99-notes.md 裁定2，注册位置正确，不是 `spider.go`）。

### 4. EngineConfig 必填字段核对（对照骨架知识文档） ✅

`jsnoteclubEngineConfig`（jsnoteclub.com.go 第168-180行）：

| 字段 | 值 | 判定 |
|---|---|---|
| SiteName | `"jsnoteclub"` | ✅ |
| KeyPrefix | `jsnoteclubRedisKeyPrefix`="jsnoteclub:" | ✅ |
| FullSweepInterval | `conf.FullSweepInterval`(缺省24h) | ✅ |
| IncrementalInterval | `conf.IncrementalInterval`(缺省15min) | ✅ |
| FullSweepGate | `true` | ✅ 全站整站重扫语义，与 fuxipan/kuakes 同类 |
| MinRequestInterval | `conf.MinRequestInterval`(缺省300ms) | ✅ 已传，`fetch()` 里确有调用 `p.engine.Wait()`（第565行），必须非零，符合 |
| SeenTTL | `FullSweepInterval+240h` | ✅ |
| NotifyFailStreak | `jsnoteclubNotifyFailStreak`=5 | ✅ |
| Log/Redis/Committer/Alive | `newJsnoteclubCrawler()` 补上 | ✅ |

未实现 `WrapAwareSite`：合理，本站全量是"一次调用遍历完整 sitemap"，不是断点续跑多次调用型（不需要）。

### 5. 代理与直连 ✅（并入第1项证据，重复不再赘述）

### 6. 只提交4种类型、无绕过 Commit、无自行调保活 ✅

- `handleArticle`/`sweepYunpan` 均只通过 `p.engine.Commit(&spider_common.ResLink{...})` 提交（第302、388行），无其他提交路径。
- 未见任何直接调用 `keepalive`/`alive()` 的代码，`Alive` 只在 `newJsnoteclubCrawler()` 里赋值给 `EngineConfig.Alive`，由骨架 `Engine.Commit` 内部管理。

### 7. 联网测试实跑 ✅

```
LOCAL_CONFIG_PATH=/home/peterq/dev/projects/1s/spider-wt-site-jsnoteclub/config.local.yaml JSNOTECLUB_IT=1 \
  timeout 600 go test -tags live ./services/bbs/ -run TestJsnoteclub -v -count=1
```
结果（本次验收实跑，非开发自述复述）：
```
--- PASS: TestJsnoteclubExtractLinks (0.00s)
--- PASS: TestJsnoteclubExtractLinksFallbackDomainScan (0.00s)
--- PASS: TestJsnoteclubLinksHash (0.00s)
--- PASS: TestJsnoteclubParseTime (0.00s)
--- PASS: TestJsnoteclubSitemapPosts (1.92s)      sitemap-posts.xml 条目数 = 1448
--- PASS: TestJsnoteclubArticleSample (100.96s)   首轮 map[committed:49 fetchError:1 found:10]；次轮(去重) map[committed:5 found:10 skipDup:9]
--- PASS: TestJsnoteclubYunpan (8.92s)            首轮 map[yunpanCommitted:271 yunpanFound:271]；次轮 map[yunpanFound:271 yunpanUnchanged:1]
--- PASS: TestJsnoteclubFullSweepStartupSkip (0.01s)
PASS  ok  	github.com/1s/enfi-spider-go/services/bbs	111.829s
```
说明：首轮样本10篇中1篇因代理侧 `unexpected EOF` 抓取失败(fetchError:1)、未被标记已见；次轮该文章重新抓取成功并提交(committed:5)，其余9篇精确命中 `skipDup`——与 `seenAfterRound1` 断言逻辑吻合，不是 100% 成功率断言，符合"代理池薄、允许部分失败"的项目要求。

默认（无 `JSNOTECLUB_IT`，含 `-tags live`）：全部联网用例正确 `SKIP`，纯函数测试正常跑；不加 `-tags live` 时因构建约束整个 `_test.go` 不参与编译（`[no tests to run]`），此为仓库 2026-09-16 起统一的 `//go:build live` 约定（PRD §9.2 已如实记录与共享简报命令的出入），其余5站同款，不算返工项。

### 8. probe 脚本 ✅

`python3 scripts/jsnoteclub_probe.py --help` 正常列出 `probe/dump/verify/sample` 四个子命令与代理参数；`probe` 子命令本次验收实跑两次，第二次成功，输出（sitemap 1448 条、`/yunpan/` 271 条 quark184/xunleipan63/bnd24）与 Go 侧联网测试、PRD 记录三方一致。

### 9. PRD 完整性 ✅

`PRD/2609/jsnoteclub.com.md` 含接口/URL清单(§3)、全量与增量策略(§5.2-5.3)、限速与代理建议(§5.5)、redis 键清单(§5.6)、可量化验收标准(§7)、实测结果(§9)，且如实记录了与调研报告的出入（§2.1 模板链接导致规模推算偏差、§9.2 三处与共享简报的出入）。

### 10. 站点特有项：提取码解析 + /yunpan/ 变化检测 ✅（本次验收重点）

**(c) 提取码解析**：`jsnoteclubPwdReg = [?&]pwd=([0-9a-zA-Z]+)`，从完整 URL 里解析（PRD §3.2 确认本站密码始终拼在 `?pwd=` 上，从无独立"提取码:xxxx"文字标注）；单测 `TestJsnoteclubExtractLinks` 覆盖夸克(无pwd)/迅雷(pwd=yeqd，且验证 href 尾部孤立 `#` 被正确去掉)/百度(pwd=za5t)三种情形，PASS。

**/yunpan/ 变化检测**：`sweepYunpan`（第285-320行）用提取到的"链接(URL+pwd)排序后 sha1"作为内容指纹（而非原始 HTML 哈希，避免埋点/文案变化误判），`full=true`（全量）无条件重新提交一遍，`full=false`（增量）命中 `SeenChanged` 未变化才跳过。实测：首轮 271 条全部提交，短时间内二轮判定 `yunpanUnchanged`、0 新提交，符合设计。

**(b) "解析成功即标记已见"是否会漏掉同一篇文章后续新增链接**——**重点核查结论：不会漏，设计正确**。关键在于 `markArticleSeen(key, lastmod)`/`isArticleSeen(key, lastmod)`（第408-423行）存的不是一个简单的布尔"见过"标记，而是**"这个路径在这个 lastmod 版本下已处理过"**：
  - 若文章被编辑新增链接，Ghost 会连带更新 `updated_at`（即 sitemap `lastmod`，PRD §2.4 已实测验证该字段与站点更新节奏吻合、非静态占位值），下一轮 `sitemap-posts.xml` 里该条目的 `lastmod` 随之变化；
  - `isArticleSeen` 比较"redis 存的旧 lastmod" vs "本轮 sitemap 给出的新 lastmod"，不相等则判定未见过，`Incremental()` 的 `lm.After(watermark)` 过滤与 `FullSweep()` 逐条 `isArticleSeen` 检查都会重新纳入处理，重新抓取正文、提取全部（含新增的）链接并提交；
  - `handleArticle` 里"解析成功即标记已见"这句自述准确说的是"单条链接提交结果(成功/ErrDupTask/不支持)不影响是否标记"，而不是"一旦见过永久不再抓取"——两者是正交的设计维度，该策略只解决"全站模板链接导致的 ErrDupTask 造成无限重试"问题(§5.4)，不影响"lastmod 变化触发重新抓取"这条路径。
  - 唯一的风险前提是"站点在新增链接时是否一定会同步更新 lastmod"，这依赖站点行为、非爬虫可控，PRD §2.4 已用排序特征+日期范围两个独立证据验证 lastmod 有意义、可信，且与 `bbs_fuxipan`/`bbs_kuakes` 采用同样假设一致，是本仓库现有的通用做法，不是本站独有风险。

**(a) 代理池**：见第1项，测试与 probe 均实测走代理池，无直连兜底。

**(d) 联网测试小样本实跑**：见第7项，本次验收独立实跑一遍（非复述开发自述），走代理，允许部分失败（fetchError:1/10），符合要求。

## 结论

**通过，无需返工。**

补充观察（非阻塞，供参考）：
1. probe 脚本 `fetch()` 3次重试全部失败时会 `raise RuntimeError` 直接终止整个命令（而不是像 Go 侧联网测试那样"跳过/降级统计"），在当前代理池样本极薄(1~2个存活)时偶发需要人工重跑；这是探测脚本一次性运行的合理取舍(不像长驻爬虫需要自愈)，不构成缺陷。
2. `services/bbs/jsnoteclub.com_test.go` 的 `jsnoteclubFakeCommitter` 是纯内存假提交器、从不返回错误，因此联网测试实际未真正触发生产环境里"模板链接命中真实网关 `ErrDupTask`"这条路径（该假设只在 PRD 里用人工比对佐证，未被联网测试直接验证）；属已知测试基础设施局限（与"success-爬虫联网集成测试"经验一致，用假 committer 避免污染线上队列），不影响本次验收结论。
