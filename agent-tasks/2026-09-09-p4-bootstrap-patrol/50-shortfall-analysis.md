# 50-shortfall-analysis —— shortfallSlices 补搬前的只读分析（Opus，全程只读）

先读 00-shared.md §2 硬性约束。**只读**：不创建/控制任何作业、不改 DB/ES。当前 repair `id=11`（operator=system）可能仍在运行，不要动它。

## 背景

- id=8 已 done（09-11 10:25）。`progress.shortfallSlices` 89 条（long 87 / cur 2），缺口合计 4,199,824 子文档（4.92%），
  其中 `child:t202606100000:long` **整窗 dst=0（src 1,143,781）**；2026-06 共 11 条占总缺口 60%。终态快照 `_note/r26-job8-final.json`（进度 JSON 单行 2.2 MB，用 python 抽字段）。
- README §「结构性短缺」说事后用 `copyMode=ids` 或 repair 补搬；`copyMode=ids` 是 bootstrap 作业的参数（v1.4 按父 id 分批实现，仅供小范围修补）。

## 要回答的问题

1. **用 `copyMode=ids` 补搬到底会做什么**：读 `bootstrap.go` `runBootstrapJob` 与 `bootstrapCopyChildrenByIds`（或同名实现）、`validateBootstrapParams`、B1/B2 的 `BatchUpsert`：
   - 新建一个 `kind=bootstrap` 作业（带 `ctimeFrom/ctimeTo` 限定到目标窗口）会不会**重跑 B0~B2**？B1 的 `BatchUpsert` 对已存在的行（含 repair 刚标成 status=3 的行）做什么——会不会把 status 翻回 1？
   - copy_parent 会不会对该窗口再做一次父文档 reindex（幂等？对 repair ④ 刚去重的 long 副本会不会重新写回 cur/long 双份）？
   - `copyMode=ids` 的子文档复制按什么 id 列表（DB active 行？）分批，rps/并发参数是什么，1,143,781 子文档预计多久。
   - 有没有更小范围的入口（例如只跑 copy_child、或 repair 的某个检查项能补子文档）？如果没有，说明「最小可行作业参数」。
2. **guard 影响**：新 bootstrap 处于 pending/running/paused 时，`repair_guard` 会把在跑的 repair `id=11` 置为 paused 且不自动恢复——确认这一点，并给出「等 id=11 done 再排」的判断依据（`-jobs` 看 id=11 state）。
3. **2026-06 整窗 dst=0 的真实原因**（只读抽样）：
   - 从 `_note/r26-job8-final.json` 抽该窗口条目（key/src/dst/rerun）与 `progress.windows.join` 里对应窗口的 ctime 边界。
   - 用 `scripts/lc_mysql_ro.sh` 取该 ctime 区间、`index_name=res_long_2026` 且 active 的父 id 若干（≤200），用 `scripts/lc_es_ids_probe.sh` 确认父文档在 `res_long_2026` 存在；再对其中 20 个父 id 用 `has_parent`/`parent_id` 查询数其在 `res_long_2026` 的 file 子文档数、以及在 legacy `enfi_resource_v6_250822` 的子文档数（**不用 terms 聚合**，用 `parent_id` 查询 + `_count`）。
   - 结论：是「子文档在源有、目标全无」（真漏搬）还是「源侧这些子文档的 routing/父不在目标」（结构性）。若真漏搬，估算需要补的子文档量与父 id 数。
4. 其余 88 条按缺口占比分档（<1% / 1~10% / >10%），给出「值得补 / 可忽略」建议与理由（对搜索的影响：file 子文档缺失意味着该资源文件列表不可检索）。

## 交付（≤800 字 + 表）

- 问题 1~4 的答案，引用代码位置（文件:行）。
- 一份**可直接执行的补搬方案**（作业参数 JSON、预计耗时/负载、执行前置条件、核验方法、回滚/中止手段），以及不建议做的做法。
- 需要主控/用户决策的点单列。结束前 kill 自己的隧道（用 18085）。
