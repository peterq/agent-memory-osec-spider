# 90-review —— 验收判据

你是本轮的验收 Agent。**不要相信开发 Agent 的汇报**，每一条都自己实测复核。
先读 `00-shared.md`、`99-notes.md`、`05-doc-fc-contract.md` 与对应角色文件，再按下面逐项验。

## 0. 一票否决项（命中任意一条，直接判不通过并停下来报告）

1. 主检出 `/home/peterq/dev/projects/1s/osec-spider-go` 有任何被修改的文件
   （`git -C ... status --short` 必须干净）——上面跑着生产守护脚本。
2. 任何仓库里出现明文 AK/SK、口令、token、client_secret（含注释与测试数据）。
   `services/proxy-provider/change_proxy_config.go` 是 gitignore 的凭据文件，
   **必须仍然没有被 git 跟踪**。
3. 提交里包含 `go.mod` / `go.sum` 的 `replace` 路径变更（20-proxy 验证 API 时的临时改动没还原）。
4. NC-JS 里出现了开发 Agent 自己打的提交（约定只能由主控提交）。
5. 任何仓库 `go build ./...` 不过。
6. `cd /home/peterq/dev/projects/1s/nc-js && pnpm -F @nc/spider-admin type-check` 不过。
7. 执行了部署动作（`deploy.sh`、ssh 生产、`pnpm build` 上传 OSS、`ossutil cp`、`s deploy`）。
   检查各仓库 `git log` 与 shell 历史里是否有这类痕迹；`nc-js` 的
   `admin/*/vite.config.ts` 必须没有残留 `deploy: false` 的临时改动。

## 1. 通用复核（每个任务都要做）

- 逐个仓库 `git -C <仓库> log --oneline master..<分支>` 与 `git diff --stat master..<分支>`，
  核对"汇报说改了什么"与"实际改了什么"是否一致，**多改的和少改的都要指出**。
- 新增包 `go vet` 与 `go test` 实跑，贴真实输出。
- 新增配置项检查：是否**每个字段都有内置缺省值**、开关是否用 `*bool`（线上 config.yaml 不分发）。
- 新增的定时/轮询逻辑：网关跑两台机，检查是否判了 `leader.IsLeader()`；
  纯只读查询则不应该判 leader（判了就是多余）。
- proto3 `optional` 的"未设置"语义：前端有没有把"未覆盖"和"覆盖成 0/负数"混为一谈。
- 中文注释与中文 UI 文案是否到位（项目硬性要求）。

## 2. 10-alert 判据

| # | 判据 | 怎么验 |
|---|---|---|
| A1 | 失败率默认值确实改成了 **1h / 60%** | 读 `queue_admin/config.go` 的 `applyAlertDefault`，`FailRateThreshold==0.6`、`FailRateWindowSec==3600` |
| A2 | 失败率统计**不再靠一次性扫 SLS** | 读 `fail_window.go` 与 `metrics.go`：分钟桶按**日志自身时间戳**分桶（不是当前时间）、有 TTL、用 pipeline |
| A3 | 数据不足时**不误报** | 找到 `coveredMinutes == 0` 时 return 的代码路径；`Overview` 此时返回 -1 而不是 0 |
| A4 | per-queue 覆盖能热生效 | 读 `alert_rules.go`：redis hash + 原子快照 + 30s 同步 + `Update` 后立即刷新；各 check 函数确实走 `effectiveRule()` 而不是 `a.conf` |
| A5 | 保留了 preCheck 的更大 backlog 阈值语义 | 读代码确认，并写一个单测覆盖 |
| A6 | 告警历史有持久化且有保留上限 | 读 `alert_history.go`：zset+记录、7 天 TTL、`ZRemRangeByRank` 限 2000 |
| A7 | **每条告警确实附了日志** | 读 `alert_logs.go`：按 rule 选查询、Go 侧按 queueName 二次过滤、failRate 优先取失败日志、SLS 不可用只写 `logsError` 不阻断告警 |
| A8 | 邮件正文带日志片段 | 读 `fire()` 的 body 组装 |
| A9 | `metricsJson` 里有阈值+实际值+窗口 | 读代码 |
| A10 | 前端不再有硬编码阈值 | `grep -n "0.5\|>= 20\|5000" admin/spiderAdmin/src/pages/queue/OverviewPage.tsx` 应查不到阈值常量；拉配置失败时**不高亮**而不是报错阻塞 |
| A11 | 前端 mock 分支实际被跑过 | 打开 mock 开关看三条告警记录：抓日志成功/`logsError` 非空/`notified=false`，UI 都要有正确表现 |

## 3. 20-proxy 判据

| # | 判据 | 怎么验 |
|---|---|---|
| P1 | **proxy-client 与上报解耦** | `grep -rn "import" illuminate/proxy-client/` 不得出现 prometheus / redis / config / proxy-monitor；依赖方向只能 monitor→client |
| P2 | 埋点没改变原有行为 | `git diff master..feat/proxy-monitor -- illuminate/proxy-client/proxy-client.go` 逐行看：`KillProxy`/`BlockProxy`/重试次数/goto DO 的控制流必须与原来等价 |
| P3 | hook 不会拖垮请求 | 读代码：hook 调用有 recover、上报走非阻塞 channel、满了丢弃并计数 |
| P4 | **失败分类真的区分了两类** | 读 `classify.go`：超时/连接类 → `ipUnusable`；429/403/业务码 → `siteBlocked`。抽查 quark/alipan/xunlei/valid/haisou 是否给了 `ClassifyResult` |
| P5 | 22 个实例化点都填了 `Scene` | `grep -rn "proxy_client.ProxyClient{" --include=*.go` 逐个核对有没有 `Scene:`，漏的列出来 |
| P6 | 供给侧推送量与去重 IP 有数 | 读 `proxy-provider.go` 的 `RecordPublish` 调用；redis 用 HLL(`PFADD`/`PFCOUNT`) |
| P7 | 分位数算法对 | 找到直方图插值实现，核对是标准累积桶线性插值；**必须有单测**，自己再手算一组验证 |
| P8 | 24h 窗口有缓存 | 读 `proxy_admin`：1440 个 key 的聚合是否做了 60s 缓存 |
| P9 | 无数据返回 -1 而不是 0 | 读代码 + 前端显示为 `—` |
| P10 | API 仓库能编译 | 按 `99-notes.md` §3 的临时 replace 法实跑 `go build ./...`，跑完确认 go.mod 已还原 |
| P11 | 前端 5 秒自动刷新且页签不可见时停 | 读 `ProxyOverviewPage.tsx` |

## 4. 30-trace 判据

| # | 判据 | 怎么验 |
|---|---|---|
| T1 | 埋点只加日志、不改控制流 | 逐个 diff 每个被改的业务文件 |
| T2 | **重复提交分支现在会打日志** | 读 `spider-common.go`，确认 `ErrDupTask` 也有日志且 level 是 Info |
| T3 | bnd 两个消费者补上了日志 | 读 `bnd_load_share.go` / `bnd_input_pwd.go`，字段与 quark 版对齐；`bndInputPwd` 二次推入队列那步单独有日志 |
| T4 | 入库结果进了 SLS | 读 `resource/big-res.go` 与 `resource/baidu.go`，确认用的是 `logger.Logger` 而不是 std `log`/`logrus` |
| T5 | `link_key` 在每个阶段都补齐、且下游队列名能正确反推类型 | 读代码，特别检查 `keywordSubscribed:seed.pansearch.me` 这种带点的队列名不会被截断 |
| T6 | Go 侧对 SLS 全文命中做了二次校验 | 读 `trace.go`，防止分词误命中 |
| T7 | 5 个单测场景都真在跑且断言到位 | `go test -run Trace -v ./services/gateway/queue_admin/...`，看每个场景断言了 events 顺序/outcome/errorMessage/verdict |
| T8 | **未埋点阶段与"没发生"被区分开** | 读 `TraceStageSummary.instrumented` 的赋值逻辑 + 前端灰显与 tooltip |
| T9 | `AuditLogs` 存量 bug 已修 | 读 `logs.go`，`service` 改成 `spider-gateway and type:queue-admin` 且注释写明原因 |
| T10 | 前端时间轴把错误消息显示出来了 | 读 `TracePage.tsx`；开 mock 实际看一眼 |

## 5. 40-fcchrome / 41-doccrawler 判据

| # | 判据 | 怎么验 |
|---|---|---|
| F1 | `fc-chrome` 是**独立嵌套 module** | 有自己的 `go.mod`；COMMON 根 `go build ./...` 仍通过且根 `go.mod` 无新依赖 |
| F2 | 换成了 `--headless=new` 且去掉了 `--disable-extensions` | 读启动参数代码 |
| F3 | 下载有域名白名单、FC 内走内网、解包防 zip-slip、crx2/crx3 头都处理 | 逐条读代码 |
| F4 | 失败在 WS 握手前以 HTTP 错误返回 | 读 `/chrome` handler |
| F5 | Tampermonkey 缺包时**构建只警告不失败** | 读 Dockerfile |
| F6 | CDP 主世界注入这条兜底路径**本地真跑过** | 看汇报里的 console 输出证据；自己复跑一次 |
| F7 | 云端油猴脚本无 nonce 时不干扰人工使用 | 读脚本入口逻辑 |
| F8 | cdp-driver endpoint 改成环境变量可配、缺省仍是旧域名、没写死不存在的新域名 | 读 `apps/cdp-driver/src/main.ts` |
| F9 | doc-crawler **每个任务都有终态** | 读代码：defer + recover 保证一定调 `TaskDone`，`TaskDone` 失败重试 3 次 |
| F10 | 保活 5 秒一次且所有退出路径都停 | 读代码 |
| F11 | 版本未变跳过提交但仍 `TaskDone` | 读代码 + 单测 |
| F12 | 优雅退出：SIGTERM 后不再 Pop、等在跑的做完 | 读代码 |
| F13 | 端到端桩测试真跑过 | 自己复跑一次，贴输出 |
| F14 | 没有改 `services/gateway/doc_scheduler/` | `git diff --stat master..feat/doc-crawler -- services/gateway/doc_scheduler/` 必须为空 |

## 6. 输出格式

按任务分节，每节给：
- **结论**：通过 / 有条件通过（列出必须修的项）/ 不通过
- 逐条判据的实测结果（命令 + 关键输出）
- 你自己新发现的问题（开发 Agent 没报告的），按「阻塞 / 重要 / 建议」分级
- 汇报与实际不符的地方，逐条点名

---

## 7. 【主控 2026-09-08 补充】五个分支已合并，改在合并后的主干上验收

全部分支已 `git merge --no-ff` 进各仓库主干（**均未 push**）。判据里写的
`git diff master..<分支>` 请改成对基线提交做 diff：

| 仓库 | 路径 | 基线提交 | 合并后 HEAD 位置 |
|---|---|---|---|
| SPIDER | `/home/peterq/dev/projects/1s/osec-spider-go` | `c34ac3c` | `master`（4 个 merge commit） |
| COMMON | `/home/peterq/dev/projects/1s/enfi-resource-common` | `255ecfe` | `master`（Phase 0 契约 + `fc-chrome/`） |
| NC-JS | `/home/peterq/dev/projects/1s/nc-js` | `7fb3721` | `main`（Phase 0 + 4 个角色各一个提交，由主控代提交） |
| API | `/home/peterq/dev/projects/1s/osec-resource-api` | `d0e2bb7` | `master` |
| userscripts | `/home/peterq/dev/projects/peterq/userscripts` | `56eecf3` | `master`（**该仓库另有用户自己的未提交改动，不要碰**） |

例：`git -C /home/peterq/dev/projects/1s/osec-spider-go diff c34ac3c..master --stat`

一票否决项第 1 条（SPIDER 主检出必须干净）现在改成：**`git status --short` 必须干净**
（合并后工作区应无未提交改动）；主检出仍然跑着生产守护脚本 `scripts/lc_adaptive_rps.sh`
（PID 1664230），**验收全程只读，不要写任何文件、不要切分支、不要 `git reset/checkout`**。
需要跑测试就在主检出跑 `go test`（只读，安全），或者用各角色的 worktree
（`../spider-wt-*`，分支仍在，内容与合并结果一致）。

一票否决项第 4 条（NC-JS 不许有开发 Agent 的提交）已由主控代为提交，作废。

合并后主控已实测：SPIDER `go build ./...` 通过、四个新包 `go vet` 干净、
`go test` 四包全过；COMMON / API `go build ./...` 通过；
NC-JS `pnpm -F @nc/spider-admin type-check` 通过。**这些你要自己复跑一遍确认。**

### 各角色的实际提交

| 角色 | 提交 |
|---|---|
| 41-doccrawler | SPIDER `5d1389b` |
| 10-alert | SPIDER `185e4b6` + NC-JS `80caebc` |
| 30-trace | SPIDER `686c0a0` + NC-JS `6b1d5bc` |
| 20-proxy | SPIDER `f6ccd58`+`81f13f1`、API `22f514f`、NC-JS `7f910e8` |
| 40-fcchrome | COMMON `dadf6f2`、userscripts `f223b11`、NC-JS `ab7753d` |

### 开发 Agent 自报的偏离与遗留（**逐条核实是否属实、是否可接受**）

1. **10-alert**：越界改了 `QueueMonitorContext.ts`（加了一个 `alertRules` 字段）——核实是否只是加字段、
   有无影响其它页面。
2. **10-alert**：`AlertRulesResponse.global.backlogThreshold` 只暴露通用队列缺省(2000)，
   没暴露 `resourcePreCheck` 专用缺省(5000)，导致总览页对 preCheck 队列在无覆盖时会偏早标红。
   核实影响面，判断是否值得加 proto 字段。
3. **20-proxy**：实际改了 **29** 个 `ProxyClient{}` 实例化点（简报里写的 22 是估数）——
   自己 grep 一遍确认**没有漏网的**。
4. **20-proxy**：只给 haisou 加了 `ClassifyResult`，quark/alipan/xunlei/valid 依赖默认的 429/403 分类。
   核实 `quark_checker.go` 的 `isRateLimited()`（空 body/非 JSON 也算限流）这个精度差异会不会
   让"被站点封禁"被系统性低估。
5. **20-proxy**：`total` 汇总行的 `distinctProxyIp`/`hosts` 恒为空；`ProxySceneSeries` 无缓存
   （24h@60s 会打出 5700+ 条 redis 命令）。评估严重性。
6. **20-proxy**：`proxyAdminRpc` 无 mock，两个前端页面从未跑过真实数据分支。
7. **30-trace**：`crawl` 桶查询加了 `stage:input-pwd*`（对文档的合理修正）。
8. **30-trace**、**10-alert**：都没有联网验证真实 SLS 查询效果（无生产凭据），
   只有假数据单测。核实单测是否真的覆盖了关键分支。
9. **40-fcchrome**：Tampermonkey 安装路径 1 未实现、路径 2 未验证（选择器全靠猜），
   只有 CDP 主世界注入这条本地验证过。核实 doc-crawler 缺省是否确实走已验证的那条。
10. **41-doccrawler**：未新增 `GatewayAddr` 配置项，改用 `config.MustSpiderGwConn("doc_crawler")`
    ——核实这与其它消费者进程写法一致。
11. 所有角色都没做真实浏览器/真实生产验证，前端只过了 `vue-tsc`。
