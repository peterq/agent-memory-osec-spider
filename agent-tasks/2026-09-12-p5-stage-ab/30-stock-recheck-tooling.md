# 角色 30：SPIDER —— 阶段 A' 存量提前复检的工具链（只做工具，不跑生产写操作）

## 目标
D1 钩子（已合入 SPIDER `950b11a`）只解决增量。bootstrap 迁入的存量里，已被旧链路从 `resource` 删掉但 lc 分表仍 `status=1` 的行
（首页样本 31/750 ≈ 4%，全量估 ≈170 万）需要一次性找出来、分批提前复检。本角色交付**两个可复用工具**并做**小样本验证**，
不做全量、不发起任何生产写操作（`TriggerCheck` 只跑 `-dry-run`）。

## 必读
1. `tools/lc-check/main.go` —— 尤其 `-trigger-move` 的实现（L138-215）：读 id 文件、去重、分批、dry-run、审计 operator。**照它的形态加 `-trigger-check`**。
2. COMMON `rpc/spider/lifecycle_rpc/lifecycle.proto` L31 与 L217-221 —— `TriggerCheck(TriggerCheckParam{ids ≤200, operator, force})` 已存在，**不改 proto**。
3. `services/gateway/lifecycle/rpc_service.go` 里 `TriggerCheck` 的服务端实现 —— 看 force 语义、批上限、是否写事件；工具的提示文字要与之一致。
4. `scripts/lc_mysql_ro.sh`、`scripts/lc_es_ids_probe.sh` 顶部注释 —— 只读 DB/ES 的既定方式，新脚本**复用它们**，不要自己拼凭据。
5. `services/gateway/lifecycle/dao.go` L14-80 —— 分表命名 `res_lc_<bnd|ali|quark|xunlei>_<00..15>`，id 是 md5，`status`/`next_check_at` 列。
6. `PRD/res-lifecycle/p5-plan-2026-09-12.md` §2.4。
7. `scripts/README.md`（若存在）或同目录脚本头部注释风格 —— 新脚本头部注释要同样完整（用途/用法/只读声明/退出码）。

## 交付物
### (1) `tools/lc-check -trigger-check`
- 新 flag：`-trigger-check <idfile>`、`-check-force`（缺省 true，本场景就是要忽略 next_check_at）、`-check-batch`（≤200）、`-check-sleep-ms`、`-check-dry-run`；复用 `-operator`。
- 行为与 `-trigger-move` 对齐：读文件去重保序 → 分批调 `TriggerCheck` → 汇总成功/失败批数；dry-run 不连网关。
- 顶部用法注释加一行示例。

### (2) `scripts/lc_legacy_deleted_probe.sh <type: bnd|ali|quark|xunlei> <bucket: 0-15> [limit 缺省 20000] [afterId 缺省空]`
- 用 `lc_mysql_ro.sh` 取 `res_lc_<t>_<NN>` 里 `status=1 AND id > '<afterId>' ORDER BY id LIMIT <limit>` 的 id（**只 SELECT id**）；
- 交给 `lc_es_ids_probe.sh <ids> resource` 找出旧索引 `resource` 里不存在的 id → 输出到 stdout（每行一个 id），stderr 打印 `scanned=<n> missing=<m> lastId=<...>`（lastId 用于下一页续跑）；
- 注意 `resource` 是旧索引名（API v2 用的 `EnfiResourceIndex`），先用 `scripts/es_curl.sh '_cat/aliases?h=alias,index' ` 或 `_cat/indices/resource*` 确认它是别名还是索引（1 次请求），把确认结果写进脚本注释。
- bnd 特殊：旧索引里 `shareId` 长度 ≤8 的百度短链可能以 `LegacyBndShareLinkFromId` 的另一个 md5 存在（见 `res_scheduler/clear_expire.go` HandleTask 开头）。probe 阶段**不处理**这点（提前复检是无害的，多检一次而已），但要在脚本注释里写明这个假阳性来源。

### (3) 小样本验证（只读 + dry-run）
- 跑 `scripts/lc_legacy_deleted_probe.sh quark 0 2000` 与 `bnd 0 2000`，把 `scanned/missing` 与缺失率写进汇报；ES 请求 ≤10 次。
- 对产出的 id 文件跑 `go run ./tools/lc-check -trigger-check <file> -check-dry-run`，贴输出。
- **不要**不带 dry-run 调 `TriggerCheck`；**不要**跑 16 个桶或全类型。

### (4) 文档
- `services/gateway/lifecycle/README.md`「旧链路失效同步钩子」一节末尾补「存量提前复检」小节：两条命令、建议节奏（每天 ≤20 万、每批 200、`-check-sleep-ms 500`）、如何续跑（afterId）、观察什么（lcCheck 队列 waiting、`res_lc_legacy_hint_total` 不涵盖此路径——它走 TriggerCheck 事件 `manual_check`）。

## 验证
```bash
cd /home/peterq/dev/projects/1s/osec-spider-go && go build ./... && go vet ./tools/lc-check/... && bash -n scripts/lc_legacy_deleted_probe.sh
```
commit 前缀 `feat(lc-check)` / `scripts(lc_legacy_deleted_probe)`，只 add 自己的文件；push。

## 交付
按 00-shared.md 格式。额外：两桶样本的缺失率、`resource` 是别名还是索引、dry-run 输出摘要。
