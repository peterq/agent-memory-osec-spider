# 角色 20：SPIDER search_admin —— 搜索总览（SLS）+ 匿名搜索防护巡检

工作树：`/home/peterq/dev/projects/1s/osec-spider-go-wt-search`（git worktree，分支 `feat/search-admin`）。**只在这个目录里干活**，主工作树另一个角色在用。
新建模块 `services/gateway/search_admin/`，再改 `config/gateway/gateway.go`（配置节）、`services/gateway/gateway.go`（注册一行）、`tools/sls-probe/README.md`（写用法）。

## 必读

1. `00-shared.md`（同目录），尤其 §4.1 SLS、§4.2 redis 键约定、§4.4 注册方式。
2. `enfi-resource-common/rpc/spider/search_admin_rpc/search_admin.proto` 全文（口径、缺省值、上限）。
3. `services/gateway/queue_admin/sls.go`（SLS 封装）、`queue_admin/worker_leader.go`（抢主锁）、`lifecycle/alert.go`（邮件 + 去抖）、`proxy_admin/register.go` + `proxy_admin/service.go`（最简模块骨架）、`lifecycle/config.go` `applyDefault`（配置缺省回填写法）。
4. `tools/sls-probe/main.go`（已有的只读探针）。

## 要做的事

### A. 配置节 `services.search_admin`（`config/config.go` 定义结构体，`config/gateway/gateway.go` 挂到 `Services`）
```yaml
services:
  search_admin:
    enabled: true              # 缺省 true: 只读接口永远注册; false 只关巡检
    sls:                       # 全部可空: endpoint/ak/sk/project 为空回落 gw_config.Get().AliLog; log_store 缺省 resource-backend
      endpoint: ""
      ak: ""
      sk: ""
      project: ""
      log_store: resource-backend
      sql: auto                # auto | on | off; auto = 启动时探测一次, 失败降级并每小时重试探测
      max_scan_lines: 50000    # 降级扫描的最大拉取行数
    guard:                     # 与 proto GuardParams 一一对应的缺省值
      enabled: true
      p90_threshold_ms: 3000
      window_sec: 300
      poll_interval_sec: 60
      sustain_polls: 2
      min_sample: 30
      close_minutes: 30
      alert_debounce_sec: 1800
      auto_close: true
      notify_url: http://cf-worker.peterq.cn/notify_admin
```
线上不分发本节也必须能跑（全部缺省），与 `QueueAdminConfig` 注释里的原则一致。

### B. SLS 聚合层（`sls.go` + `agg.go`）
- `slsClient`：照 `queue_admin/sls.go`，加 `query(sql string, from, to int64, limit int64) ([]map[string]string, error)`。
- 固定检索前缀：`service:resource-search-api and (stage:search or stage:search-v3)`；`entry=v2` 只取 `stage:search`，`v3` 只取 `stage:search-v3`。
- **SQL 路径**（`sqlAgg`）：
  - Overview 时序：`| select (__time__ - __time__ % {桶秒}) as t, count(*) as c, count_if(level='error') as err, count_if(json_extract_scalar(data,'$.backend')='v3' or stage='search-v3') as v3, count_if(coalesce(json_extract_scalar(data,'$.uid'),'')='' or json_extract_scalar(data,'$.uid')='anonymous') as anon, count_if(json_extract_scalar(data,'$.guard')='anonymous_closed') as blocked, count_if(level<>'error' and cast(json_extract_scalar(data,'$.result.total') as bigint)=0) as empty, count_if(cast(json_extract_scalar(data,'$.duration') as bigint)>2000) as slow, avg(cast(json_extract_scalar(data,'$.duration') as bigint)) as avg_ms, approx_percentile(cast(json_extract_scalar(data,'$.duration') as bigint),0.5) as p50, approx_percentile(...,0.9) as p90, approx_percentile(...,0.99) as p99, max(...) as max_ms, approx_distinct(json_extract_scalar(data,'$.ip')) as ips, approx_distinct(if(json_extract_scalar(data,'$.uid')<>'anonymous', json_extract_scalar(data,'$.uid'), null)) as uids group by t order by t limit 100000`
    区间合计再单独发一条不带 group by 的（去重指标要按整区间去重）。`v2Count = count - v3Count`。
  - Top：`| select json_extract_scalar(data,'$.kw') as k, count(*) as c, avg(...) as avg_ms, count_if(level='error') as err, count_if(...total=0) as empty, max(__time__) as last_ts, approx_distinct(json_extract_scalar(data,'$.uid')) as dk group by k order by c desc limit {limit}`；ip/uid 榜同理（`dk` 分别 = 不同 uid 数 / 不同 ip 数）。
  - SQL 是否可用：启动时（及每小时）用 `| select count(*) as c` 对最近 5 分钟探测；报错则 `sqlAvailable=false`，响应 `source=sls-scan`、`note` 写明「logstore 未开启字段统计, 已降级」。
- **扫描路径**（`scanAgg`）：`GetLogs` 反向分页（`reverse=true`，`offset` 步进，单页 ≤ 100 条是 SDK 限制？以 `queue_admin/sls.go` 用的 200 为准）直到窗口取完或到 `max_scan_lines`；逐条解析 `data` JSON 后在内存里算同一套指标（延迟分位排序取分位；去重用 map）。达到上限 → `truncated=true`。两条路径共用一个 `func(logs) SearchStats` 的纯函数便于单测。
- 结果缓存：按（method, fromMs, toMs, bucket, entry, kind, limit）60s；`toMs` 在「现在」附近的请求把 `toMs` 向下对齐到整分钟再缓存，避免每秒都 miss。
- 所有查询带 `context` 超时 40s；SLS 未配置/不可用时返回明确错误（`errSlsNotConfigured`），不 panic。

### C. 匿名搜索防护（`guard.go`）
- 参数：配置缺省 + redis hash `search_guard:params` 覆盖（字段名与 proto `GuardParams` 的 camelCase 一致），`UpdateGuardParams` 只写非零/已 Set 字段；每次巡检前重读。
- leader-only 巡检（自己的锁键 `search_guard:leader`，照 `worker_leader.go`），每 `pollIntervalSec`：
  1. 取最近 `windowSec` 的合计（`count`, `p90Ms`）；`count < minSample` → 记 state，streak 清零，跳过。
  2. `p90 > threshold` → streak++，否则 streak=0。写 `search_guard:state`（lastEvalAtMs/lastP90Ms/lastSample/overStreak/leaderHost）。
  3. `streak >= sustainPolls` 且去抖未命中 → `fire`：邮件（subject `[搜索防护] p90 {p90}ms 连续 {n} 次超阈值 {threshold}ms`，正文含窗口、样本数、是否已关闭匿名、到期时间、主机；`source=search-guard`），事件 `alert`；若 `autoClose` → `SET search_guard:anonymous_closed <json> EX closeMinutes*60`（已关闭则**续期**到新的 until），事件 `auto_close`。触发后 streak 清零。
  4. 每轮顺带检查：上一轮记录为关闭而现在键已不存在 → 事件 `auto_expire`（用 state 里的 `closedUntilMs` 判断，避免重复）。
- `SetAnonymous`：`closed=true` → 写键（`by=manual:<operator>`，TTL=minutes 或缺省），事件 `manual_close`，发邮件（同 source）；`closed=false` → DEL，事件 `manual_open`，发邮件。非 leader 也可执行（写 redis 即可）。
- `GuardStatus`：读键（`TTL` 推 `closedUntilMs`，值 JSON 里的 reason/by/closedAtMs）、参数、state、events（`LRANGE 0 49`），`leader/leaderHost`。
- 巡检出错（SLS 挂了）只记日志 + state 里记 `lastError`（放进 `note`），不发告警邮件轰炸（每小时最多一封 `warn`）。

### D. RPC 服务与注册
- `service.go`：`Service` 嵌 `search_admin_rpc.UnimplementedSearchAdminRpcServer`；`NewService(conf, rds, aliLog)`；`register.go` 照 `proxy_admin`；`gateway.go` 在 `proxy_admin.Register` 之后加一段注册（注释说明用途，失败只记日志）。
- 日志用 `logger.Logger("search-admin")`，关键动作（fire/close/open/params）`WithStage` 打 Warn/Info。

### E. 工具与文档
- `tools/sls-probe/README.md`：用途、环境变量名（**不写值**）、三条示例（原始日志 / SQL count / 带 json_extract 的分位）；说明在 auto 模式下可能被权限拦截。
- `services/gateway/search_admin/README.md`：模块说明、配置、redis 键、SQL 与降级、巡检状态机、如何本地用桩跑单测、线上验证步骤（给主控用）。

### F. 测试
- `agg_test.go`：给定一组伪日志（含 v2/v3/error/anonymous/blocked/empty/slow）断言 `SearchStats` 各字段与分位；扫描分页与 `truncated`。
- `sql_test.go`：SQL 拼装（桶秒、entry 过滤、limit 上限）与结果行 → 结构体解析（列缺失/非数字要容错为 0）。
- `guard_test.go`：用假 aggregator + `miniredis`（先查 `go.mod`，没有则写最小 `redis.UniversalClient` 桩）跑巡检状态机：样本不足不触发；连续 2 次触发一次并写键与事件；去抖内不重复邮件；autoClose=false 只发邮件；手动开/关；到期事件。
- `go build ./... && go vet ./services/gateway/search_admin/... ./config/... && go test ./services/gateway/search_admin/... ./config/...`。
- 如能通过 `tools/sls-probe` 联网（可能被拦），验证一次 SQL 可用性并在交付里写结论；被拦就明说。

## 交付（最终回复里写）
- 改动文件清单 + 提交哈希（分支 `feat/search-admin`，不 push）。
- 测试命令与结果；SQL 可用性探测结论（或「未能验证」）。
- 线上启用后主控要做的验证步骤（README 里也有）。
- 对契约的疑问（如有）。
