# 30-recover —— 恢复执行 Agent（Opus）：cancel id=4 → repair → 复核 → retry id=8 → done

> 先读 00-shared.md（硬性约束）与 91-verify-failed.md §0（背景）。本任务**会写生产**（作业控制、repair 会改 DB/ES），
> 一步一核验、失败即停并报告，不越过本文列出的动作范围。

## 0. 用户决策（2026-09-11 已确认）

1. **cancel 作业 id=4**（paused 的旧 bootstrap，用于解除 repair 守卫）。
2. repair **白天也可以跑**（不必等低峰），但仍须盯 heap / v2 组 1 中位 / breaker。
3. repair 参数 `skipEsToDb=false`（保留检查项 ①），其余缺省（`batch` 1000、`maxDocs` 200000 只限 ①）。**不要用 `force`**（id=4 取消后守卫自然放行）。
4. shortfallSlices（89 条，2026-06 整窗 dst=0）**不在本任务处理**，done 之后另行排作业。

## 1. 执行步骤（每步都有核验，核验不过就停）

用独立隧道 18085（建法见 00-shared §3）。lc-check 命令一律 `go run ./tools/lc-check -addr 127.0.0.1:18085 …`。

**S1 前置核对**：`-jobs` 确认只有 id=8 failed、id=4 paused、无 running/pending；`_tasks?actions=*reindex*` 为 0；集群 green；
`-params` 的 `enabled=true`、`dual_write_legacy=true`。

**S2 cancel id=4**：`-control-job 4 -action cancel -operator p4-recover`。核验：`-jobs` 里 id=4 `state=canceled`；
`_tasks` 无新 reindex（id=4 的 `es_task_id` 早已不存在，cancel 只落状态）。

**S3 创建 repair**：`-create-job repair -operator p4-recover -job-params '{"skipEsToDb":false}'`。记下新作业 id（记为 R）。
核验：15~30 秒内 R 变为 `running`（`pollOnce` 15 秒一轮）；若 R 变成 `paused` 且 `progress.message` 提到 bootstrap 守卫，说明 id=4 取消未生效或还有别的 active bootstrap——**停下报告，不要用 force**。

**S4 盯 repair 直到 done**（预计 1.5~4 h；① 最多 20 万条 ES→DB，②③④ 全量 64 表 43.7M 行）：
- 每 10 分钟：`-jobs` 看 R 的 state/progress/updatedAt；`scripts/lc_job_brief.sh R 127.0.0.1:18085` 只看摘要行；
  `_cat/nodes` heap；`_tasks?actions=*delete/byquery*` 数量（④ 会对 long 发子文档删除，短命属正常）。
- 每 30 分钟：`scripts/v2_search_latency.sh osec-res2 1`（组 1 中位）、breaker、`docker logs --since 30m spider-gateway | grep -cE 'panic:|\[fatal\]'`。
- **介入条款**：v2 组 1 中位 >1,100 ms 连续 3 次（间隔 ≥10 分钟）或集群非 green 或 breaker 增长 → `-control-job R -action pause`，报告并等主控；
  R 变 `failed` → 立即报告 `error`，不 retry。
- 进度口径：repair 的 progress 字段含义读 `repair.go` 的 `setProgress` 调用后自行解读；`updatedAt` 每批推进。
- 前台等待用 `T=$(( $(date +%s)+480 )); until [ $(date +%s) -ge $T ]; do sleep 20; done`。

**S5 只读复核两索引差额**（R done 后）：
- DB：`scripts/lc_mysql_ro.sh` 执行与 `dao.go` `CountByIndexName` 等价的 SQL（按 `index_name` + active 状态跨 64 表求和），分别对 `res_short_202609`、`res_long_2026`。
- ES：`scripts/es_curl.sh '<索引>/_count' -H 'Content-Type: application/json' -d '{"query":{"term":{"join":"resource"}}}'`。
- 判定与 `bootstrapVerify` 同口径：绝对差 ≤100 免检，否则差额/DB ≤0.1%。两索引都过才进 S6；否则报告数字并停。
- 同时记 R 的终态：`dbToEsFixed`/`esToDbFixed`/`dupCleaned` 等计数（在 progress/extra 里）。

**S6 retry id=8**：`-control-job 8 -action retry -operator p4-recover`。核验：state `pending`→`running`，step 停在 `verify` 后很快 `finish`→`done`
（B0~B3c 被 `bsStepBefore` 跳过，verify 秒级）。若再次 `failed`，报告 `error` 里的数字，不再 retry。
done 后 B6 会自动排一个 repair（落库 operator=`system`，`bootstrap-8` 只是 redis 幂等键——执行后更正）——**属设计行为，不取消**，记录其 id 并观察其起跑（同样受 S4 的介入条款保护，但本任务不必等它跑完，观察 30 分钟无异常即可收尾）。

**S7 收尾**：`-jobs` 终态截图式记录；`_tasks` 归零；隧道 18085 kill 并核对 `ss -ltnp | grep 1808`。
发邮件：`notify-admin.sh "[P4] id=8 恢复完成: repair R + retry → done" "<精简 html>" lifecycle-deploy`。

## 2. 交付（≤700 字）

- 时间线（日期 时:分 事件），含 S2~S6 每步的核验结果。
- repair R：起止、耗时、三类修复计数、期间 heap 区间 / v2 中位区间 / breaker / 是否介入。
- 复核数字表（两索引 DB/ES/差额/比例/判定）。
- id=8 终态（state/step/finishedAt）与 B6 排出的 repair id 及其状态。
- 异常与可复用经验单列。
