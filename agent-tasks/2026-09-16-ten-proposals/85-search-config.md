# 角色 85：搜索回归集与硬编码配置化（提案 12）

短名 `search-config`。worktree：`api-wt-search-config`（分支 `feat/search-config`）。只改 API。

## 目标

1. `controller/api.go`（v2，约 197 行）与 `controller/api_v3.go`（约 66 行）里写死的匿名限期 `"26/02/13-1000"`、`forbidden` 词表来源、`search_canary` 比例等硬编码改为配置（缺省值 = 现行为，线上不加配置行为不变）。匿名限期这条已过期失效，改成 `search.anonymous_deny_until`（空 = 不限制）。
2. `search_canary` 泛化为通用 feature flag：新包 `services/featureflag`，`Percent(name) int`/`Enabled(name) bool`，值来自配置 + redis 覆盖（`ff:<name>` 热更新，读失败回落配置），带本地缓存；`search_canary` 的 percent 读取改走它（保持原有自动调步逻辑不变，只替换「读当前比例」这一层；若耦合太深就只提供 flag 包 + 一处示例接入，汇报说明）。
3. 搜索回归集工具 `tools/search-regression`：读 `tools/search-regression/keywords.txt`（50 个关键词，从 `agent-memory/lessons/failure-v3首页重合度受前缀展开分片彩票影响.md` 与 SPIDER `PRD/res-lifecycle/` 的 P5 对拍材料里找已有的关键词清单；找不到就用 `_note`/测试里的样例凑，标注来源），对指定 base URL 跑 v2/v3 搜索，输出：每词首页 top15 重合度、P50/P99 延迟、total 差异；支持 `-snapshot <文件>` 保存基线与 `-compare <基线>` 对比，重合度低于阈值非零退出，可接进 CI（手动触发）。**默认 base URL 指本地，不得默认打生产**；请求节奏遵守 `agent-memory/lessons/failure-v3首页重合度受前缀展开分片彩票影响.md` 里的三级漏桶说明（每秒 ≤2）。
4. `forbidden` 词表：看 `services/forbidden/keyword.go` 的加载方式，若是硬编码路径/内嵌，改成配置项 + 热加载间隔可配。

## 必读

`controller/api.go` `SearchApi`、`controller/api_v3.go` `SearchApiV3`、`config/config.go`（`SearchCanaryConfig`/`SearchGuardConfig`/`SearchConfig`/`SwitchConfig` 的写法与缺省值机制）、`services/search-canary/`、`services/search-guard/`、`services/forbidden/`；`agent-memory/knowledge/architecture-api.md`。

## 文件所有权

API：`controller/api.go`、`controller/api_v3.go`（只改硬编码相关行；**不动** `ValidShareLink*` 与 `services/valid`）、`config/config.go`（只加字段）、`services/featureflag/**`、`services/search-canary/`（只改读取比例那一层）、`services/forbidden/`、`tools/search-regression/**`、`README.md` 一节。

## 验证

`go build ./...`；`go vet`/`go test ./services/featureflag/... ./services/search-canary/... ./services/forbidden/... ./controller/...`；工具用 `httptest` 假服务跑一遍 snapshot/compare。

## 交付

分支/提交、新增配置项表（键、缺省值、含义）、flag 包用法、工具用法与样例输出、keywords.txt 来源说明。
