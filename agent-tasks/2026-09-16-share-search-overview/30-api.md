# 角色 30：API —— 搜索接口的匿名搜索防护开关

仓库：`/home/peterq/dev/projects/1s/osec-resource-api`（分支 `feat/search-guard`）。改动很小，但两条搜索入口都要覆盖。

## 必读

1. `00-shared.md` §4.1（日志字段）、§4.2（redis 键约定）、§5。
2. `controller/api.go` `SearchApi`（约 150~240 行）与 `controller/api_v3.go` `SearchApiV3`：现有 `uid == "anonymous" && 日期 < 26/02/13` 的写死拦截已过期失效（保留不动，与本任务无关）；`logData` 的组装与 `defer` 里的日志写法。
3. `config/config.go` 的 `SearchCanaryConfig`（配置节 + `Defaults` 的写法）与 `services/search-canary/canary.go`（redis 用法、`config.GetRedis()`）。
4. `api-starter.go` 里 `service.canary` 的注入方式（`controller.NewEnfiResourceApi` 附近）。

## 要做的事

1. 配置节 `search_guard`（`config/config.go`，全部有缺省值，线上不加配置也生效）：
   ```yaml
   search_guard:
     enabled: true                          # false = 完全不查 redis
     key: search_guard:anonymous_closed     # 与网关约定一致, 一般不改
     cache_ms: 1000                         # 本地缓存, 避免每个请求都 GET
   ```
2. 新包 `services/search-guard/guard.go`：
   - `New(rds redis.Cmdable, conf *config.SearchGuardConfig) *Guard`；`Closed(ctx) (closed bool, info ClosedInfo)`：`GET key`，存在即关闭并解析 JSON（`reason/by/closedAtMs/untilMs`）；结果本地缓存 `cache_ms`（`sync/atomic` 或 mutex）；**redis 出错 fail-open**（返回 false，`WithStage("guard.redis").Error` 限频记录，例如每 30s 一次）。
   - 单测用 `github.com/alicebob/miniredis/v2`（`go.mod` 已有 indirect，改为直接依赖即可）：键存在/不存在/JSON 损坏/redis 关闭四种情况 + 缓存生效。
3. 在 `SearchApi` 与 `SearchApiV3` 里，`logData` 组装完、`forbidden.Keyword` 之前加：
   ```go
   if uid == "anonymous" && s.guard.Closed(ctx) {
       logData["guard"] = "anonymous_closed"
       ctx.JSON(http.StatusForbidden, &util.Response{Code: 50008, Msg: "请登陆后再搜索", Data: "请登陆后再搜索"})
       return
   }
   ```
   注意 `SearchApi` 里 `backend` 仍为空，defer 不会把这次计入 canary 统计（现有注释已说明早退路径的处理，保持一致）。响应码/文案与现有匿名拦截完全一致，客户端不需要改。
4. 注入：`NewEnfiResourceApi` 增加 `guard` 字段与参数（或 setter），`api-starter.go` 构造时传入 `search_guard.New(config.GetRedis(), config.Config.SearchGuard)`；`SearchGuard` 为 nil 时用缺省值。
5. `go build ./... && go vet ./controller/... ./services/search-guard/... && go test ./services/search-guard/... ./services/search-canary/...`。
6. 在 `services/search-guard/README.md` 写 10 行以内说明：键约定、fail-open、如何手动关闭/开放（`redis-cli SET/DEL`，仅作应急，正常走后台页面）。

## 交付（最终回复里写）
- 改动文件清单 + 提交哈希（分支 `feat/search-guard`，不 push）。
- 测试结果。
- 对约定的疑问（如有）。
