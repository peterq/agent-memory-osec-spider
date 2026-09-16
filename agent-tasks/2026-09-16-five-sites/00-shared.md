# 五站爬虫并行开发（2026-09-16）—— 子 Agent 共享简报

所有输出用中文；代码注释用中文。你是其中一个站点的开发子 agent，各自在独立 worktree 里工作。

## 背景

站点发现第二轮筛出 5 个满足验收的网盘资源站，现在要各写一个爬虫接入取证链路（SPIDER → 网关队列 → STORAGE → ES）。
只采 4 种网盘：`bnd`(pan.baidu.com/s/…)、`ali-share`(aliyundrive|alipan.com/s/…)、`quark`(pan.quark.cn/s/…)、`xunleipan`(pan.xunlei.com/s/…)；其他类型提交前过滤。

## 你的工作目录（worktree，基于 `integration/ten-proposals`，含 sitecrawler 骨架）

```
/home/peterq/dev/projects/1s/spider-wt-site-<短名>     # 分支 feat/site-<短名>
```

- module `github.com/1s/enfi-spider-go`；分支上已有主控提交的 `temp(site): go.mod replace 指向 common-wt-ten-proposals`（合并 master 前由主控撤销），**不要再改 go.mod**。`go build ./...` 已验证通过。
- **只在自己的 worktree 里做 git 操作**（`git add`/`commit`），不要 push、不要 checkout 别的分支、不要碰主检出 `osec-spider-go` 和别的 `spider-wt-*`。
- 允许改动的文件：**自己的新文件** + `config/config.go`（加一个配置结构体）+ `config/crawler/crawler.go`（挂载 `Services.<Site>`）+ `commands_crawler.go`（加一行子命令注册；6 站既有做法，不在 `spider.go`）。
- **探测脚本、联网测试、开发期手工验证一律走代理池**（`--require-proxy` 语义），不要用 curl/requests 直连目标站「看一眼」——qileso 开发期直连多次已触发 429。
  **禁止**改 `config*.yaml`、`config.prod.yaml`、`deploy.sh`、`.vscode/`、`go.mod`、骨架包 `services/spider-common/sitecrawler/`（需要新能力先在汇报里提出）。

## 必读（按顺序，每个都说明为什么读）

1. 你站点的调研报告：`/home/peterq/dev/projects/1s/enfi-resource-common/.claude/worktrees/site-discovery-260916/site-discovery/260916/<域名>.md`
   —— 枚举方式、URL 形态、限流实测、坑都在里面，**不要重新调研**；报告与实测不符时以实测为准并在 PRD 里记录。
2. 骨架知识：`/home/peterq/dev/projects/peterq/agent-memory-osec-spider/agent-memory/knowledge/architecture-spider-sitecrawler骨架.md`
   —— `Site` 接口（`Name/FullSweep/Incremental`）、`Engine`（`Serve/RunRound/Wait/Seen/SeenChanged/Commit`）、`EngineConfig` 必填字段核对表（尤其 `MinRequestInterval` 只在你调用 `engine.Wait()` 时才传）。
3. 样板实现（在你的 worktree 里）：sitemap 枚举型看 `services/bbs/fuxipan.com.go`，数字 id 枚举 + 水位线型看 `services/bbs/feikuai.tv.go`，文章型看 `services/bbs/kuakes.com.go`；对应 `_test.go` 是联网集成测试样板；`config/config.go` 里 `FuxipanConfig` 等是配置节样板（内嵌 `SiteCommonConfig`）；`spider.go` 里 `bbs_fuxipan` 是注册样板。
4. PRD 样板：`PRD/2609/fuxipan.com.md`；探测脚本样板：`scripts/fuxipan_probe.py`。
5. 联网测试经验：`/home/peterq/dev/projects/peterq/agent-memory-osec-spider/agent-memory/lessons/success-爬虫联网集成测试.md`（假 committer + 独立 redis 前缀 + 环境变量开关）。

## 硬规则

- **[用户确认] 爬虫一律走 IP 代理池**：`NeedDirect: false` + 无条件订阅代理池；禁止本机直连目标站。
- 代理同步进程与蜻蜓白名单进程**已由主控启动**，**禁止**执行 `proxypool.py start` / `go run . dev_add_local_ip_to_qingting`（重复实例会让同一代理被重复推送）；只允许只读的 `python3 /home/peterq/dev/projects/1s/enfi-resource-common/.claude/worktrees/site-discovery-260916/site-discovery/tools/proxypool.py status`。
- **当前本地代理池很薄（1~7 个存活）**：联网测试样本要小（单个用例 ≤30 次请求）、超时放宽、失败退避重试；`code=0`/`RemoteDisconnected` 是代理侧问题，403/429 才是站点限流，测试断言不要依赖 100% 成功率。
- 保活语义：只有 `Commit` 真正成功才续期（骨架 `Engine.Commit` 已实现，别自己再调 alive）。
- 全站扫描**禁止启动即全量**：用骨架的 `FullSweepGate`（除非你的全量天然是断点续跑，则像 feikuai 一样置 false 并说明）。
- **禁止使用 Monitor / 等待后台任务通知**；所有命令前台同步执行；长命令用 `timeout`。
- **对账用抽样，不要跑全量**；全量能力留在 probe 脚本与环境变量开关里。
- 只访问公开页面，不注册不登录；数字必须有出处。

## 交付物

1. `PRD/2609/<域名>.md`：站点概况与反爬结论 / 接口与 URL 清单 / 字段特征 / 与 4 种类型的支持度 / 全量与增量策略 / 限速与代理配置建议 / redis 键清单 / **可量化验收标准** / 实测结果。
2. `services/bbs/<域名>.go`：实现 `sitecrawler.Site`，`new<Site>Crawler()`，配置节 `<Site>Config`（内嵌 `config.SiteCommonConfig`，全套缺省值，开关用 `*bool`），子命令 `bbs_<短名>` 注册进 `spider.go`。committer 声明为接口类型、redis 键前缀做成结构体字段。
3. `services/bbs/<域名>_test.go`：`<SHORT>_IT=1` 才跑的联网集成测试（假 committer、独立 redis 前缀 `<短名>-test:<pid>:`、`defer` 清键），覆盖：枚举不重不漏（抽样）、类型过滤、去重、增量水位线；默认 `t.Skip`。
4. `scripts/<短名>_probe.py`：`probe`（总数与字段样例）/ `dump`（全量导出，默认不跑）/ `verify`（抽样对账）。
5. 验证并记录到 PRD「实测结果」：
   ```bash
   cd /home/peterq/dev/projects/1s/spider-wt-site-<短名>
   go build ./... && go vet ./services/bbs/
   <SHORT>_IT=1 timeout 900 go test ./services/bbs/ -run Test<Site> -v -count=1
   ```
6. 在自己分支 `git commit`（信息用中文，**不要加 Co-Authored-By**），不 push。
7. 最终汇报（压缩）：分支与提交 hash / 子命令名 / 全量与增量策略一句话 / 联网测试结果（样本数、提交数、耗时）/ 与报告不符的发现 / 未完成项与风险。

## 注意

- 仓库有大量**存量** vet 告警与测试失败（`services/alipan`、`services/quark`、`gateway`…），只对自己的包负责，不要顺手改。
- 骨架的 `Engine.Commit` 已做 4 类型过滤 + 提交 + 保活；解析出的链接用 COMMON 的 `spider_contract` 正则（见样板），不要自写正则。
