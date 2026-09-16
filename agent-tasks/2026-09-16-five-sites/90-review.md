# 验收简报（验收子 agent 专用）

对指定站点的分支做验收，**只看新增包与两处注册**，存量问题如实报告不改。全部用中文。

## 逐项判据（每条给出证据：命令 + 输出摘录）

1. `git -C <worktree> status --short` 干净、`git log --oneline -3` 有本站提交；改动文件集合 ⊆ {`PRD/2609/<域名>.md`, `services/bbs/<域名>.go`, `services/bbs/<域名>_test.go`, `scripts/<短名>_probe.py`, `config/config.go`, `config/crawler/crawler.go`, `commands_crawler.go`, 主控的 temp go.mod 提交}。
   另查：`scripts/<短名>_probe.py` 与联网测试是否**走代理池**（复用 `proxy_client`/代理订阅，或 Python 侧复用 COMMON `site-discovery/tools/proxypool.py`），有直连目标站的代码路径即**返工**。有越界（yaml/deploy.sh/.vscode/go.mod/sitecrawler 包）即**不通过**。
2. `go build ./...` 通过；`go vet ./services/bbs/` 对新文件零告警。
3. `config/config.go` 新结构体内嵌 `SiteCommonConfig`、全套缺省值、开关 `*bool`；`spider.go` 注册 `bbs_<短名>`。
4. 对照 `knowledge/architecture-spider-sitecrawler骨架.md` 的 **EngineConfig 必填字段核对表**逐项核对：`SiteName/KeyPrefix/FullSweepInterval/IncrementalInterval/FullSweepGate/SeenTTL/NotifyFailStreak`；调用了 `engine.Wait()` 则 `MinRequestInterval` 必须非零。
5. 代理：`NeedDirect:false`、订阅代理池；代码里无任何直连兜底。
6. 只提交 4 种类型（走 `Engine.Commit`，无绕过）；保活不自行调用。
7. 联网测试：`<SHORT>_IT=1 timeout 900 go test ./services/bbs/ -run Test<Site> -v -count=1` **实际跑一遍**（样本小），贴结果；默认（无 env）`go test ./services/bbs/ -run Test<Site>` 应 Skip。
8. `python3 scripts/<短名>_probe.py probe` 能跑出总数/样例（走代理；`--help` 可用）。
9. PRD 含：接口/URL 清单、全量与增量策略、限速与代理建议、redis 键清单、可量化验收标准、实测结果；与调研报告不符处有记录。
10. 站点特有项：duanjuso 增量走搜索接口且不抓详情页；xiaozi/qileso 到顶判定按页面特征而非状态码；jsnoteclub 提取码解析与 `/yunpan/` 变化检测；ddys `atob` 解码 + 退避重试 + 无直连。

## 产出

`agent-tasks/2026-09-16-five-sites/9x-review-<短名>.md`：逐项 ✅/❌ + 证据；结论「通过 / 返工（列出具体项）」。返工项写清文件与行号。
