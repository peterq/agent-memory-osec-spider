# 80-code-fixes —— bootstrap 三处缺陷修复（Sonnet，只改代码+单测，不部署、不连生产）

先读 00-shared.md §2 硬性约束，再读 COMMON `agent-memory/lessons/failure-longBoundary漂移导致父子跨索引与shortfall误报.md`（成因）。
仓库 SPIDER `/home/peterq/dev/projects/1s/osec-spider-go`，文件 `services/gateway/lifecycle/bootstrap.go`（及 dao.go/README）。
注意：另一个 Agent 正在用生产网关，**不要部署、不要重启网关、不要连生产**；仓库里有用户未提交的 `.vscode/launch.json`，不要碰。

## 修复 1：`longBoundary` 固化进 progress，全作业复用

- 现状：`bootstrapCopyParents`（约 819 行）与 `bootstrapCopyChildrenByWindow`（约 1115 行）各自 `time.Now().AddDate(0,0,-s.conf.LongThresholdDays)`，长跑作业两阶段边界不一致。
- 改法：在 `JobProgress` 增加 `LongBoundary string json:"longBoundary,omitempty"`（ISO 时间）。第一次需要边界时（copy_parent 之前，或更早在 B1 建库时若 B1 也用它分流——请核实 `bootstrapRowOf`/B1 是否也按 boundary 决定 `IndexName/IndexRole`，若是则在 B1 起点就固化）计算并 `setProgress` 落库；之后所有阶段（B1/copy_parent/copy_child/verify）统一读 `prog.LongBoundary`，为空才现算并写回（兼容旧作业断点）。
- 日志里打印一次「本作业 longBoundary=…」。
- 单测：模拟 progress 已有 LongBoundary 时各阶段取到同一值；为空时现算并写回。

## 修复 2：shortfall 记账区分「子没搬」与「父不在本索引」

- 现状：`ChildShortfall{key,src,dst,rerun}` 的 `dst` 用 `has_parent` 口径（`verifyChildWindow` 约 1410 行），父不在目标索引时 dst=0 误报。
- 改法：在 `ChildShortfall` 增加 `dstByParentId int64 json:"dstByParentId,omitempty"`（目标索引按 `parent_id` 口径的子文档计数，不依赖父在本索引）与 `missingParents int64 json:"missingParents,omitempty"`（窗口内应在目标索引却缺失的父数，可用 DB 该窗口 active 行 vs 目标索引 `ids`/`_count` 差值，或至少给出 `has_parent` 与 `parent_id` 两口径差）。
  Warn 日志与 `progress.extra` 同步补这两个数；README「结构性短缺」一段补充两口径含义与判读（`dst<dstByParentId` ⇒ 父不在本索引，走 mover 归位而非补搬）。
- 单测：补一例 `has_parent`=0、`parent_id`=N 的判读。

## 修复 3：`bootstrapCopyChildrenByIds` 尊重 `ctimeFrom/ctimeTo`

- 现状：`dao.ListIdsByIndex`（dao.go 约 663 行）SQL 只有 `index_name=? AND status=1`，`copyMode=ids` 会退化全量。
- 改法：给 `ListIdsByIndex` 增加可选 ctime 范围参数（沿用 bootstrap 其他 SQL 的 ctime 列与格式），`bootstrapCopyChildrenByIds` 传入 `p.CtimeFrom/CtimeTo`；两者都空时行为不变。
  README `copyMode` 一行改为「按父 id 分批，受 ctimeFrom/ctimeTo 限定，仅供小范围修补」；`validateBootstrapParams` 里 `copyMode=ids` 且未给 ctime 范围时**拒绝**（返回明确错误），避免误跑全量。
- 单测：SQL 构造含/不含范围两例；validate 拒绝一例。

## 验证与提交

- `go build ./...`、`go vet ./services/gateway/lifecycle/...`、`go test ./services/gateway/lifecycle/...`（集成测试靠环境变量自动 skip）。
- 三处可分三个 commit（中文信息，例如 `fix(res-lifecycle): longBoundary 固化进 progress 全作业复用`），只 `git add` 改动的 go/README 文件，`git pull --rebase --autostash` 后 push master。
- 若某项发现设计上需要主控决定（例如 B1 分流也依赖 boundary 导致改动面扩大），先完成其余两项并在交付里说明。

## 交付

每项：改动摘要（文件:行）、单测名与结果、commit hash；未完成项与原因。
