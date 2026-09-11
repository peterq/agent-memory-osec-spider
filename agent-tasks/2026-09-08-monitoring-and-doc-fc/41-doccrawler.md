# 41-doccrawler —— 服务端文档爬虫进程 doc-crawler

先读 `00-shared.md` 与 `05-doc-fc-contract.md`，再读本文件。
你负责**服务端进程**。并行的角色 40 负责 FC Chrome 环境与云端油猴脚本；
接口以 `05-doc-fc-contract.md` 为准，**不要等他，按契约先写**。

## 用户原话（本角色相关部分）

> 背景: 有很多资源爱好者, 通过在线文档的方式组织并维护更新大批量的分享链接,
> 并传播该文档以此盈利. 现在已接入文档内链接爬虫.
> 现有情况: 由于在线文档的复杂性, 直接逆向比较困难, 且可能因为服务商修改通信协议导致链路失效.
> 所以文档队列由服务器维护. 但是文档爬虫由 pc 上的油猴脚本完成.
> 目标:
> - 去掉对 pc 的依赖, 通过阿里云函数计算 fc, 在云端运行 chrome 实例.
> - 服务端进程 doc-crawler, 从 gateway pop 任务, 控制并发, 调用 fc.

## 现状（已调研，不用重查）

### 服务端文档调度（网关侧，**本轮不要改它**）

- `services/gateway/doc_scheduler/doc_scheduler.go`：队列名 **`doc_crawler`**（`:243`），
  `queue_task.NewQueue2("doc_crawler", rds, hostname)`
- 队列任务结构体 `Task`（`:21-37`），`Key() = t.Model.Url`；`Model` 是整行 `spider_dao.DocModel`
- DB 模型：`services/gateway/spider_dao/doc_dao_models.go:14-31`
- 灌任务：`loopLoadDbTask2Queue`(`:248`) / `load20DbTask2Queue`(`:314`)，优先级
  `priorityNextCrawlReady=127` / `priorityNew=128`，失败重试 `+10`
- `PopTask`(`:361`)：`queue.PopAndPendingCtx(ctx, 15s)`，空返回 `ErrNoMoreTask(110101)`
- **保活超时 10 秒**（`:672` `loopCheckTimeoutTask` 每 2s 扫，10s 无保活即判超时失败）
- 重试：`Retry<3` 原地 RePush 抬优先级；≥3 → `saveRetry24HoursLater`
- 成功入库 `saveSuccess`(`:589`)，复爬间隔算法 `doc_dao_models.go:133-165`

### gRPC 契约（已存在，不用改 proto）

`COMMON rpc/spider/doc_scheduler_rpc/doc_scheduler.proto`，`service DocSchedulerRpc`：
`PopTask(PopTaskParams) -> Task`、`TaskKeepalive({seq_id,url}) -> Empty`、
`TaskDone(TaskDoneParams{seq_id,url,success,fail_msg,Invalid,type,doc_mtime,version,link_count,meta}) -> Empty`。

链接提交用 `COMMON rpc/spider/spider-gw.proto` 的 `spider.SpiderRpc/CommitResource2`
（`services/gateway/gw_rpc_server.go:173`，支持 `Meta`，比爬虫路径多一个 `submit_user_id` 维度）。

**网关两种 transport 都注册了**（`services/gateway/gateway.go:367,376`），
所以 doc-crawler 直接走**标准 gRPC**，不需要 WebRTC。

### 现有 PC 端调度逻辑（要直译的对象，只读）

`/home/peterq/dev/projects/peterq/userscripts/src/plugins/scheduler/scheduler.ts`：
`popServerTaskLoop()`(`:84`)、`spiderThread(i)`(`:128`，`maxParallel=5`、默认 `parallel=2`)、
`runTask()`(`:156`：开标签页 → 8s 内必须收到页面 ping → 期间调 `taskKeepalive` → 收结果调 `taskDone`)。

## 实现要求

### 落点

- **新子命令 `doc_crawler`**，代码放 `services/doc_crawler/`
  （用户明确要求独立进程，是 "管理类不新增进程" 决策的例外；在包注释里写明这一点）
- 在 `spider.go` 的 commands 表里注册（照抄相邻条目的写法）
- `deploy.sh` 里加 `serviceToCmd["doc_crawler"]="doc_crawler"` 与 `serviceToHosts`
  （主机先填 `osec-jenkins`，**并在注释里标注"待用户确认部署主机"**）
- 配置：`config/config.go` 新增 `Services.DocCrawler`，**所有字段必须有内置缺省值**
  （线上非 gateway 服务的 config.yaml 不由 deploy.sh 分发），开关用 `*bool`

配置项（缺省值照写）：

| 字段 | yaml | 缺省 | 说明 |
|---|---|---|---|
| `Enabled` | `enabled` | `*bool` nil = 开 | |
| `GatewayAddr` | `gateway_addr` | 复用现有网关客户端配置的取法（照抄别的消费者进程怎么连网关） | |
| `FcEndpoint` | `fc_endpoint` | `ws://nc-app-prod-cdp3.cn-hangzhou-vpc.fcapp.run/chrome` | **新实例域名尚不存在，写成缺省值 + TODO 注释** |
| `FcEndpointPublic` | `fc_endpoint_public` | 公网版同名域名 | 本机调试用 |
| `Concurrency` | `concurrency` | `2` | 同时跑几个文档 |
| `MaxConcurrency` | `max_concurrency` | `5` | 上限 |
| `TaskTimeoutSec` | `task_timeout_sec` | `240` | 单文档最长耗时，必须 < FC 单实例 300s |
| `KeepaliveSec` | `keepalive_sec` | `5` | |
| `FirstEventTimeoutSec` | `first_event_timeout_sec` | `60` | 多久没收到 `start` 判失败 |
| `UserscriptUrl` | `userscript_url` | `https://osec-deploy-pub.oss-cn-hangzhou.aliyuncs.com/fc-chrome/userscripts/kdoc.user.js` | |
| `ExtraExtensions` | `extra_extensions` | 空 | 逗号分隔的扩展 URL |
| `UseCdpInject` | `use_cdp_inject` | `*bool` nil = 开 | 走 CDP 直接注入而非依赖油猴（见契约 §5） |
| `CommitBatchSize` | `commit_batch_size` | `200` | |

### 主流程

```
启动 → 连网关(标准 gRPC) → 起 N 个 worker
worker:
  PopTask (阻塞 15s, NoMoreTask 就退避 3~10s 重试)
  → 生成 nonce
  → 连 FC: ws://<fc>/chrome?script=<userscriptUrl>&inject=1&ext=<extra>&timeoutSec=<...>
  → CDP: Target.createTarget(docUrl + "#taskNonce=" + nonce) / Page.navigate
  → 监听 Runtime.consoleAPICalled, 解析 [[DOC_SPIDER]] 前缀的消息(见契约 §3)
  → 每 5s TaskKeepalive
  → 收到 final result:
        version 与 task.model.version 相同 → 不提交链接
        否则 CommitResource2 分批提交
        TaskDone{success:true, ...}
  → 收到 error 事件: TaskDone{success:false, failMsg, Invalid: permanent}
  → 任何超时/连接断开: TaskDone{success:false, failMsg:"..."}, 并保证 Chrome 连接被关闭
  → defer 关 WS、关 target
```

### 硬性要求

1. **并发控制**：worker 数由配置决定且可在运行时被 `MaxConcurrency` 兜住；
   每个 worker 一条独立 WS（一次 WS = 一个 Chrome 实例），**不要复用 WS 跑多个任务**
   （FC 侧单实例 300 秒上限，复用会互相牵连）。
2. **保活是硬要求**：网关 10 秒没保活就判超时并重推，会导致同一文档被反复爬。
   保活 goroutine 必须在任务开始时就起，任何退出路径都要停掉。
3. **每个任务必须有终态**：不管成功、失败、panic、超时，都要调一次 `TaskDone`（用 defer + recover 保证）。
   `TaskDone` 本身失败要重试 3 次。
4. **优雅退出**：收到 SIGTERM 时停止 Pop、等在跑的任务做完（最多等 `TaskTimeoutSec`）再退出，
   否则容器重启会留下一批 pending 任务等超时。
5. **日志**：用 `logger.Logger("doc-crawler")` 打结构化日志（会进 SLS），
   每个任务至少有 `pop` / `chrome-connected` / `first-event` / `result` / `done` 五个 stage，
   `data` 带 `{url, nonce, seqId, linkCount, version, duration}`。
   失败时把 `failMsg` 打全。
6. **CDP 客户端选型**：优先用仓库已有的依赖。SPIDER 里 `tools/ujuso-captcha/` 用了 `chromedp`
   （独立 go.mod）。主仓 go.mod 里**没有** chromedp —— 你有两个选择：
   (a) 给主 go.mod 加 chromedp；(b) 自己用 `gorilla/websocket` + 裸 CDP JSON 实现
   （只需要 `Target.createTarget` / `Runtime.enable` / `Runtime.consoleAPICalled` /
   `Page.addScriptToEvaluateOnNewDocument` / `Target.closeTarget` 这几条，代码量不大且依赖最少）。
   **推荐 (b)**，理由写进代码注释；选 (a) 要在汇报里说明新增依赖及其体积。
7. **不要改 `services/gateway/doc_scheduler/` 的任何逻辑**。如果发现它有问题，写进汇报，不要动手。
8. FC 不可用时（连不上/握手 4xx）要有退避，不要空转打爆日志。

### 测试

- 单测：console 协议解析（含分批 `seq/final`、超大消息、脏数据）、
  版本未变跳过提交、终态保证（模拟 panic 也要 TaskDone）、优雅退出
- **本地端到端**：可以起一个假的 WS 服务端冒充 FC（按契约 §2/§3 回放一段 console 事件）+
  假的 gRPC 网关（参考 `osec-spider-go/tools/stubgw`，那是 2026-09-08 GitHub OAuth 联调时写的桩网关，
  看它怎么起一个只实现被测接口的 gRPC/RTC 服务）。**这条必须真的跑通并给出输出**。

## 交付

分支：SPIDER `feat/doc-crawler`。

汇报里必须写清：
1. 文件清单与职责
2. `go build ./...`、`go vet ./services/doc_crawler/...`、`go test ./services/doc_crawler/...` 的真实输出
3. 端到端桩测试的实际输出
4. CDP 客户端选型的理由
5. 需要人工确认的：部署主机、FC 新实例域名、是否要下线 PC 上的油猴调度器
