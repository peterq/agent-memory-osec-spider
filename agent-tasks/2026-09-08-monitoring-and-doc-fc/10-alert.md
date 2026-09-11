# 10-alert —— 告警加入后台（附现场日志）+ 队列失败率告警按队列可配

先读 `00-shared.md`，再读本文件。你是本任务的**全栈开发**（COMMON 契约已就绪 → SPIDER 后端 → NC-JS 前端）。

## 用户原话

> 告警加入后台, 附上日志
> 队列失败率告警调整, 支持按队列配置, 默认值调整: 10min/50% -> 1h/60%.

## 目标拆解

1. **告警历史落库 + 后台可查**：现在告警只发邮件 + 打一条日志，redis 里只有 1 小时去抖 key，
   后台完全看不到。要能在管理后台看到"什么时候、哪条规则、哪个队列、为什么触发"。
2. **每条告警附上触发时的现场日志**：从 SLS 抓相关日志片段，随告警记录一起存下来，
   后台能直接看到，邮件正文里也要带上。
3. **失败率告警按队列可配**：窗口与阈值都能按队列单独设置，后台可改、热生效。
4. **默认值调整**：窗口 10min → **1h**；阈值 50% → **60%**。

## 必读文件（说明要提取什么）

| 文件 | 为什么读 |
|---|---|
| `SPIDER services/gateway/queue_admin/alert.go` | 告警引擎全貌：`run()` 60s 轮询、6 条规则、`sustain()` 内存态、`fire()` 去抖+邮件。你要改的核心 |
| `SPIDER services/gateway/queue_admin/overview.go:62-96` | `finishFailMap10m()`——失败率数据源，10 分钟窗口硬编码在 `:67`，扫描上限 `finishFailScanLimit=1000` |
| `SPIDER services/gateway/queue_admin/metrics.go:145-209` | `pollSlsCounters()`——已经每 60s 增量扫 `finishQueuedTask` 日志，**你要在这里顺带写分钟桶** |
| `SPIDER services/gateway/queue_admin/config.go:59-93` | `applyAlertDefault()`——所有告警缺省值，改默认值的地方 |
| `SPIDER config/config.go:343-363` | `QueueAdminAlertConfig` 结构体，新增 yaml 字段的地方 |
| `SPIDER services/gateway/lifecycle/params.go` | **必抄范式**：redis hash + `atomic.Pointer` 原子快照 + 30s 后台同步 + `Update()` 校验与审计 |
| `SPIDER services/gateway/queue_admin/{audit.go,errors.go,logs.go,sls.go,registry.go}` | 审计写法、错误码约定、SLS 查询封装、队列名枚举 `allQueueNames()` |
| `NC-JS admin/spiderAdmin/src/pages/queue/OverviewPage.tsx:12-32` | 前端**另有一份硬编码阈值副本**（waiting/aging/failRate），必须改成从后端拉 |
| `NC-JS admin/spiderAdmin/src/pages/lifecycle/ParamsPage.tsx` | 配置编辑页范式 |
| `NC-JS admin/spiderAdmin/src/pages/queue/LogSearchPage.tsx` | 日志表格渲染与 `gotoLogSearch` 跳转范式 |

## 契约（主控已写好并生成，直接用）

`COMMON rpc/spider/queue_admin_rpc/queue_admin.proto` 已追加：

```
rpc ListAlerts(ListAlertsParam) returns (ListAlertsResponse);
rpc GetAlertRules(common.Empty) returns (AlertRulesResponse);
rpc UpdateAlertRule(UpdateAlertRuleParam) returns (common.Empty);
rpc DeleteAlertRule(DeleteAlertRuleParam) returns (common.Empty);
```
消息：`AlertRecord`（含 `repeated LogEntry logs`、`logsQuery`、`logsError`、`metricsJson`、`host`）、
`AlertRulesResponse`、`QueueAlertRuleOverride`、`AlertRuleConfig`（全部字段是 proto3 `optional`，
未设置 = 沿用全局）、`UpdateAlertRuleParam`、`DeleteAlertRuleParam`。
生成代码已在 `queue_admin.pb.go` / `queue_admin_grpc.pb.go` 里，**不要重新生成除非你改了 proto**。

## 后端实现要点（SPIDER `services/gateway/queue_admin/`）

### A. 失败率统计：从"现查 SLS"改为"redis 分钟桶"

**为什么必须改**：现在 `finishFailMap10m` 一次 `GetLogs` 扫最多 1000 条来算 10 分钟失败率，
窗口拉到 1 小时后一定扫不全（SLS `search` 的 limit 被硬夹到 ≤200，`countByQuery` 也只是近似），
结果会系统性偏低且不可信。

做法（新建 `fail_window.go`）：

- `pollSlsCounters()` 里已经每 60s 增量拉一次 `finishQueuedTask` 日志（limit 2000）。
  在它遍历日志、`metricFinishTotal.Inc()` 的同一个循环里，**顺带累加到本地 map，然后一次
  `HIncrBy` 写进 redis 分钟桶**：
  - key：`queueAdmin:finishWin:<minuteEpoch>`（minuteEpoch = 日志时间戳所在分钟的 unix 秒 / 60）
  - field：`<queueName>:finish` / `<queueName>:fail`（fail 的判据沿用现有的 `!d.Success`）
  - TTL：26 小时（`Expire` 每次写都刷新即可）
  - 用 pipeline 批量写，避免逐条往返
  - **按日志自身时间戳分桶**，不要按当前时间，否则跨轮次会串桶
- 提供 `finishFailInWindow(queueName string, windowSec int64) (finish, fail int64, coveredMinutes int, err error)`：
  读最近 `windowSec/60` 个分钟桶（`HMGet` 或 pipeline `HGet`）求和，`coveredMinutes` = 实际有数据的桶数。
- `Overview` 的 `finish10m/fail10m` 也改读桶（窗口固定 600s，字段名与语义不变）。
  桶完全没数据（`coveredMinutes == 0`）时按 proto 注释返回 **-1**（表示不可用），
  不要回落成 0（0 会被前端当成"真的没有任务"）。
- 告警判定同理：`coveredMinutes == 0` 时直接 return，不触发告警（**宁可漏报不可误报**）。
- 保留 `finishFailScanLimit` 相关旧代码路径不再使用的部分要删干净，别留死代码。

⚠️ `pollSlsCounters` 与 `alert.run()` 都是 leader-only（`IsLeader()`），写桶的只有 leader，
读桶的也是 leader，leader 切换后桶数据在 redis 里仍然连续 —— 这正是用 redis 而不是内存的原因。

### B. per-queue 告警配置（redis hash + 热同步 + 审计）

新建 `alert_rules.go`，**照抄 `services/gateway/lifecycle/params.go` 的结构**：

- redis hash key：`queueAdmin:alertRules`，field = 队列名，value = 覆盖项 JSON
- `atomic.Pointer[rulesSnapshot]` 原子快照 + 后台 goroutine 每 **30s** 同步一次（常量导出给
  `GetAlertRules` 的 `syncIntervalSec` 字段用）
- `effectiveRule(queueName) resolvedRule`：全局值（`applyAlertDefault` 后的 conf）+ 该队列覆盖项合并
- `alertEngine` 的 `checkBacklog/checkAging/checkStalled/checkFailRate` 全部改成从
  `effectiveRule(queueName)` 取值，**不要再直接读 `a.conf`**。
  注意保留现有的"`backlog` 对 `resourcePreCheck` 用另一个更大阈值"语义：把它落成
  **全局层的默认值选择**（preCheck 用 `BacklogThresholdPreCheck`，其余用 `BacklogThresholdDefault`），
  队列覆盖优先级更高。
- 负数 = 关闭该规则（沿用现有约定），校验时允许负数
- `UpdateAlertRule`/`DeleteAlertRule` 必须：校验 `queueName`（用 `registry.go` 的 `checkQueueName`）、
  校验取值范围（`failRateThreshold` 在 `[-1, 1]`，`failRateWindowSec` 在 `[60, 86400]` 且是 60 的整数倍，
  `failRateMinFinish >= 0`）、写 redis、**写审计**（`audit.go`）、并立即刷新本地快照（不用等 30s）
- `GetAlertRules` 返回：`global`（全部字段都填上生效值）、`overrides`（按队列名排序）、
  `knownQueues`（`svc.reg.allQueueNames()`）、`syncIntervalSec`

### C. 默认值调整

- `config/config.go` 的 `QueueAdminAlertConfig` **新增** `FailRateWindowSec int64 \`yaml:"fail_rate_window_sec"\``
  （注释：失败率统计窗口秒，缺省 3600）
- `queue_admin/config.go` 的 `applyAlertDefault`：
  - `FailRateThreshold` 缺省 **0.6**（原 0.5）
  - `FailRateWindowSec` 缺省 **3600**
  - 其余不动
- 在 `applyAlertDefault` 上方注释里写明"2026-09-08 按用户要求由 10min/50% 调整为 1h/60%"

### D. 告警历史 + 现场日志

新建 `alert_history.go`：

- 存储（redis，**不要引入 MySQL**）：
  - 索引 zset：`queueAdmin:alertHistory` — score = `firedAtMs`，member = 记录 id
  - 记录：`queueAdmin:alertRecord:<id>` — 记录 JSON 字符串，TTL 7 天
  - id 生成：`fmt.Sprintf("%d-%s", firedAtMs, shortHash(rule+":"+target))`，可读且唯一
  - 每次写入后做保留清理：`ZRemRangeByScore` 删掉 7 天前的，再 `ZRemRangeByRank` 只保留最近 2000 条
- `fire()` 改造（保持现有的 SetNX 去抖语义与顺序不变）：
  1. 去抖通过后，先**抓现场日志**（下面 E 节），
  2. 组装 `AlertRecord`（含 `metricsJson` —— 触发瞬间的阈值/实际值/窗口，务必带上，
     这是事后复盘最有用的东西），
  3. 写 redis 历史，
  4. 打结构化 Warn 日志（保持现有），
  5. 发邮件（正文里附上日志片段），发送结果回写 `notified`/`notifyError` 到记录里。
  即使写历史失败也不能影响发邮件，反之亦然（各自 recover/记错误日志）。
- `ListAlerts` 实现：`ZRevRangeByScore` 取 `[fromMs, toMs]` 内最多 2000 个 id → 批量 `MGet` 记录 →
  按 `rule`/`target` 过滤 → `total` = 过滤后条数 → 按 `offset/limit` 切片（limit 缺省 50、上限 200）。
  时间参数缺省：`toMs` 为 0 时取 now，`fromMs` 为 0 时取 `toMs - 24h`。

### E. 抓现场日志（"附上日志"的核心）

新建 `alert_logs.go`，函数 `collectAlertLogs(rule, target string, firedAt time.Time) (logs []LogEntry, query string, truncated bool, err error)`：

- 时间窗：`[firedAt-10min, firedAt]`
- 按规则选查询语句与过滤方式：
  | rule | SLS 查询 | Go 侧二次过滤 |
  |---|---|---|
  | `failRate` | `buildStageQuery("spider-gateway","resScheduler","finishQueuedTask","")` | `data.queueName == target` **且优先保留 `success=false` 的**（先取失败的，不足再补成功的） |
  | `backlog` / `aging` / `stalled` | 同上 | `data.queueName == target` |
  | `kwSiteMissing` | `buildStageQuery("spider-gateway","resScheduler","pushKwTask","")` | 内容含 target 站点名 |
  | `selfPollError` | `service:spider-queue_admin and type:queue-admin` | level 为 ERROR/WARN |
- 每次最多向 SLS 要 200 条（上限就是 200），Go 侧过滤后**最多保留 50 条**存进记录，
  `truncated` 标记是否被截断；`logsQuery` 存下拼好的查询语句，前端可一键跳日志搜索页。
- SLS 未配置或查询报错：**不要让告警失败**，把原因写进 `logsError` 即可。
- 邮件正文：在原有 detail 后面追加 `<pre>` 块，附**最多 20 条**日志（时间 + stage + content 截断到 300 字），
  超出部分写"…还有 N 条，见后台告警页"。

### F. 注册

`register.go` 里 `QueueAdminRpc` 的 4 个新方法要能被调用（`Service` 实现全部方法即可，
service 注册代码不用改）。启动 `alertRules` 的同步 goroutine（放在 `svc.alert.Start()` 附近，
**同步 goroutine 不需要 leader 判断**——读配置两台机都要读；只有"写桶/发告警"才 leader-only）。

## 前端实现要点（NC-JS `admin/spiderAdmin`）

1. TS 契约、菜单项、插槽、mock **主控已在 Phase 0 做好**（见 `00-shared.md` §3），不要重做。
   你只需要**替换两个占位页面的内容**。
2. 替换 `src/pages/queue/AlertHistoryPage.tsx`（已存在占位，props 已有 `isShow: boolean`）：
   - 顶部：时间范围 `RangePicker`（缺省最近 24h）+ 规则下拉 + 目标输入 + 刷新
   - 表格列：触发时间 / 规则 / 目标 / 主题 / 是否已通知 / 操作(查看详情)
   - 详情抽屉：detail 全文、`metricsJson`（用 `JsonTree.tsx` 渲染）、**现场日志表格**
     （抄 `LogSearchPage.tsx` 的列定义）、`logsError` 有值时用 `Alert` 提示、
     一个「在日志搜索页打开」按钮（调 ctx 的 `gotoLogSearch(logsQuery)`）
   - 自动刷新：沿用 `useDocumentVisibility() + useTimeoutToRef(10e3)` 套路
3. 替换 `src/pages/queue/AlertRulesPage.tsx`（已存在占位，无 props）：
   - 上半：全局生效值只读展示（描述列表），并注明"改这些要改网关 yaml 并重启"
   - 下半：按队列覆盖的表格 + 新增/编辑弹窗（抄 `ParamsPage.tsx` 与 `modals/ModalConfItem.tsx`）；
     每个字段一个"是否覆盖"开关，关掉即不下发该字段（对应 proto3 optional 的"未设置"）
   - 顶部提示：`syncIntervalSec` 秒内生效
4. `src/pages/queue/OverviewPage.tsx:12-32`：删掉硬编码阈值，改为在 `QueueCtxProvider` 里
   拉一次 `getAlertRules()` 并 provide，卡片高亮按"该队列的生效阈值"判定。
   拉取失败时**回落到不高亮**，不要因为拿不到配置就报错阻塞总览页。

## 交付

在下列分支上提交（分支不存在就从当前主干建）：

- COMMON：`feat/alert-admin`（主控已改 proto，**你若未再改 proto 就不用在 COMMON 提交**）
- SPIDER：`feat/alert-admin`
- NC-JS：`feat/alert-admin`

汇报格式：
1. 改动文件清单（按仓库分组）
2. 每条验证命令 + 真实输出结论（`go build ./...`、`go vet ./services/gateway/queue_admin/...`、
   `go test ./services/gateway/queue_admin/...`、两个 `type-check`）
3. **失败率窗口从"现查 SLS"改成"redis 分钟桶"后，首次上线的 1 小时内数据是不全的**——
   请在汇报里明确说明你是怎么处理"数据不足"的
4. 没做完的部分 / 需要人工提供的信息
