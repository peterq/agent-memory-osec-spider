# 10-patrol —— 巡检 Agent（Opus）：作业 id=8 直至 done

## 目标

在本轮时长内（**约 5 小时**，或作业 `done/failed` 立即结束）无人值守地盯 id=8，只在触发介入条款时动手，
最终输出一份精简报告给主控。

## 节奏

- **每 30 分钟**：`scripts/lc_patrol_sample.sh 8 _note/adaptive_rps.state.json 127.0.0.1:18085`，
  并单独解析 brief 的 `failedSlices / childVerifyFail / childShortfall / shortfallSlices` 四个数（变化要记）。
  以 `long_file` 两次差分 ÷ 间隔秒算吞吐（间隔 ≥25 分钟）；同时记 `child:` 槽（总 1620）推进。
- **每 1 小时**：breaker、`scripts/v2_search_latency.sh osec-res2 1`、两台容器 id 是否仍为 `93d1fb726816`/`600e1a8c2738`
  与 `docker logs --since 1h spider-gateway 2>&1 | grep -cE "panic:|\[fatal\]"`（不要 `-i fatal`，会被关键词误触发）（`--since` >2 h 不可靠）、
  网关日志 `grep -c "重跑该窗口一次"`、守护日志尾 5 行与状态文件 `alert / es_fail_streak / stat_failed / running / pid`（`/proc/<pid>` 存在）。
  直查 `_tasks?actions=*reindex*&detailed=true` 分片 rps 求和应 ≈ 状态文件 `peak`（18000），父任务数应为 1（0 可能是翻台间隙，1~2 分钟后复查）。
- 每小时把一行摘要追加到 SPIDER `_note/patrol-2026-09-09-r19.log`（时间、进度%、吞吐、child 槽、r%、heap、v2、介入），方便主控中途查看。

## 口径补充（第 19 轮沉淀）

- **重跑段判据**：`created≈0` + vconf 数百万 + `shortfallSlices` 增量≈槽增量 三者同现 = 在重跑 resume 前的旧 failedSlices 窗口（约 61 条，第 19 轮已跑 57 条，本轮应很快越过）。该段 `_count` 差分无意义，只报槽速率与 cursor。
- **越过重跑段的信号**：`created` 与 `total` 同量级、vconf 归零、`shortfallSlices` 不再随槽 1:1 增长。之后恢复 `_count` 差分（≥25 分钟）作主口径，并**重新校准完成时间**（当前估 09-11 16:00~24:00），报告里两口径都给。
- **禁止**在网关日志 grep `shortfall`/`短缺`（progressJson 单行 2.2 MB）；短缺明细只能把 `go run ./tools/lc-check -addr 127.0.0.1:18085 -job 8` 输出重定向到 `_note/` 下文件再用 python 抽 `shortfallSlices` 字段，不打印全文。
- 重跑段已于 09-09 17:50 越过，此后以 `_count` 差分为主口径（越段后实测 3,642 docs/s；大窗口段 5,300~6,900、密集小窗口段 1,400~2,900），夜间实测收敛为 2,400~4,900、均值 3,388 且与窗口体量弱相关；白天 08:00 后 r 12~18% 时吞吐 1,900~2,800（早高峰压制），07:00~08:00 反而 4,400+；白天工作时段（08:00~14:00）实测均值 2,071（与 r% 强负相关）；**完成时间必须按昼夜分段加权外推**（白天 ≈1,950~2,000 / 夜间 ≈3,350；白天段用 ≥3 段滚动均值），当前校准 09-11 ≈16:20（区间 14:00~19:00），每轮重校。「短缺增量/槽增量 <10%」即非重跑段。v2 中位单次超 1,100 先隔 ≥10 分钟复测，不按单次判。brief 出现 `total=None ratio=` 而 child 槽消失 = 跳板超时行序错位（脚本已改关键字匹配），不是隧道断。**尾段口径（09-11 起生效）**：`_count` 差分已被业务 dual_write 的 delete-by-query 抵消（净负不是故障，判别见 patterns #83），**主口径切换为 child 槽 / progress 线性推进**（21 槽/h 上下），`long_file` 只记数值不外推。**采样间隔缩到 15 分钟**（等待段 ≤480 s），作业 done/failed 立即返回。done 时只记录 `finishedAt`、brief 终态与四个计数，不做校验。
- 小窗口段翻台间隙可达 6 分钟：`父任务数=0` 时先看守护日志「预算分配 N=1」与作业 `updatedAt`，不要立刻重跑 `lc_window_stat.sh`。
- brief 缺 slices 行 / `lc-check -jobs` 空输出 = 大概率自己的隧道静默断了，先 `ss -ltnp | grep 18085` 再重建，不是作业异常。
- 每小时摘要追加到 `_note/patrol-2026-09-09-r<轮次>.log`（主控 prompt 会给轮次）。

## 介入条款（命中才动，动前先复核一次判据，动后邮件）

1. 守护死亡（`/proc/<pid>` 不存在，或状态文件 mtime >13 分钟且日志无新行）或 `alert` 非空 / `es_fail_streak≥3` → 按 00-shared §3 停后重启守护（`--peak` 用状态文件里的 peak）。
2. 出现非 id=8 的 running 作业（repair 除 id=8 自带外）→ `go run ./tools/lc-check -addr 127.0.0.1:18085 -control-job <id> -action pause` 并报告。
3. `_tasks` 里出现 ≥2 个 bootstrap 父任务（`reindex from [resource] to [`）且持续 >3 分钟 → 孤儿 `_tasks/<id>/_cancel`（保留 `updatedAt` 在推进的那个）。
4. 熔断（任一）：集群非 green / breaker tripped 相对基线增长 / 任一节点磁盘可用 <20% / v2 组 1 延迟 >1,100 ms 连续 3 次（间隔 ≥10 分钟）且 `created<total` → pause 并立即返回报告。
5. 作业 `done` / `failed` → **立即**输出最终报告返回（不做完成校验，那是另一个 Agent 的活）。
6. 隧道断（`state=? step=?` 或 lc-check 连接失败）→ 先重建自己的 18085 隧道，再核对网关容器；不要误判为作业故障。

**不要做**：手工 rethrottle、改参数、重部、resume（除非是自己因条款 4 pause 后主控明确让你 resume）、动 18082/18083/18084 隧道。
旧会话的第 18 轮巡检 Agent 可能仍在跑到 ~15:30（只读为主），若发现守护 pid 变化但 `running=true`，当作它已处理，不重复重启。

## 交付（最终报告 ≤600 字，中文）

- 本轮时间段、采样次数、是否介入（及原因/动作/结果）。
- 进度：起止 `long_file` 计数与百分比、child 槽起止、均值吞吐与分段吞吐、**用 `_count` 差分外推的完成时间**。
- 四个计数起止：`failedSlices / childVerifyFail / childShortfall / shortfallSlices`；网关「重跑该窗口一次」次数。
- 集群：heap 区间、breaker、v2 组 1 中位与峰值、r% 区间、守护 peak 变化与 pause/刹车次数、容器 id 是否未变、panic 计数。
- 异常与建议（可为空）。新的**可复用经验**单独列出（供主控写入 patterns）。
- 结束前确认已 kill 自己的 18085 隧道。
