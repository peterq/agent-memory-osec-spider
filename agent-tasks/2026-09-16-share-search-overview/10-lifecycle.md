# 角色 10：SPIDER lifecycle —— `LifecycleRpc.ShareOverview` + 按类型检测计数器

工作树：`/home/peterq/dev/projects/1s/osec-spider-go`（分支 `feat/share-search-overview`）。只改 `services/gateway/lifecycle/` 及其 README。

## 必读

1. `00-shared.md`（同目录）。
2. `enfi-resource-common/rpc/spider/lifecycle_rpc/lifecycle.proto` 末尾「分享链接总览」一节（口径与字段）。
3. `services/gateway/lifecycle/README.md`、`stats.go`（计数器与 Stats 缓存）、`result.go`（三个 onCheck*）、`browse.go`+`browse_dao.go`（`ListEvents`/`TableStats` 的参数校验、缓存、DAO 写法——新接口照这个风格）、`rpc_service.go` `Overview`（TypeStat 转换）、`esops.go`（ES 请求怎么发）、`typemap.go`（spider_contract 类型 ↔ ES type 值）。
4. `agent-memory/lessons/patterns-统计ES索引先查文档形态.md`。

## 要做的事

### A. 计数器加类型维度（`stats.go` + `result.go`）
- 新增按类型的桶：小时桶 `resLc:cnth:<name>:<type>:YYYYMMDDHH`（TTL 35 天）、天桶 `resLc:cntd:<name>:<type>:YYYYMMDD`（TTL 400 天）；`name ∈ valid|invalid|error`，`type` 为 spider_contract 常量（bnd/ali-share/quark/xunleipan）。
- **保留**现有全局分钟桶/天桶及 `LastHour/LastDays`（告警与指标在用），在 `Add` 里同一 pipeline 顺带写新桶：把 `Add(name, n)` 改成 `AddTyped(name, typ, n)` 或加一个新方法，三个 `onCheck*` 调用处传 `typ`。
- 新增读取方法：`RangeTyped(name, typ string, from, to time.Time, bucket string) (map[int64]int64, error)`（bucket=hour|day，返回桶起始 unix 秒 → 计数），用 `MGET` 批量取，键数 = 桶数 × 类型数，最多 92 天 × 24 × 4 ≈ 8.8k 个键，分批 500 个一组。
- 计数器起算时间：首次部署后新桶才有数据。把「计数器上线时间」写进 redis `resLc:cnt:since`（`SETNX` 当前时间，不覆盖），`ShareOverview` 的 `note`/`warnings` 用它说明「早于 X 的检测数为 0 是因为计数器尚未上线」。

### B. `ShareOverview` RPC（新文件 `share_overview.go` + `share_overview_test.go`）
1. 参数校验：`fromMs/toMs` 必填且 `toMs>fromMs`，跨度 ≤ 92 天，否则 `ErrInvalidParam`；`bucket` 空时 ≤3 天用 hour 否则 day；`type` 非空时必须是四种之一；`clientTopN` ≤0→20，上限 100。桶按 Asia/Shanghai 本地时间对齐（day 桶 = 本地 0 点）。
2. 事件聚合（MySQL）：一条 SQL
   `SELECT type, event, <bucket_expr> AS b, COUNT(*) FROM res_lc_event WHERE created_at >= ? AND created_at < ? [AND type=?] AND event IN ('created','updated','invalid','moved','legacy_invalid_hint') GROUP BY type, event, b`
   `bucket_expr`：hour 用 `DATE_FORMAT(created_at,'%Y-%m-%d %H:00:00')`，day 用 `DATE(created_at)`。走 `idx_created` 范围扫；用 `ctx` 超时 30s，超时返回 warnings 而不是整个失败。DAO 方法放 `browse_dao.go`（照 `CountEvents` 风格，参数化，不拼接用户输入）。
3. 检测计数：`RangeTyped` 取 valid/invalid/error 三组，`checked = 三者之和`。
4. ES 新增按来源：对 `s.conf.AliasAll`（为空回退 `gw_config.Get().EsResourceIndex`）发一条 `_search size=0`：
   `query = bool{filter:[range ctime[gte fromMs, lt toMs, format epoch_millis], <资源父文档过滤>, (type=? 可选)]}`，
   `aggs = by_type(terms type size 10) > by_client(terms client size clientTopN, missing "")` 以及 `by_bucket(date_histogram ctime interval 1h|1d, time_zone Asia/Shanghai) > by_type`（后者只用来填 `ShareCounts.esCreated` 的合计/按类型，不需要塞进 buckets）。
   **资源父文档过滤怎么写要先对拍**：用 `exists type` 与 `join=resource` 两种过滤各 count 一次（可在 `share_overview_test.go` 里以桩数据说明；无法联网时在 README 写清楚待线上核对的两条 `curl`），取两者一致的写法；不一致则用 `exists type` 并在 `note` 说明。ES 超时 20s，失败只写 warnings（`byClient` 为空），其余数据照常返回。
   ES type 值 → spider_contract 常量用 `typemap.go` 的现成映射。
5. 存量：`s.Stats()` → `stock`（四种类型固定顺序）。
6. 组装响应：`buckets` 按桶补齐（全 0 也要有）；`byType` 固定四种顺序（`type` 指定时只返回该种）；`total` 为全类型合计；`byClient` 按 created 降序；`note` 固定文案（把 proto 注释里的口径浓缩成 3~5 句中文）；`costMs/generatedAtMs`。
7. 缓存：结果按（fromMs,toMs,bucket,type,clientTopN）做 60s 内存缓存（参考 `statsCache`，加 mutex + map，最多 200 项 LRU 简化为满了清空）。
8. 注册：`Service` 已嵌 `UnimplementedLifecycleRpcServer`，实现方法即可；**不要求 enabled**（只读接口在 enabled=false 时也要能答，与 `ListEvents` 一致）。

### C. 测试
- `share_overview_test.go`：参数校验表驱动；桶补齐与本地时区对齐；事件聚合结果 → 响应组装（用 sqlite/内存 DAO 桩，看现有 `browse_test.go`/`dao_test.go` 怎么做的就照做）；计数器 `RangeTyped` 用现有测试里的 redis 桩方式（找 `stats_test.go`/`alert_test.go` 的做法，没有就用 `github.com/alicebob/miniredis/v2`——先看 `go.mod` 里有没有，没有就写一个最小 `redis.UniversalClient` 桩只实现用到的方法）。
- ES 部分用 `httptest.Server` 桩返回固定聚合 JSON，断言请求体里的 range/aggs 结构与结果解析。
- `go build ./... && go vet ./services/gateway/lifecycle/... && go test ./services/gateway/lifecycle/...` 全绿（integration/e2e 测试若需要真实 mysql/es 会自动 skip，保持原状）。

### D. 文档
- `services/gateway/lifecycle/README.md` 加一节「分享链接总览（ShareOverview）」：数据来源、计数器新键、缓存、已知口径差异、线上核对 curl。

## 交付（最终回复里写）
- 改动文件清单 + 提交哈希（分支 `feat/share-search-overview`，不 push）。
- 测试命令与结果摘录。
- 未能验证的项（例如 ES 文档形态对拍需线上核对）与建议核对命令。
- 对契约的疑问（如有）。
