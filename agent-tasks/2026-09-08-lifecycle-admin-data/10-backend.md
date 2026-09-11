# 角色简报：SPIDER 后端

> 先读同目录 `00-shared.md`。本文件只写后端专属内容。

## 要实现的方法

在 `lifecycle_rpc.LifecycleRpcServer` 接口新增的 4 个方法上实现：

1. `ListResources(ctx, *ListResourcesParam) (*ListResourcesResponse, error)`
2. `TableStats(ctx, *TableStatsParam) (*TableStatsResponse, error)`
3. `ListEvents(ctx, *ListEventsParam) (*ListEventsResponse, error)`
4. `TableDiagnostics(ctx, *common_message.Empty) (*TableDiagnosticsResponse, error)`

## 落点

- 实现：`services/gateway/lifecycle/browse.go`（新建）
- 测试：`services/gateway/lifecycle/browse_test.go`（新建）
- DAO 查询加到 `dao.go`，或同目录新建 `browse_dao.go` —— 按哪种更贴合现有风格自行判断

`Service` 结构体已实现整个 `LifecycleRpcServer` 接口，加上这 4 个方法即可满足新接口。

## 必读文件（读它们是为了拿到什么）

| 文件 | 要提取什么 |
|---|---|
| `services/gateway/lifecycle/rpc_service.go` | 现有 rpc 实现风格、`s.dao` 用法、错误返回习惯；**必须复用** `resourceLifecycleOf(typ, row)` 填 `ResourceLifecycle`，以及 `msToTime` |
| `services/gateway/lifecycle/dao.go` | `LcTableName` / `lcTableNameByBucket` / `LcAllTables` / `typeOfTable` / `bucketOf`、gorm 用法、`d.DB()`、已有的 `CountByIndexName` |
| `services/gateway/lifecycle/models.go` | `ResLifecycleModel` / `ResEventModel` / `ResCycleModel` / `ResJobModel` 与全部状态枚举常量 |
| `services/gateway/lifecycle/service.go`、`register.go` | Service 结构体的依赖（gorm DB、ES client、config）与注册方式 |
| `services/gateway/lifecycle/stats.go`、`esops.go` | 现有 ES 查询与统计缓存写法；`TableDiagnostics` 的 DB↔ES 对拍**必须复用**这里的 ES 访问方式，不要另起一套 http 客户端 |
| `services/gateway/lifecycle/dao_test.go` | 现有测试用了 gorm DryRun 还是 sqlmock，跟着用 |

## 实现要点

1. **超时**：每个 rpc 的所有 SQL 都用 `ctx` + gorm `WithContext`，并对未带 deadline 的 ctx
   兜一个默认超时——建议 `ListResources` / `ListEvents` 10s，`TableStats` / `TableDiagnostics` 30s。
2. **参数校验**：`type` 为空直接报错；`offset` 超 `maxOffset`（建议常量 10000）直接报错，
   并在响应里回传 `maxOffset` 让前端禁用深翻页；`limit` 夹到 1..200，缺省 50。
3. **SQL 注入**：分表名是拼进 SQL 的，必须用 `LcAllTables()` / `lcTableNameByBucket()` 生成的
   白名单表名，不能拼用户输入。`orderBy` / `timeField` / `dimension` 也必须走白名单映射到列名，
   不能透传。
4. **跨表分页**：`ListResources` 跨 16 张分表时用 `UNION ALL` 子查询 + 外层 `ORDER BY … LIMIT`，
   每个子查询各自带 WHERE 与 `LIMIT offset+limit+1` 以便下推；`bucket` 指定时只查那一张表。
   `scannedTables` 如实回填。`hasMore` 用"多取一条"判断，不依赖 total。
5. **时间字段**：DB 是 `datetime`、proto 是毫秒时间戳，转换沿用 `rpc_service.go` 的既有做法；
   注意 `last_check_at` 是可空列，NULL 要映射成 0。
6. **`TableDiagnostics` 的列/索引比对**：用 gorm `Migrator()` 或直接查 `information_schema.columns`
   / `statistics`，与 `ResLifecycleModel` 等 gorm 模型声明比对，输出缺列 / 多列 / 类型不符 / 缺索引。
   67 张表 = 64 分表 + `res_lc_cycle` + `res_lc_job` + `res_lc_event`，`kind` 字段据此填
   `shard` / `cycle` / `job` / `event`。
7. **`TableDiagnostics` 的 `reconciles`**：对 `res_lc_cycle` 登记的每个 index_name，DB 侧统计
   `status=1 且 index_name=该索引` 的行数（千万级上很贵——先评估 `CountByIndexName` 的代价，
   代价过高就改用估算并在 `note` 里说明口径），ES 侧取父文档数；取不到 ES 时填 `-1` 而非报错。

## 验证（全部通过才算完成）

```bash
cd /home/peterq/dev/projects/1s/osec-spider-go
go build ./...
go vet ./services/gateway/lifecycle/
go test ./services/gateway/lifecycle/ -count=1
```

新增单元测试至少覆盖：参数校验（type 为空 / offset 超限 / limit 夹取）、白名单映射
（非法 `orderBy` / `dimension` 被拒）、UNION ALL SQL 的拼装结果。

**不需要连生产数据库**；现有依赖真实 DB 的集成测试（`*_it_test.go`）不要跑也不要改。

## 交付

见 `00-shared.md` 第 5 节。额外汇报：每个 rpc 的代价评估，以及你为
`maxOffset` / 超时 / 估算口径选的**具体数值**与理由。
