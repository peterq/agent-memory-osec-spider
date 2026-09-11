# 91-verify-failed —— 校验取证 Agent（Opus）：作业 id=8 以 failed 终结后的只读取证与差额分类

> 先读 00-shared.md（硬性约束照旧）。本任务**全程只读**：不创建/retry/cancel 任何作业、不跑 repair、不改 DB、不改参数。
> 结论供主控与用户决策。

## 0. 已知终态（09-11 05:16）

- id=8 `state=failed step=verify progress=1.00`，错误：`res_short_202609 的 DB/ES 差额 0.107% > 0.1%`（DB 2,752,219 vs ES 父文档 2,749,262，差 2,957）。
- verify 在 cur 索引失败后**直接返回，res_long_2026 从未对拍**（`bootstrapVerify` 循环顺序 cur→long）。
- 别名已就绪：`res_lc_all` → res_long_2026 + res_short_202609 + res_short_202608；`res_lc_cur` → res_short_202609；`res_lc_long` → res_long_2026。B6 不切别名，只 `pollEsStats` + 排一次 repair。
- `retry` 会让 id=8 从 `verify` 步续跑（`bsStepBefore` 跳过 B0~B3c），通过后 done。
- repair 守卫：存在 `kind=bootstrap` 且 state∈{pending,running,paused} 就拦（id=4 paused 会拦；`-job-params '{"force":true}'` 可绕过）。repair 检查项 ②「DB 有 ES 无 → MarkDeleted(status=3)」在 `res_lc_all` 上 LocateIds。
- 终态快照：SPIDER `_note/r26-job8-final.json`（`grep -vE progressJson=` 看头部；progressJson 单行 2.2 MB 只能用 python 抽字段）。

## 1. 取证（写进报告）

- `scripts/lc_job_brief.sh 8 127.0.0.1:18085`、`go run ./tools/lc-check -addr 127.0.0.1:18085 -jobs`（确认无新作业、id=4 仍 paused）、`-params`（`enabled`/`dual_write_legacy` 仍 true）。
- ES：`_tasks?actions=*reindex*` 为 0；`_cat/nodes` heap；`_cluster/health`；breaker 与基线（fielddata 2 / parent 0）；`_cat/indices/res_short_2026*,res_long_2026`。
- 网关两容器 id（`93d1fb726816`/`600e1a8c2738`）、`docker logs --since 2h spider-gateway | grep -cE 'panic:|\[fatal\]'`。
- 守护状态文件：`running=false exit_reason='fatal: 作业 state=failed'`；`ss -ltnp | grep 1808` 现状。

## 2. res_long_2026 补对拍（verify 没做的那一半）

- 读 `services/gateway/lifecycle/dao.go` 的 `CountByIndexName` 拿到等价 SQL（按 `index_name` + active 状态计数，注意分表 `LcAllTables()`），经跳板 `osec-res1` 的 mysql 客户端执行**只读 SELECT**。
- MySQL 访问方式参照 `scripts/lc_rollback_repair_marked.sh` 第 103~160 行（DSN 现读、只在变量里用、经 osec-res1 内网直连）。**注意**：该脚本读的是 `_note/config/spider.gateway.prod.yaml`，现在本地只有 `_note/config/spider.prod.yaml`（v2 格式，`mysql:` 可能缩进在 `services.gateway` 下），需自行适配解析；**DSN 任何片段不得出现在输出/文件/报告里**。
- ES：`res_long_2026/_count` with `{"query":{"term":{"join":"resource"}}}`。
- 报告：DB 行数、ES 父文档数、差额与百分比、是否会在 retry 时通过（阈值：绝对差 ≤100 免检；否则 ≤0.1%）。

## 3. cur 差额 2,957 条的成因分类（抽样，必要时全量）

目的：区分「线上双写/生命周期删除造成的自然漂移」（repair MarkDeleted 是正确处理）与「copy_parent 漏搬」（MarkDeleted 会误伤，应 copyMode=ids 补搬）。

1. 从 DB 取 `index_name='res_short_202609'` 且 active 的 id（按 id 分页 `ListActiveIdsAfter` 同款 SQL，每批 ≤1000），先抽约 5%（均匀分页取样，不要 `ORDER BY RAND()`）。
2. 每批用 `res_lc_all/_search` 的 **`ids` 查询**（`{"query":{"ids":{"values":[...]}},"_source":false,"size":1000}`，禁止 terms 聚合/fielddata）找出 ES 无的 id。
3. 对 ES 无的 id 再查 legacy 源索引 `enfi_resource_v6_250822`（同样 `ids` 查询）：存在 → 疑似漏搬；不存在 → 线上已删。
4. 报告：抽样量、ES 无的条数与比例（外推到 2,957 是否吻合）、两类各占多少；若「疑似漏搬」>0，列 5 个样例 id 与其在 legacy 的 `ctime`/`index` 信息，并评估是否值得全量扫描（2.75M id / 1000 ≈ 2,752 次查询，估算耗时）。若时间允许且漏搬比例>0，直接做全量并给出完整 id 清单落到 `_note/r8-cur-missing-ids.txt`（不入 git）。

## 4. shortfallSlices 89 条汇总

- 用 python 从 `_note/r26-job8-final.json` 抽 `progressJson` 里的 `shortfallSlices`：条数、按窗口时间段分布、src/dst 合计与缺口占比、单窗最大缺口。
- 这些是子文档（file）短缺，与 §3 的父文档差额是两回事，分开报告。

## 5. 交付（≤900 字 + 数据表）

- 终态取证表；res_long_2026 对拍结果；cur 差额分类结果与结论（自然漂移 / 漏搬 / 混合）；shortfall 汇总。
- **恢复方案建议**（不执行）：例如「repair(force 或先处理 id=4) → 立即 retry id=8 → done → B6 自动排 repair」，说明每步风险与前置条件；列出**需用户决策**的项（id=4 取消 vs force；若有漏搬，先 copyMode=ids 再 repair；差额若持续增长 retry 的时间窗口）。
- 时间线按「日期 时:分 事件」逐行（供 rollout §12 引用）。可复用经验单列。
- 结束前 kill 自己的 18085 隧道（若被占用改 18086 并注明）。
