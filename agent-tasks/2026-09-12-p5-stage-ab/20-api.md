# 角色 20：API —— (a) v2 validShareLink 失效上报 lc；(b) bnd 慢查询归因与 `search_v3.go` 修法

两件事都在 API 仓库，按 (b) 归因 → (a) 编码 → (b) 编码 → 测试 → 一次或两次 commit 的顺序做。
(b) 的归因是**只读生产 ES**，必须先做，结论决定 (b) 是否改代码。

## (b) bnd 慢查询归因（只读）

### 必读
1. `services/search/search_v3.go` 全文（≈300 行）—— 尤其 `childMatch := elastic.NewHasChildQuery("file", …)` 与 `resType` 处理；注释第 3 条就是当初保留 `has_child` 的理由。
2. `services/search/search.go` 只看 SearchV2 里 DSL 结构对照（**不改它**）。
3. SPIDER `PRD/res-lifecycle/rollout-2026-09-05.md` §13.2/§13.3（`grep -n "^### 13" 定位`）与 `p5-precheck-2026-09-12.md` §3 表格：baidu 关键词、v2/v3 `took`。
4. SPIDER `PRD/res-lifecycle/p5-plan-2026-09-12.md` §3。
5. SPIDER `scripts/es_curl.sh` 顶部注释 —— 经跳板机只读访问生产 ES 的唯一方式（凭据自动打码）。用法：
   `cd /home/peterq/dev/projects/1s/osec-spider-go && scripts/es_curl.sh 'res_lc_all/_search' -H 'Content-Type: application/json' -d @/path/body.json`
   请求体写到 `/tmp/claude-1000/`下的会话 scratchpad 或 `/tmp` 文件再 `-d @file`（避免 shell 转义）。

### 做法
- 从 `p5-precheck-2026-09-12.md` §3 选 5 个 baidu 关键词：3 个 `match` 大 total 的（如 `英语 洪晓燕`、`爱 你电视`、`传奇 暗黑 …`）+ 2 个 `precise` 的（如 `凡人`、`星球大战`）。
- 用 `SearchV3` 的 DSL 手工还原请求体（`resType=baidu`、`join=resource` must、function_score gauss ctime、`size=15`），对 `res_lc_all` 各跑 3 次取 `took` 中位：
  ① 原样；② 去掉 `has_child` should 子句；③ 原样 + `"profile": true`（只跑 1 次，看时间落在哪个 query 组件）。
  再对旧索引 `resource`（SearchV2 的 DSL，注意 v2 的 type 字段名/`.keyword` 差异，看 `search.go`）跑 ① 作对照。
- **总请求 ≤ 40 次**，请求之间 `sleep 2`；任何一次 took > 10 s 就停下换更小的 size。只读，不写。
- 把结果写成 `PRD/res-lifecycle/p5-bnd-profile-2026-09-12.md`（SPIDER 仓库，中文，表格：关键词 | v2 took | v3 原样 | v3 去 has_child | profile 最大耗时组件），结论一句话：假设成立/不成立。

### 判定
- 去掉 `has_child` 后 bnd `took` 回到旧索引量级（≤1.5×）→ **假设成立**，做下面的代码改动。
- 否则 → 不改 `search_v3.go`，把 profile 指向的组件（`join` 全局序数 / `nested filelist` / `function_score`）写进报告，附 `_stats/fielddata` 与 `res_lc_all` 各索引 mapping 里 `join` 字段 `eager_global_ordinals` 的值，交主控决策。

### 代码改动（仅假设成立时）
- `search_v3.go`：`resType == "baidu"` 时 `shouldQuery` 不含 `childMatch`（`precise` 与 `match` 两条路径都要处理）；`resType=all` 与其余类型保留。
- 先确认那 948 条 join 型百度父文档是否也带 nested `filelist`（`es_curl.sh` 在 `res_lc_all` 查 `type=baidu AND join=resource AND has_child(file)` 取 3 条看 `_source.filelist` 是否非空；≤3 次请求）。若**不带**，报告里注明"去 has_child 后这 948 条只能靠父 filename 命中"，仍然改，但写进风险。
- 顶部函数注释第 3 条要同步改写（说明按 resType 分派的理由，引用 profile 报告路径）。
- `SearchV1V3` 若也带 `has_child` 且能按 resType 判断，同样处理；不能判断（v1 无 resType）则不动并注明。
- 单测：`search_v3_test.go` 已有的 DSL 断言风格下加 case：`resType=baidu` 的 Source() 不含 `has_child`；`resType=quark`/`all` 含。

## (a) v2 `validShareLink` 失效 → 上报 lc

### 必读
1. `services/valid/valid.go` L90-160 —— `checkValid` 判失效后 `go s.deleteInvalid(...)` 直删旧索引。
2. `services/valid/valid_v3.go` L110-165 —— v3 的 `deleteInvalid` 已经调用 `s.lcRpc.ReportInvalid(...)`，**照这个写法**。
3. `services/remoteservice/service.go` —— `GetLifecycleRpcClient()` 已存在。
4. `api-starter.go` L195-215 —— `NewValidService(...)` 的构造点。
5. SPIDER `services/gateway/lifecycle/rpc_service.go` L731-775 —— 网关 `ReportInvalid` 的处理：会 push lcClear，lcClear 会删 lc 索引、写 invalid_link、`MarkInvalid`、再 push 旧 clearExpire；lifecycle 未启用返回 `ErrNotEnabled`。

### 主控裁定（与 p5-plan §2.1 末段的措辞不同，以本节为准）
API 侧判失效用的 `bndApi/quarkApi/xunleiApi/aliValid` **与 v3 valid 是同一套实现**，v3 已经用 `ReportInvalid` 直接让 lc 置失效，
所以 v2 路径也直接调 `ReportInvalid`，不需要新 RPC、不需要 API 接 redis 队列：
- `validService` 增加 `lcRpc lifecycle_rpc.LifecycleRpcClient`（构造函数加参数，`api-starter.go` 传 `remoteservice.GetLifecycleRpcClient()`；为 nil 时跳过上报）。
- `deleteInvalid` 成功删旧索引后追加：
  `ReportInvalid(Items: [{Id: id, Type: typ, ShareId: shareId, Source: "api-v2-search", DetectedAtMs: now, EsAlreadyDeleted: false}])`
  —— `EsAlreadyDeleted=false`：v2 只删了旧索引，lc 索引要由网关删。
- 失败只记日志（沿用 v3 写法），`ErrNotEnabled`/连接错误都不能影响 `checkValid` 返回值；日志级别 warn，不要 error 刷屏。
- 单测：用 fake `LifecycleRpcClient` 断言被调用一次且字段正确；nil client 不 panic。看 `valid_v3_test.go`（若有）怎么 mock。

## 验证

```bash
cd /home/peterq/dev/projects/1s/osec-resource-api && go build ./... && go vet ./services/... && go test ./services/search/... ./services/valid/... -count=1
```
有依赖外部环境失败的用例，贴原文并说明与本次改动无关。

## 交付

按 00-shared.md 交付格式。额外：profile 报告路径与一句话结论；(b) 是否改了代码；(a) 的 Source 字面量。
