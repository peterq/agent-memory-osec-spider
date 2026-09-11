# 90-verify —— 完成校验 Agent（Opus）：作业 id=8 done 之后

> 前提：巡检 Agent 报告 id=8 `state=done`（或 `failed`，此时只做取证不做修复）。先读 00-shared.md。

## 1. 取证（只读，全部数字进报告）

- `scripts/lc_job_brief.sh 8 127.0.0.1:18085`：`state/step/finishedAt`、slices 前缀计数（child 应 1620/1620）、
  `failedSlices / childVerifyFail / childShortfall / shortfallSlices` 终值。
- `go run ./tools/lc-check -addr 127.0.0.1:18085 -jobs`：确认作业自带的 B5 对拍（父文档）已跑且无新的 running/pending 作业；
  若自动产生了 repair 作业，记录其 id/state/结果，不要手工 retry。
- 目标索引终态：`res_long_2026`/`res_short_202609` 的 `join=resource` 与 `join=file` `_count`；源索引 `join=file` `_count`（12.00 亿口径）；
  两者差额与 `shortfallSlices` 总短缺量对比（README「结构性短缺」定义）。
- ES：`_tasks?actions=*reindex*` 应为 0；`_cat/nodes` heap 应回落到空载锯齿（85~93 属该集群空载基线，见 patterns #17）；
  `_cluster/health` green；breaker 与基线一致。
- 守护：状态文件 `running`、`exit_reason`、`pause_count`、`heap_brake.count`；作业 done 后守护可由主控决定停掉（**你不要停**）。
- 网关：两台容器 id 未变、`docker logs --since 1h` 无 panic；热更新参数 `enabled=true`/`dual_write_legacy=true` 未变。

## 2. 短缺对账（只读或幂等）

- 解析 `progress.shortfallSlices`（用 `go run ./tools/lc-check -addr 127.0.0.1:18085 -job 8` 输出，**只用 python 抽取该字段，不要打印全文**）：
  条数、涉及窗口时间段、每条的源/目标计数差与占比。
- 抽 3~5 条短缺窗口，按 `services/gateway/lifecycle/README.md` 的 `copyMode=ids` 说明做一次抽查（若 README 说明抽查需要创建作业，
  用 `-create-job`，operator 写 `p4-verify`，参数最小化；不确定就**只报告不执行**）。
- 是否需要跑一次新 repair 对账：读 README「repair」一节与 `decisions/`、`lessons/failure-repair误标*`，
  确认互斥判据不会命中 id=4（patterns #41）；**执行前必须把方案发给主控确认**（用最终报告的「待主控决定」列出），不得自行发起。

## 3. 交付

- 报告 ≤800 字：终态数字表（起止时间、总时长、父/子文档终值、短缺条数与量、四计数终值）、健康核对结论、抽查结果、
  待主控决定事项、可复用经验。
- 报告里的数据将由主控写入 rollout `PRD/res-lifecycle/rollout-2026-09-05.md` `## 12. 全量 bootstrap 实测`，
  所以时间线请按「日期 时:分 事件」逐行给出，方便直接引用。
- 结束前 kill 自己的 18085 隧道（若与巡检 Agent 共用端口冲突，改用 18086 并在报告注明）。
