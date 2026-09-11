# 70-move-shortfall —— 用 mover 让 shortfall 相关父归位（Opus，写生产）

> 先读 00-shared.md（硬性约束）与 COMMON `agent-memory/lessons/failure-longBoundary漂移导致父子跨索引与shortfall误报.md`（成因与修法）。
> 用户决策（09-11）：入口用 lc-check `-trigger-move`；**只修 shortfall 相关父**；放宽 move 参数。禁用任何 bootstrap 作业 / `copyMode=ids`。

## 0. 现场前提（执行前逐项核对）

- `-jobs`：repair id=11 已 `done`，无 running/pending 作业（任何 bootstrap 出现都要停下报告）。
- `-params`：`enabled=true`、`dual_write_legacy=true`；当前 `move_interval_sec=300`、`move_batch=200`、`move_requests_per_second=3000`、`move_verify=true`。
- 集群 green、`_tasks?actions=*reindex*` 为 0。网关 leader 在 res2（mover 只在 leader 跑）。
- lc-check 已含 `-trigger-move`（主控确认后才派本任务；`go run ./tools/lc-check -h` 应能看到该 flag）。

## 1. 枚举目标父 id（只读，**只走 DB + cur 索引**；09-11 第一次执行因在 legacy 上跑 has_child 触发节点重启，已改口径）

1. `go run ./tools/lc-check -addr 127.0.0.1:18085 -job 8 > _note/job8-final-done.json`（已存在可复用；2.2 MB，**只用 python 抽字段**）：
   取 `progressJson.shortfallSlices[].key` 里 **87 条 `:long`** 窗口的前缀（如 `t202606100000`），在 `progressJson.windows.join[]` 找到各窗口 ctime 起止，合并成区间列表（上次结果 24 段，见 `_note/mv-windows.json`）。
2. **DB 枚举**（`scripts/lc_mysql_ro.sh`，只查 join 型三类表 `res_lc_{ali,quark,xunlei}_00..15`，bnd 型没有 join 子文档不查）：
   每表 `SELECT id FROM <表> WHERE index_name='res_short_202609' AND status=1 AND file_count>0 AND utime < '<边界>' AND (ctime BETWEEN … OR …) LIMIT 50000`，
   边界取 `now-90d`（执行当天 00:00，格式与列一致，先 `SHOW COLUMNS` 确认 ctime/utime 列名与类型）。汇总去重到 `_note/move-shortfall-ids.txt`。
   **不做任何 ES 端 has_child/has_parent/聚合验证**。
3. 规模判据：**主控 09-11 18:40 已裁定放行全量 102,601**（`_note/move-shortfall-ids.txt`，第二次执行已枚举并抽样核验通过，file_count 合计 470 万与缺口 418 万吻合）。本次直接复用该文件，不重新枚举；若文件不存在或行数偏离 102,601 ±5% 才重跑 §1.2。
4. 抽样核验（白名单查询）：随机 30 个 id → `scripts/lc_es_ids_probe.sh` 确认在 `res_short_202609` 存在、在 `res_long_2026` 不存在；其中 10 个用 `parent_id` 查询（routing=该 id）`_count` 在 `res_long_2026` 的子文档数 >0（证明「父在 cur、子在 long」）。若 10 个里 ≥3 个子文档为 0，停下报告。
5. 2 条 `:cur` 半区窗口（`t202608290000`/`t202608310000`，合计 21,451）本轮**跳过**，在交付里注明。
6. 报告枚举结果：总 id 数、按表类型分布、按月份分布、前 5 个 id。

## 2. 放宽参数（主控已定值）

`go run ./tools/lc-check -addr 127.0.0.1:18085 -update move_interval_sec=30`（主控定 30：mover 每轮 runOnce 串行不重叠，≈24,000 父/h，全量 ≈4.5 h；`move_batch` 保持 200、`move_requests_per_second` 保持 3000）。
核验 `-params` 生效。**结束时必须改回 300**（§5）。

## 3. 试点一批

`go run ./tools/lc-check -addr 127.0.0.1:18085 -trigger-move _note/move-shortfall-ids.txt -move-target long -move-batch 200 -move-dry-run` 看批数；
然后先只投递**前 200 个 id**（切一个小文件）。等 ≥2 个 mover 周期（约 2~3 分钟），做三查核验（各抽 20 个父）：
- `scripts/lc_es_ids_probe.sh <ids> res_long_2026` 应全部存在、`res_short_202609` 应全部不存在；
- `parent_id`（routing=父 id）查询 `_count` 在 long 与 legacy 一致（**不用 `has_parent`**，白名单外）；
- `scripts/lc_mysql_ro.sh` 查这些 id 的 `index_name` 已是 `res_long_2026`、`status=1`。
- 网关 res2 `docker logs --since 10m spider-gateway | grep -E "mover|搬迁" | grep -ciE "error|失败|不通过"` 为 0。
试点不达标 → 停下报告，**不继续投递**。

## 4. 全量投递与盯盘

- `-trigger-move` 全部剩余 id（约 512 批），`-move-sleep-ms 500`。投递只是入 redis set，消费由 mover 决定（30 s/批 × 200 父 ≈ 24,000 父/h，10 万父 ≈ 4.5 h；含超大父的批更久）。
- **本轮可能盯不到结束**：单轮约 4.5 h 前台等待；若本轮结束时仍未搬完，交付里写清剩余量（DB COUNT 口径）与当时集群状态，**不要改回参数**（由下一轮收尾），主控会再派一轮盯盘。
- 每 10 分钟：`_tasks?actions=*reindex*`/`*delete/byquery*` 数、`_cat/nodes` heap、集群健康；剩余量用 DB 复查（§1.2 同款 SELECT COUNT(*)）或网关 res2 日志里 mover 的批次日志估算，**不要在 ES 上估**。
- 每 30 分钟：`scripts/v2_search_latency.sh osec-res2 1`（组 1 中位；>1,100 ms 连续 3 次间隔 ≥10 分钟 → 报告并等主控，不自行改参数）、breaker、网关 panic 计数。
- 一批失败会被 mover 记日志并放弃（成员已 SPOP），最后用 §1.2 的查询复查残留 id，残留再投一次；仍残留列出交主控。
- 前台等待 `T=$(( $(date +%s)+480 )); until [ $(date +%s) -ge $T ]; do sleep 20; done`。

## 5. 收尾

- 第 2 轮（收尾轮）流程：先用 §1.2 的 DB `SELECT COUNT(*)`（同口径）看剩余；剩余 >0 且 10 分钟不再下降 → 用 §1.2 SELECT 重新导出残留 id 到 `_note/mv/residual.txt` 复投一次（最多两次）；仍不动的列出交主控。
- 仅当 DB COUNT 口径剩余 ≈0（或残留已复投两次仍不动）时：`-update move_interval_sec=300`，`-params` 核验恢复。
- 终态复核：§1.2 的 DB SELECT COUNT 合计（应 ≈0）；随机 50 个已搬父三查（ids probe 在 long / 不在 cur、DB index_name=long、10 个 parent_id 计数 >0）；`res_short_202609`/`res_long_2026` 父文档 `_count`（term join=resource，白名单内）与 DB 对拍，差额应仍 <0.1%。
- `_tasks` 归零；kill 18085；邮件 `[P4] shortfall 父归位完成`（精简）。

## 6. 交付（≤700 字 + 表）

时间线；枚举数；试点核验；全量投递批数/失败批；mover 耗时与速率；期间 heap/v2/breaker；终态复核数字；残留与建议；可复用经验。
