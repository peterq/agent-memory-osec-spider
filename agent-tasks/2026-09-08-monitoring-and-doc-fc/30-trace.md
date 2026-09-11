# 30-trace —— 资源链接爬取路径追踪

先读 `00-shared.md`，再读本文件。你是本任务的**全栈开发**（SPIDER 埋点补齐 + 网关 RPC + NC-JS 页面）。

## 用户原话

> 资源链接爬取路径追踪, sls 客户端查日志构建, 从来源提交, 到爬取/重试入库的时间线,
> 有错误的显示错误消息

## 目标

后台里输入一条分享链接（或分享 id），一次查出它在全链路的完整时间线：
谁发现并提交的 → 网关预检怎么判的 → 分发到哪个队列 → 消费端爬详情成功还是失败 →
入库结果 → 有没有重试/超时重推 → 最终结论。**每一步有错就把错误消息显示出来。**

## 现状（已调研，不用重查）

### 链路与现有日志锚点

| # | service | type | stage | 标识字段 | 文件:行 |
|---|---|---|---|---|---|
| 1 | `spider-<爬虫>` | `res-link-committer` | `commit-res-link` | `data.link.Url`（**原始 URL**） | `services/spider-common/spider-common.go:62-87` |
| 2 | `spider-gateway` | `spider-gateway` | `rpc/...PushQueuedTasks` | `data.input` 里有完整 payload | `services/gateway/gateway.go:298-312`（拦截器） |
| 3 | `spider-gateway` | `resScheduler` | `preCheck.handle` | `data.task.key`=`<typ>:<id>`、`data.target` | `services/gateway/res_scheduler/pre_check.go:71-135` |
| 4 | `spider-gateway` | `resScheduler` | `finishQueuedTask` | `data.{queueName,taskKey,success,reason,isPermanentFail}` | `res_scheduler.go:223-255` |
| 5 | `spider-v2*LoadShare` | `queueRemoteConsumer:<queue>` | `onSuccess.submitResult` / `onFail.submitResult` | `data.task.key`、`data.task.payload.url` | `illuminate/queue-task/queue_consumer_remote.go:84-95` |
| 6 | `spider-v2*LoadShare` | `<pan>-load-share-v2` | `load-share.*` / `handle.*` | ali=`data.id`，quark=`data.shareId`+`data.taskKey`，xl=`data.shareId`+`data.url`，**bnd 无任何日志** | `services/v2/res_crawler/{ali,quark,xl,bnd}/` |
| 7 | `spider-gateway` | `resScheduler` | `handleTimeout.<q>.rePush` / `.removeTask` | `data.{key,seq,retry,payload}` | `res_scheduler.go:338-376` |

### 已知断点（必须处理）

1. **预检队列 key 带类型前缀 `<typ>:<id>`，下游队列 key 只有 `<id>`**（`pre_check.go:118`）——
   同一条链接两个 key。
2. **URL 在预检里被规范化改写**（`pre_check.go:84` `ShareLinkFromId`）——按原始 URL 全文搜会漏。
3. **`CommitResLink` 遇到重复任务（`ErrDupTask`）完全不打日志**（`spider-common.go:64` 的 defer 里
   显式跳过）——"这条链接为什么没有后续"最常见的答案就是它。
4. **bnd 两个消费者零日志**（`bnd_load_share.go`、`bnd_input_pwd.go`，只有被注释掉的 `log.Println`）。
5. **入库结果只走 std `log.Println`，不进 SLS**（`resource/big-res.go:253,350`；`resource/baidu.go:38`
   用 `logrus.Warn`）。
6. **ali 消费者缺"入库成功"日志**（quark `:170`、xl `:200` 有）。
7. STORAGE 仓库完全没有 SLS —— **本轮不改 STORAGE**，入库结果从 SPIDER 侧
   （`SaveResource`/`SaveBigResource` 拿到的 `resp.Canceled/CancelReason`）记录即可。
8. `queue_admin/logs.go:24,46` 的 `SearchLogs` **硬编码只查 `service:spider-gateway`** ——
   追踪必须跨 service 查，不能复用它。
9. **SLS 没有对 `data` 内嵌 JSON 做二次索引**（`sls.go:75-80` 有注释说明）——
   按 `data.xxx` 精确过滤只能拉回来在 Go 侧逐条 parse。

### 存量 Bug（顺手修，改动很小）

`queue_admin/logs.go:32` 的 `auditLogServiceName = "spider-queue_admin"`：queue_admin 已于
2026-09-04 并入网关进程，审计日志实际写入的 `service` 是 `spider-gateway`，导致 `AuditLogs`
线上永远查不到记录。改成查 `service:spider-gateway and type:queue-admin`，并在注释里写明原因。

## 实现方案

### Part 1：补齐埋点（低侵入，只加日志，不动业务逻辑）

统一约定：**每条链路日志都用 `WithField("link_key", "<typ>:<id>")` 打一个顶层字段**
（`WithField` 会平铺成 SLS 顶层字段，见 `pan/common/utils/logger/ali-log.go:109-115`；
与内置字段撞名才会加 `app_` 前缀，`link_key` 不撞）。这样等 SLS 控制台给 `link_key` 建了索引，
就能从"全文检索"升级成"精确字段查询"。

| 位置 | 要加什么 |
|---|---|
| `services/spider-common/spider-common.go:62-87` | ① 加 `link_key` 顶层字段；② **重复提交分支也要打日志**（`Info("duplicate")`，level 用 Info 不要 Error），把现在 `defer` 里那个 `if !errors.Is(retE, resource.ErrDupTask)` 改成两个分支都打、内容不同 |
| `services/gateway/res_scheduler/pre_check.go` | 各日志点加 `link_key`（它已经有完整 task，直接 `task.Key`） |
| `services/gateway/res_scheduler/res_scheduler.go:223-255, 338-376` | `finishQueuedTask` / `handleTimeout.*` 加 `link_key`。注意下游队列的 taskKey 没有类型前缀，要按 `queueName` 反推类型补全（`bndLoadShare`/`bndInputPwd`→`bnd`，`aliLoadShare`→`ali-share`，`quarkLoadShare`→`quark`，`xlLoadShare`→`xunleipan`，`resourcePreCheck` 已带前缀） |
| `illuminate/queue-task/queue_consumer_remote.go:84-95` | 加 `link_key`（从 `task.Key` + 队列名推） |
| `services/v2/res_crawler/bnd/bnd_load_share.go` | **新增日志**：开始/成功/永久失败/失败/入库结果，字段与 quark 版对齐（`shareId`/`taskKey`/`link_key`），用 `logger.Logger("bnd-load-share-v2")` |
| `services/v2/res_crawler/bnd/bnd_input_pwd.go` | 同上，logger 名 `bnd-input-pwd-v2`；**二次推入 `bndLoadShare` 那一步要单独打一条**（`bnd_input_pwd.go:86-98`），否则时间线里会出现"同一 key 出现两次"却看不出原因 |
| `services/v2/res_crawler/ali/ali_load_share.go:135` | 补一条"入库成功"日志（stage `load-share.save-resource`），与 xl `:200` 对齐 |
| `resource/big-res.go:219-352` | `SaveResource`/`SaveBigResource` 里的 `log.Println` 改成 `logger.Logger("res-save")` 的结构化日志，stage `save-resource` / `save-big-resource`，data 带 `{url, resId, canceled, cancelReason, fileCount, size}`，**并加 `link_key`**。保留原有 std log 也行，但 SLS 里必须有 |
| `resource/baidu.go:33-61` | `SaveBaiduResource` 的 `logrus.Warn(err)` 改成同样的结构化日志（成功也打） |

⚠️ 埋点只加日志，**不要改任何控制流、重试次数、错误返回**。
⚠️ 日志量：`SaveResource` 是高频路径，成功日志用 `Info` 即可，不要打 `data` 里的完整文件列表。

### Part 2：网关侧 `TraceResLink` 实现

落点：`services/gateway/queue_admin/trace.go`（复用 queue_admin 已有的 `slsClient` 与 leader 无关的只读路径）。

契约已在 `COMMON rpc/spider/queue_admin_rpc/queue_admin.proto` 里生成好：
`TraceResLinkParam` / `TraceResLinkResponse` / `TraceIdentity` / `TraceEvent` / `TraceStageSummary`。

步骤：

1. **解析输入 → `TraceIdentity`**：
   - 输入可能是完整 URL、`<typ>:<id>`、或裸分享 id
   - URL：用 `spider_contract.ParseShareLink`；`<typ>:<id>`：直接拆；裸 id：无法判类型，
     此时 `linkType` 留空并对所有类型都试（用裸 id 做全文检索即可）
   - `canonicalUrl` = `spider_contract.ShareLinkFromId(typ,id)`；`resId` = `resource.Md5bin([]byte(canonicalUrl))`
   - 解析不出来时 `parseError` 写清楚原因，仍然用原始输入做一次全文检索（用户可能贴了别的东西）
2. **并发跑多条 SLS 查询**（`errgroup`，每条独立超时 10s，单条失败只进 `warnings` 不整体失败）：

   | 阶段 | query |
   |---|---|
   | commit | `type:res-link-committer and <term>` |
   | preCheck | `service:spider-gateway and type:resScheduler and stage:preCheck.handle and <term>` |
   | finish | `service:spider-gateway and type:resScheduler and stage:finishQueuedTask and <term>` |
   | timeout | `service:spider-gateway and type:resScheduler and stage:handleTimeout* and <term>` |
   | consume | `type:queueRemoteConsumer* and <term>` |
   | crawl | `stage:load-share* or stage:handle*`（再拼 `and <term>`） |
   | save | `type:res-save and <term>` |
   | rpc（可选，`includeRpcLogs=true` 才查） | `service:spider-gateway and stage:rpc* and <term>` |

   `<term>` 的构造：
   - 缺省用 **全文检索**：`"<shareId>"`（加引号，SLS 短语检索）。
     分享 id 是字母数字串，是当前唯一能跨所有阶段命中的方式。
   - 若配置项 `services.queue_admin.sls.link_key_indexed = true`（新增，**缺省 false**），
     改用 `link_key:"<typ>:<id>"` 精确查询。在 `TraceResLinkResponse.warnings` 里说明当前用的是哪种模式。
   - 每条查询 limit 用 `limitPerStage`（缺省 50，上限 200）。

3. **Go 侧二次校验**：把每条日志的 `content`+`dataJson` 再匹配一次分享 id（防止 SLS 全文分词
   误命中别的日志）。命中不了的丢弃。
4. **翻译成 `TraceEvent`**：`phase` / `phaseLabel`（中文）/ `summary`（中文一句话）/ `outcome` / `errorMessage`。
   - 错误消息来源优先级：`data.reason` > `data.failMsg` > `content`（level 为 error 时）> `error_stack` 首行
   - `summary` 举例：
     - `commit` + ok → `"爬虫 bbs_kuakes 提交了链接"`
     - `commit` + duplicate → `"链接重复提交, 已被去重丢弃"`
     - `preCheck` + `dispatched` → `"预检通过, 分发到队列 quarkLoadShare"`
     - `preCheck` + `repeat task` → `"6 小时内已处理过同一链接(去重键命中), 直接结束"`
     - `finish` + success=false + isPermanentFail=true → `"消费端上报永久失败: <reason>"`
     - `handleTimeout.*.rePush` → `"消费端保活超时(61 秒), 第 N 次重推"`
     - `save-resource` + canceled → `"入库被跳过: <cancelReason>"`
5. **`stages` 汇总**：每个阶段的条数、首末时间、结论；**`instrumented=false` 的阶段要显式标出**
   （例如 SLS 里查不到 `res-save` 是因为该版本还没上线埋点，而不是"没入库"）。
   给 `note` 写清楚，这是避免误判的关键。
6. **`verdict`**：按最后一个有意义的事件给出中文结论。至少覆盖：已入库 / 被去重丢弃 /
   不支持的链接类型 / 消费端永久失败 / 仍在队列中 / 超过重试上限被丢弃 / 查无记录（可能超出 SLS 保留期）。
7. **`truncated`**：任一阶段命中数达到 limit 就置 true。
8. 时间窗缺省最近 7 天；SLS 未配置时返回 `ErrSlsUnavailable`（`errors.go` 已有 110506）。

**测试要求**：SLS 需要生产凭据，**本轮无法联网验证**。必须写单测：
把 `slsClient` 抽成接口（或给 `Service` 加一个可替换的查询函数字段），用假数据构造
"完整成功链路 / 重复丢弃 / 消费端永久失败 / 超时重推三次后丢弃 / bnd 走 inputPwd 二段" 5 个场景，
断言 events 顺序、outcome、errorMessage、verdict 都对。

### Part 3：前端页面

**替换占位文件** `admin/spiderAdmin/src/pages/queue/TracePage.tsx`（菜单键 `MenuKeys.QueueTrace` 与
插槽主控已在 Phase 0 接好，见 `00-shared.md` §3，不要再改 `navState.ts` / `AppLayout.tsx`）：

- 顶部：一个大输入框（贴链接/分享 id）+ 时间范围（缺省最近 7 天）+ 「包含网关 RPC 日志」开关 + 查询按钮
- 身份卡片：类型 / 分享 id / taskKey / 规范化 URL / resId(md5)；解析失败时用 `Alert` 提示
- **结论条**：`verdict` 大字显示，成功绿色 / 失败红色 / 未知灰色
- **时间轴**：用 antdv `<Timeline>`，每个节点 = 一个 `TraceEvent`，显示时间(含毫秒)、阶段中文名、
  summary；`outcome != ok` 用红/黄色圆点；有 `errorMessage` 的直接在节点里红字显示；
  点击展开看 `content` 与 `dataJson`（`JsonTree.tsx`）
- **阶段汇总条**：横向 steps，`instrumented=false` 的阶段灰显并加 tooltip 说明 note
- `warnings` 用 `Alert` 列在上方
- 「在日志搜索页打开」按钮 → `gotoLogSearch(...)`
- mock 数据里已经准备好一条完整成功链路 + 一个 `instrumented=false` 的阶段（见
  `packages/catalyst/contract/rpc/spiderGw/queueAdminMock.ts` 的 `mockTrace`），开 mock 开关就能调页面

## 交付

分支：SPIDER `feat/link-trace`，NC-JS `feat/link-trace`。

汇报里必须写清：
1. 补了哪些埋点（文件:行 清单）
2. `go build ./...`、`go vet` 新包、`go test ./services/gateway/queue_admin/...` 的真实输出
3. 5 个单测场景各断言了什么
4. **`link_key` 顶层字段需要人工在 SLS 控制台建索引**（写进"需要人工"清单，并说明建完后
   把 `services.queue_admin.sls.link_key_indexed` 打开）
5. 埋点上线前查历史链接只能查到部分阶段——这一点你在 UI 上是怎么表达的
