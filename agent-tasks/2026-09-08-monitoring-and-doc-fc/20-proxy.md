# 20-proxy —— 代理池情况纳入 admin 后台

先读 `00-shared.md`，再读本文件。你是本任务的**全栈开发**（SPIDER 埋点 + 监控包 + 网关 RPC + NC-JS 页面）。

## 用户原话

> 将代理池情况加入 admin 后台。包括 5 分钟、1 小时、24 小时的
> - 推送 ip 数, 去重 ip 数
> - 前端实时展示
> - 按每个消费端场景分, 成功率、失败率（要区分统计 ip 不可用 和 ip 被所爬站封禁）、延迟（按百分比计 p99 p95）
> - 需要修改 代理池修复端 proxy-client 以支持数据上报点. 但是不要让 proxy-client 和数据上报耦合. 可以加入关键点 hook, 让依赖端调用
> - 监控上报逻辑不要分散在各消费端, 而是形成单独的 package, 由消费端发起注册
>
> 总的来说就是尽可能少的侵入现有业务逻辑代码

## 现状（已调研，不用重查）

- **供给侧**：`services/proxy-provider/proxy-provider.go`
  - 单实例，部署在 osec-jenkins（`deploy.sh` 的 `serviceToHosts["proxy"]="osec-jenkins"`）
  - 蜻蜓 API 每 12s 拉 100 个 → `illuminate/proxy-pool` 的 50 并发 checker 校验 → 逐个
    `rds.Publish(conf.PubChannel, proxy.Encode())`（**发布点：`proxy-provider.go:268`**）
  - payload 就是裸字符串 `"ip:port"`（`illuminate/proxy-pool/proxy.go:14,20`），**不要改这个编码**，
    改了所有订阅方都受影响
  - `proxy-pool/proxy.go:58-65` 的 `checkedMap` 每 60s 全量清空 → 同一 IP 大约每分钟被重发一次，
    所以"推送 ip 数"和"去重 ip 数"必然差很多，这是正常的
  - 频道名来自 `config.Config.Services.Proxy.PubChannel`，生产值是 `proxy_subject`
- **消费侧**：`illuminate/proxy-client/`（`proxy-client.go` / `proxy-leader.go` / `proxy-helper.go`）
  - `ProxyClient` 结构体 `proxy-client.go:43-58`；`Do(req *Request) (*Response, error)` `:134-192`
  - `Response.Proxy` 字段里有本次实际用的代理（`:32-39`）
  - **唯一的错误收敛点是 `proxy-client.go:172-190`**：
    `strings.Contains(err.Error(), "proxyconnect tcp")` → `KillProxy`，其余 → `BlockProxy(1s)`
  - **没有任何场景/站点标识**，22 个实例化点各建各的池
  - 三个包都没有 import prometheus / redis / config
- **有 22 个 `ProxyClient{}` 实例化点**（爬虫 / 网盘客户端 / valid checker / 下载调度 / lifecycle_checker），
  跨 SPIDER 与 API 两个仓库（`osec-resource-api/services/valid/valid.go:29` 也建了一个）
- 代理池目前**零 metrics、零后台页面**

## 架构设计（照此实现，不要自行改方案）

### A. `illuminate/proxy-client` 只加 hook，不加任何上报逻辑

新建 `illuminate/proxy-client/hook.go`：

```go
package proxy_client

// ResultKind 一次代理请求的结果分类。
type ResultKind string

const (
    ResultOk          ResultKind = "ok"
    ResultIpUnusable  ResultKind = "ipUnusable"  // 代理本身不可用: CONNECT 失败/连接被拒/超时/TLS 失败
    ResultSiteBlocked ResultKind = "siteBlocked" // 被目标站点拦截: 429/403/站点业务码
    ResultHttpError   ResultKind = "httpError"   // 其它非 2xx
    ResultOther       ResultKind = "other"
)

// RequestOutcome 一次(单次, 不含重试聚合)代理请求的观测结果。
type RequestOutcome struct {
    Scene      string          // ProxyClient.Scene
    Proxy      proxy_pool.Proxy
    Host       string          // 目标站点 host
    StatusCode int             // 无响应时为 0
    Latency    time.Duration
    Retry      int
    Err        error
    Kind       ResultKind
}

// Hook 观测钩子。proxy-client 只负责调用, 不关心实现。
// 实现方必须自己保证非阻塞与不 panic。
type Hook interface {
    OnRequestDone(o RequestOutcome)
    OnProxyAdded(scene string, p proxy_pool.Proxy)
    OnProxyKilled(scene string, p proxy_pool.Proxy)
    OnProxyBlocked(scene string, p proxy_pool.Proxy, d time.Duration)
}

func RegisterHook(h Hook)   // 进程级注册, 允许多个; 并发安全
```

`ProxyClient` 只加两个字段（**其余一律不改**）：

```go
Scene string  // 消费端场景名, 如 "quark" / "bbs_kuakes" / "valid_bnd"; 为空时上报为 "unknown"
// ClassifyResult 业务可选提供的结果分类器, 用来把站点自己的业务码/状态码判成 siteBlocked。
// 返回空字符串表示"用默认分类"。
ClassifyResult func(res *Response) ResultKind
```

`Do()` 里的埋点要求：
- 在 `case res = <-req.resCh:` 之后、走重试之前，**每一次实际发出的请求**都调一次
  `fireRequestDone(...)`（含被重试掉的那些），latency 用该次请求的耗时。
- 默认分类器（新建 `classify.go`）：
  - `err != nil`：含 `proxyconnect tcp` / `connection refused` / `connection reset` / `no route to host`
    / `i/o timeout` / `context deadline exceeded` / `tls:` / `EOF` → `ResultIpUnusable`；其余 → `ResultOther`
  - `err == nil`：`StatusCode` 429 或 403 → `ResultSiteBlocked`；2xx/3xx → `ResultOk`；其余 → `ResultHttpError`
  - 若 `pc.ClassifyResult != nil` 且返回非空，**以业务返回值为准**
- hook 调用必须包在 `defer recover()` 里，**任何 hook 的错误都不能影响请求本身**。
- `KillProxy` / `BlockProxy` / `AddProxy` 里各调一次对应 hook。
- **`illuminate/proxy-client` 不许 import prometheus / redis / config / 任何 services 包。**

### B. 新建独立监控包 `illuminate/proxy-monitor/`（package `proxy_monitor`）

职责：实现 `proxy_client.Hook`，在内存里按分钟聚合，定期批量刷进 redis。**消费端主动注册。**

公开 API：

```go
// Init 进程级初始化: 注册 hook + 启动后台 flush goroutine。多次调用只生效一次。
// rds 用代理池那个 redis(config.Config.Services.Proxy.Redis), 保证与 proxy-provider 同库。
func Init(rds redis.UniversalClient, hostname string) error

// Attach 给一个 ProxyClient 打上场景标签(等价于设置 pc.Scene), 由消费端调用。
func Attach(pc *proxy_client.ProxyClient, scene string)

// RecordPublish 供给侧(proxy-provider)专用: 记录一次代理推送。
func RecordPublish(ip string, ok bool)
```

Redis 数据模型（key 前缀统一 `proxyMon:`，**全部按分钟分桶 + TTL 26 小时**）：

| key | 类型 | 内容 |
|---|---|---|
| `proxyMon:c:<minute>` | hash | field `<scene>|<kind>` → 次数；另有 `<scene>|_sumLatencyMs`、`<scene>|_count` |
| `proxyMon:h:<minute>` | hash | 延迟直方图，field `<scene>|le|<bucketMs>` → 次数（累积桶，含 `+Inf`） |
| `proxyMon:ip:<scene>:<minute>` | HLL | 该场景该分钟用到的去重代理 IP（PFADD） |
| `proxyMon:pub:<minute>` | hash | `total` / `fail` |
| `proxyMon:pubip:<minute>` | HLL | 该分钟推送的去重 IP |
| `proxyMon:scenes` | zset | member=scene，score=最后上报毫秒（供 `ListProxyScenes` 与前端下拉） |
| `proxyMon:hosts:<scene>:<minute>` | set | 上报该场景的主机名 |

- `<minute>` = `unix秒 / 60`
- 延迟桶（毫秒，**固定不可变，改了会让历史数据错位**）：
  `10,25,50,100,200,300,500,750,1000,1500,2000,3000,5000,8000,12000,20000,30000,+Inf`
- flush 周期 **10 秒**，用 pipeline 一次提交；进程退出时（`app.OnExit`）再 flush 一次
- 内存聚合必须有上限保护：scene 数超过 200 时新场景归入 `"__overflow__"`，防止标签爆炸
- **本包不许 import config**（保持可被 API 仓库复用）；配置由调用方注入

### C. 消费端接入（尽量少侵入）

- 在 `spider.go` 的进程启动流程里**统一调一次** `proxy_monitor.Init(...)`（redis 从
  `config.Config.Services.Proxy.Redis` 建），失败只打日志不阻断启动。
  找一个所有子命令都会经过的位置（`spider.go` 的 main / 命令分发前）。
- 22 个 `ProxyClient{}` 实例化点**只加一个 `Scene:` 字段**，不要动别的参数。场景命名规则：
  | 位置 | scene |
  |---|---|
  | `services/quark/quark-client.go` | `quark` |
  | `services/aliyun-drive/ad-client.go` | `alipan` |
  | `services/xunlei-pan/xl-client.go` | `xunlei` |
  | `services/share/baidu-client.go` 用的池 | `baidu` |
  | `services/bbs/*.go` | 站点子命令名，如 `bbs_kuakes` / `bbs_misoso` |
  | `services/keyword/**` | `keyword_<站点>`，如 `keyword_aipanso` |
  | `services/haisou/haisou.cc.go` | `keyword_haisou` |
  | `services/gateway/valid/valid.go` 的 4 个池 | `valid_bnd` / `valid_quark` / `valid_xunlei` / `valid_alipan` |
  | `services/gateway/download_scheduler/**` | `download_<用途>`，如 `download_bnd_resolver` |
  | `services/devops/clear_expire` | `clear_expire` |
  | `services/lifecycle_checker` | `lifecycle_checker` |
  | `services/v2/res_crawler/bnd/bnd_input_pwd.go` | `bnd_input_pwd` |
  | `services/spider-common/debug_proxy_server.go` | `debug_proxy` |
  | `services/spider_util/dev_utils.go` | `dev` |
- **API 仓库（`osec-resource-api/services/valid/valid.go:29`）也加 `Scene: "api_valid"` 并调 `Init`**。
  它 import 的是 SPIDER 的 illuminate 包，改完两边都要能 build。
- **区分"IP 被所爬站封禁"**：给几个已知会返回 429 的池加 `ClassifyResult`：
  quark（`quark-client.go` 已有 429 判定）、alipan、xunlei、`valid/*_checker.go`、haisou
  （haisou 的业务码 11003/13001 明确是站点拦截 → `ResultSiteBlocked`）。
  其余保持默认分类。**不要重写这些业务原有的重试/冷却逻辑**，只是多返回一个分类值。
- 供给侧：`proxy-provider.go:268` 的 publish 前后各加一行 `proxy_monitor.RecordPublish(string(proxy), err == nil)`，
  并在 `Start()` 里调 `Init`。

### D. 网关侧读取与聚合：新建 `services/gateway/proxy_admin/`

照抄 `services/gateway/queue_admin/` 的结构（`register.go` / `service.go` / `errors.go`）。

- `Register(rtcServer, grpcServer, rds)`，由 `services/gateway/gateway.go` 的 `Start()` 调用，
  注册失败只记日志不阻断网关启动（与 queue_admin 一致）
- redis 用哪个：优先 `config.Config.Services.Proxy.Redis`（与上报侧同库），为空时回落网关 redis；
  在响应的 `dataSource` 字段里回显实际用的 key 前缀，便于排查
- 实现 proto 里的三个方法：
  - `ProxyOverview`：对每个窗口（缺省 300/3600/86400 秒）把对应分钟桶 `HGetAll` 回来求和；
    分位数由累积直方图**线性插值**得出（标准 Prometheus `histogram_quantile` 算法，
    落在 `+Inf` 桶时返回最后一个有限桶边界并在注释里说明）；
    去重 IP 用 `PFCOUNT key1 key2 ...`（redis 支持多 key 并集）；
    **24h 窗口有 1440 个 key，必须做 60 秒结果缓存**（抄 `queue_admin/stats.go` 的缓存写法）
  - `ProxySceneSeries`：按 `intervalSec`（必须是 60 的整数倍）聚合分钟桶成时序点
  - `ListProxyScenes`：读 `proxyMon:scenes` zset，取最近 24h 有上报的
  - 无数据时：计数为 0，比率与分位数返回 **-1**（proto 注释已定义），不要返回 0
- **不需要 leader 判断**（纯只读查询，两台机都能服务）
- prometheus 指标可选，不做也行；做的话前缀 `proxy_admin_`

### E. 前端（NC-JS `admin/spiderAdmin`）

1. TS 契约（`proxy_admin_rpc`）、`useGwClient` 的 `proxyAdminRpc`、菜单项、插槽与 props 传递
   **主控已在 Phase 0 做好**（见 `00-shared.md` §3），不要重做。你只需要**替换两个占位页面的内容**。
   占位组件当前的 props 是 `ProxyOverviewPage{isShow: boolean, proxyAdminRpc: any}`、
   `ProxySceneDetailPage{proxyAdminRpc: any}`，请把 `any` 换成真实的 `ProxyAdminRpcClient` 类型
   （从 `@nc/catalyst/contract/rpc/scheduler/proto/proxy_admin_rpc/proxy_admin.client` 导入）。
2. 替换 `src/pages/proxy/ProxyOverviewPage.tsx`：
   - 三列卡片：5 分钟 / 1 小时 / 24 小时，每列展示 **推送 IP 数**、**去重 IP 数**、
     全场景汇总的成功率/IP 不可用率/被封禁率、p95/p99
   - 下方表格：按场景一行，列 = 场景 / 请求数 / 成功率 / IP 不可用 / 被站点封禁 / 其它错误 /
     p50 / p95 / p99 / 用到的去重 IP 数 / 上报主机数；可切换看哪个窗口
   - **实时展示**：`useDocumentVisibility() + useTimeoutToRef(5e3)` 每 5 秒自动刷新（抄
     `pages/queue/OverviewPage.tsx`），页签不可见时停
   - 失败率高的行用颜色标出（比率 > 0.3 警告色，> 0.6 危险色）；`-1` 一律显示为 `—`
3. 替换 `src/pages/proxy/ProxySceneDetailPage.tsx`：
   场景下拉（`ListProxyScenes`）+ 时间范围，用 `MiniLineChart.tsx` 画请求量堆叠与 p95/p99 曲线。

## 硬性要求

- **`illuminate/proxy-client` 与 `illuminate/proxy-monitor` 都不许 import `config` 包**；
  proxy-client 更不许 import proxy-monitor（依赖方向只能是 monitor → client）。
- 埋点**不得改变任何现有的重试、Kill、Block 行为**。改完 `go test ./illuminate/...` 要过。
- 上报路径必须完全非阻塞：channel 满就丢弃并累加一个本地丢弃计数（在 flush 日志里输出），
  绝不能因为 redis 慢而拖住爬虫请求。
- redis 写入用 pipeline；单次 flush 的命令数要有上限。

## 交付

分支：SPIDER `feat/proxy-monitor`，API `feat/proxy-monitor`，NC-JS `feat/proxy-monitor`。

汇报里必须写清：
1. 22 个实例化点你实际改了哪些、场景名各是什么（列表）
2. `go build ./...`（SPIDER 与 API 两个仓库都要）、`go vet ./illuminate/proxy-client/... ./illuminate/proxy-monitor/... ./services/gateway/proxy_admin/...`、
   `go test ./illuminate/...` 的真实输出结论
3. 分位数插值算法你怎么实现的，写了什么单测
4. 没做完的部分 / 需要人工确认的（例如某些池的 `ClassifyResult` 需要业务确认）
