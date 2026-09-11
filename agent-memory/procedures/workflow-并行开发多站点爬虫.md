---
title: 工作流：用并行子 Agent + git worktree 同时开发多个站点爬虫
type: procedure
status: active
created_at: 2026-09-03T15:45:00+08:00
updated_at: 2026-09-03T15:45:00+08:00
priority: high
keywords: [并行开发, worktree, 子agent, 合并, 冲突, 代理池共享, Monitor卡死]
summary: 一次接入多个新站点时的分工方式：worktree 隔离、共享资源集中准备、冲突面收敛、合并与验收
load: on-demand
related:
  - agent-memory/procedures/workflow-新站点调研.md
  - agent-memory/lessons/success-本地代理池打通.md
  - agent-memory/lessons/failure-haisou搜索接口收紧.md
---

# 并行开发多站点爬虫

[实测 2026-09-03] 用这套流程一次接入 6 个站点（dyyjmax / fuxipan / feikuai /
kuakes / misoso / haisou），5 个联网验收通过并合并，全程无返工。

## 1. 共享资源由主会话集中准备，**绝不让子 Agent 各自去做**

```bash
cd osec-spider-go && go run . dev_add_local_ip_to_qingting &          # 蜻蜓白名单，常驻
python3 enfi-resource-common/site-discovery/tools/proxypool.py start  # 生产代理频道同步
python3 enfi-resource-common/site-discovery/tools/proxypool.py status # 确认在跑
```

**为什么必须集中**：每多跑一个同步进程，同一个代理 IP 就会被重复推送一次，
代理池规模虚高，且对同一 IP 的实际请求频率成倍上升，更容易被目标站封。
派活时要在提示词里**明确禁止**子 Agent 执行这两条命令，只允许跑只读的 `proxypool.py status`。

## 2. 每站一个 worktree + 独立分支

```bash
cd osec-spider-go && ./scripts/new_worktree.sh feat/spider-<站点短名>
```

必须用脚本，别手工 `git worktree add`——worktree 要和 `enfi-resource-common` 同级
（go.mod 的 `replace` 是相对路径），脚本还会补齐 gitignore 掉的 `change_proxy_config.go`。

## 3. 提前收敛冲突面（**这条最省事**）

在派活的提示词里就写死：**只允许改自己的新文件 + `config/config.go` + `spider.go`**，
不要碰 `config_dev.yaml`、`config.prod.yaml`、`deploy.sh`、`.vscode/launch.json`。

实测对比：前两批没加这条约束，dyyjmax 与 kuakes 都改了 `config*.yaml`，
kuakes 还改了 `deploy.sh` 和 `.vscode/launch.json`；后两批加了约束，
冲突就只剩 `config/config.go` 和 `spider.go` 两处（各加一个结构体 + 一行注册），
解法统一是「全部保留、按字母序排列」，非常机械。

## 4. 并行度与批次

最大 4 个并发子 Agent。**把对同一共享资源压力最大的站点错开批次**——
代理池是全局共享的，6 个爬虫同时联网测试会争抢同一批代理 IP，
既拖慢彼此，也更容易把目标站惹毛。规模最大 / 有 IP 配额限制的站点放后面单独跑。

## 5. 子 Agent 提示词里必须写的几条

- 先读该站的调研报告，**不要重新调研**（但见 §7 的例外）。
- 只采 4 种网盘类型，提交前过滤，否则刷 `unsupported type` 错误日志。
- `NeedDirect: false` + 无条件订阅代理池。
- 配置节给全套内置缺省值，开关字段用 `*bool`。
- `committer` 声明成接口类型、redis 键前缀做成结构体字段（否则测试没法注入）。
- **禁止使用 Monitor / 起需要等待通知的后台任务**，所有命令前台同步执行。
- **对账用抽样，不要跑全量**；全量能力保留在 probe 脚本和环境变量开关里。

## 6. 两个反复出现的子 Agent 失败模式

### 6.1 卡在「等自己起的后台任务」上

4 个子 Agent 里有 3 个都停在「我起了个后台 dump / Monitor，等通知」，
而那个通知永远不会来（或任务早已结束）。表现是 Agent 报 completed，
但 `result` 是「I'll wait for the notification before continuing」。

**处理**：主会话直接去查目标进程在不在（`pgrep -af`）、产物文件有没有，
然后用 SendMessage 明确告知「没有进程在跑，你等的通知不会来」，
并要求改为前台同步执行。**在初始提示词里就禁止用 Monitor 能省掉整轮往返。**

### 6.2 把"跑全量"当成验收的必要条件

有子 Agent 去跑 79987 条的全量 dump（预计 1 小时）、308 个 sitemap 的完整 verify。
这对"证明爬虫正确"毫无必要，纯属烧时间和站点配额。

**处理**：明确口径——抽样对账能证明"翻页不重不漏、total 对得上"就够了，
全量能力保留在 probe 脚本里供上线前最终确认。

## 7. 报告与实际不符时以实测为准

子 Agent 常能挖出调研报告里没有的坑，这些是**高价值产出**，要回流到记忆里。本批实例：
- **dyyjmax**：Flarum 详情页 `<meta name="description">` 会把正文截断，
  产出"腰斩"的分享链接 id。爬虫只扫 API 的 `contentHtml`、不碰整页 HTML 即可绕开。
- **misoso**：`melost.cn` 自己的 robots.txt 指向的是**过期 sitemap**（99 个文件、
  lastmod 停在 2025-03-07），真正在用的是 `misoso.cc` 的 robots.txt 指向的那份（1254 个文件）；
  且越界的 `disk-N.xml` 返回**假 200**（SPA 兜底 HTML）而不是 404。
- **haisou**：上午还能跑通的搜索接口，下午对代理池 IP 全量 429。
  见 `lessons/failure-haisou搜索接口收紧.md`。

## 8. 合并

派一个 version Agent 逐个合并，**每合一个立刻 `go build ./...`**，
通过了再合下一个（出问题能立刻定位到是哪个分支）。冲突一律「全部保留、按字母序排列」。
合完跑 `go build ./...` + `go vet ./services/<新增包>/...` + `go test ./services/...`（不带 `*_IT=1`）。

⚠️ 仓库里有**大量存量的 vet 告警与测试失败**（`services/alipan`、`services/quark`、
`services/gateway/*`、`services/devops/*` 等）。验收新代码只看新增包，
存量问题如实报告但**不要顺手去改**。

删 worktree 和分支前，用 `git merge-base --is-ancestor` 确认提交确实已在 master 上。
**不要 push**，留给用户决定。
