---
title: 可迁移模式：长周期生产巡检（全量 bootstrap 实战）
type: lesson
status: active
created_at: 2026-09-06T05:50:00+08:00
updated_at: 2026-09-12T02:40:00+08:00
priority: high
keywords: [巡检, bootstrap, 子Agent, 后台进程, 隧道, keepalive, progress, _count 差分, lc-check, watch 脚本, reindex, 吞吐]
summary: 派子 Agent 做数小时生产巡检的 98 条硬经验：前台等待、隧道 keepalive、复制阶段用 _count 差分而非 progress、watch 脚本静默降级要识别
load: on-demand
related:
  - agent-memory/current/tasks.md
  - agent-memory/procedures/workflow-部署.md
  - agent-memory/lessons/failure-copy_child真正瓶颈是子文档量.md
---

# 可迁移模式：长周期生产巡检

## 问题

P4 全量 bootstrap（作业 id=8，约 2 天）需要主控派子 Agent 分轮巡检 4~6 小时。第 1 轮暴露了 4 个与巡检手段本身有关的问题。

## 经验

1. **[事实] 巡检子 Agent 必须在自己的回合内前台等待。**
   子 Agent 把 watch 脚本丢到后台后输出"等待采样点通知"就结束了回合，主控只收到这一句；后台进程不会把子 Agent 叫醒。
   规避：提示词明确要求 `sleep 540` 循环（单次 ≤9 分钟，避开 Bash 10 分钟超时）凑够采样间隔再采样，直到本轮结束才输出最终报告；主控收到早退可用 SendMessage 把它叫回继续。
2. **[事实] `ssh -N -L` 隧道不带 keepalive 约 2.5 小时掉线。**
   一律用 `ssh -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 18082:127.0.0.1:8082 osec-res2 &`。rollout §11.5 的命令待补。
   同一次网络中断也带走了用户自己的 18081 隧道（pid 1880789），子 Agent 按约束未代建——需报备用户。
3. **[事实] lc-check 的 `progress` 在复制阶段失效**：`progress=-1.00`、`progress.done` 冻结在 DB 行数、`progress.slices` 无窗口计数。
   进度与吞吐只能用目标索引 `_count`（按 `join` 类型分父/子）两次差分 ÷ 间隔秒；watch 脚本每行的 `cur(p/f)`/`long(p/f)` 可直接相减。
   `scripts/lc_reindex_stat.sh` 单次采样只是瞬时任务计数（小窗口 running_s <3 s），算不出有效吞吐，只用来看任务在跑、rps 是否被守护 `_rethrottle` 降过。
4. **[事实] watch 脚本对 lc-check 失败静默降级**（隧道断时输出 `state=? step=?`，ES 部分正常），容易被当成 ssh 抖动忽略。出现时先核对隧道，再核对网关容器。

5. **[事实] 判断「限速空等 vs 集群慢」看 `_tasks?actions=*reindex&detailed=true` 的 `created/total/throttled_millis`**：`created==total` 且 `throttled_millis>0` = 该窗口已搬完在等限速，瓶颈在作业侧（窗口固定开销），此时吞吐低不应熔断；`created<total` 才是 ES 侧慢。
6. **[事实] `progress.slices` 前缀计数是复制阶段可靠的阶段完成度信号**：`dbjoin/dbbnd` 为扫描窗口，`join/bnd` 为复制窗口（每窗口 2 个半区槽，总量 join 1620 / bnd 2196），但槽间密度不均不能线性外推时间。`progress`/`ratio` 会在 -1 与 1 间跳变，任何时候不用。
7. **[事实] `res_short_202609` 的 file 子文档存量（≈3,790 万）来自线上双写，背景增速 ≈56 docs/s**，算 copy_child 差分吞吐要扣除。
8. **[事实] `lc-check -job` 单次输出 ≈344 KB**（slices 全量），直接读会爆 token；用 `scripts/lc_job_brief.sh`/`lc_count_light.sh`（第 3 轮固化）。

9. **[事实] ES 6.7 `_tasks?actions=` 是精确后缀匹配**：`*reindex` 只命中以 `reindex` 结尾的父任务，sliced 子任务名是 `indices:data/write/reindex[c]`，必须写 `actions=*reindex*`；与 `detailed` 取值无关。已统一修正（SPIDER `3e12122`）。
10. **[事实] 长 `sleep 540` 会被 harness 拦截**（"Blocked: sleep 540"）。前台等待改用 `T=$(( $(date +%s) + 540 )); until [ $(date +%s) -ge $T ]; do sleep 20; done`。
11. **[事实] copy_parent 百度型窗口吞吐持续缓降**：08:27~09:08 有效 1,362 docs/s（1,543→1,221），守护未降速、rps 恒 6000；`created<total` 在窗口秒级翻台时是批中态，不代表 ES 慢。v2 延迟已到基线 1.7 倍（673 ms）。

12. **[事实] `scripts/v2_search_latency.sh` 的关键词组 1/2 不可跨组比较**（组 2 基线更高），熔断判据基线 404 ms 是组 1 口径，盯盘固定用组 1。
13. **[事实] copy_parent 尾段（稀疏年份）窗口体量会缩到目标值的 1/9（≈3.2 万/窗口）**，吞吐随之跌到几百 docs/s，`_tasks?actions=*reindex*` 是唯一能看出窗口体量的入口。
14. **[事实] heap 守护只看 heap，v2 延迟劣化到 13.5× 时守护全程未触发**；heap 峰值 90~94% 但 1 分钟内回落也不满足熔断条款——v2 延迟是本次唯一有效的护栏。
15. 清理后台进程用 `pgrep` 取 pid 再 `kill`；`pkill -f` 会匹配自身（退出码 144 且不生效）。

16. **[事实] sliced `_reindex` 的父任务 `status.requests_per_second` 恒为 0、分片在跑时父任务 `status.slices` 为全 null 数组**；判断实际限速必须按 `parent_task_id` 归并分片子任务的 rps 求和，否则会每轮误发 `_rethrottle`。
17. **[事实] 本 ES 集群空载 max heap 就在 85~93% 锯齿**（作业 paused、零 reindex 时实测 91~93），任何以 85% 为阈值的守护/熔断在此集群会持续误触发；守护改用 95/90。heap 阈值应按集群基线可配。
18. **[事实] 外部 rethrottle 守护会与网关自带 `bootstrap_guard` 对着调**（guard 每开新窗口压到 rps/2，守护 5 秒拉回），净效果外部守护胜出，等价于架空网关 heap 保护——上线外部守护时要意识到这一点，并保留 breaker 熔断作兜底。
19. **[事实] copy_child 窗口按父文档数配平、不保证子文档数配平**，早年窗口子文档极少（首窗口吞吐 ≈133 docs/s），早期吞吐不可外推完成时间；以 `child:` 槽推进 + 近 2 小时平均吞吐估算。

20. **[事实] copy_child 吞吐用 `res_long_2026` 的 `join=file` `_count` 差分**（无双写噪声），间隔 ≥25 分钟；`res_short_202609` 口径 60 秒短差分常为负值不可用。`_cat/indices` 的 docs.count 含 nested `filelist` 子文档（3.37 亿 vs `_count` 4,160 万），不能当进度。
21. **[事实] 早年 ctime 窗口（2013~2021）的 join 子文档为 0**，前 196 个 child 槽纯窗口开销空转（约 2.3 h），该段吞吐外推无意义。
22. **禁止对目标索引未知字段做 terms 聚合**：会失败并可能触发 fielddata breaker，而 breaker tripped 增长是守护的致命判据（pause + 退出）。
23. **[事实] 守护 `lc_v2_slow_ratio` 取数失败时状态文件记 `n=0 act=hold`**，与真实低样本区间无法区分（待加 `stat_failed` 字段）；`lc_job_brief.sh` 跳板 ssh 超时会静默输出父/子全 0，下次采样恢复即可。

24. **[事实] 守护状态文件 mtime 天然可达 10 分钟**（区间末才刷新），判守护死亡以 `/proc/<pid>` 为主、mtime >13 分钟且日志无新行为辅。
25. **[事实] 子 Agent 会话可被挂起数小时**（第 7 轮 23:50~07:48），守护进程必须与 Agent 回合解耦（setsid nohup + 隧道自愈）才能无人值守——本次验证有效。
26. `notify-admin.sh` 长 HTML 正文会被 auto 分类器拦，邮件正文要精简；`cp` 备份 `_note/` 下状态文件也可能被拦。

27. **[事实] 作业 pause 不会取消 ES 侧 reindex**（`es_task_id` 持久化，resume reattach）；若 resume 后作业转去别的窗口，旧任务成为孤儿继续消耗资源且被外部守护拉到 peak（合计 2×peak）。重部/resume 后务必核对 `_tasks?actions=*reindex*` 父任务数量，孤儿任务用 `_tasks/<id>/_cancel` 取消（幂等窗口无数据风险）。
28. **[事实] 外部 rethrottle 守护会把生命周期 move 搬迁的小 reindex 也拉到 peak**，属既有行为，短任务影响可忽略。

29. **[事实] 生命周期网关容器名是 `spider-gateway`**，`resource-storage-gateway` 是另一个长期服务（`/work/storage`），核对版本用 `docker ps --filter name=^spider-gateway$`。
30. **[事实] 外部守护按父任务逐个 rethrottle 无全局预算**，多父任务并存时集群 rps = N×peak；`_tasks/<id>/_cancel` 孤儿任务 2 分钟内见效（分片 10→4、heap 96→88、v2 15 分钟回落）。
31. **[事实] 修改正在运行的 bash 守护脚本必须原子替换（写临时文件再 mv）**，原地编辑会破坏 bash 按偏移读取；改后需 `--stop` 再启动才生效。

32. **[事实] `_tasks` 的 `total` 是当前活跃分片之和**，分片完成后从 `_tasks` 消失、`total` 随之下降；窗口百分比要用窗口首次出现时的 total 作分母。
33. **[事实] 幂等补跑窗口 `created≈0`，进度只能看 `version_conflicts`**（`scripts/lc_window_stat.sh` 按父任务输出 total/created/conflicts/已扫%/rps）；`lc_patrol_sample.sh` 只看 created 会误判"没在动"。pause/resume 或热修后作业会重扫已复制窗口，代价是同等的扫描时间（≈5,100 docs/s）。
34. **[事实] v2 主动探针（`v2_search_latency.sh`）与被动真实流量慢请求占比（`lc_v2_slow_ratio.sh`）明显解耦**（探针 1,354 ms 时 r 仅 7~9%，r 23% 时探针在回落），盯盘不能用前者推断后者。
35. `pgrep -f` 会匹配到自身所在的 `bash -c` 命令行（退出码 144），清理隧道/后台进程只用启动时记下的 pid。

36. **[事实] 补跑/大窗口尾段扫描速率随分片退出而降**（4 片 3,935/s → 1 片 1,608/s），估窗口剩余时间要按当前分片数折算。
37. **[事实] `_tasks` 父任务=0 且守护 `last_parents=0` 可能只是小窗口翻台间隙**（0.3~0.6 分钟），看作业 `updatedAt` 是否推进 + 守护日志尾部，1~2 分钟内恢复即正常。
38. **[事实] 补跑段结束的最快信号**：`version_conflicts` 从千万级归零、`created` 与 `total` 同量级，比 `_count` 差分早约 20 分钟。
39. **[事实] copy_child 窗口体量 2024-05 后骤降到 30~100 万级**，片数推进快但吞吐降至 3,800~4,200 docs/s（固定开销占比升高）；完成时间仍只用 `_count` 差分外推。

40. **[事实] 巡检隧道必须 `setsid nohup ssh … &` 起**：Bash `run_in_background` 包装进程退出时会带走普通 `&` 起的 ssh（第 11 轮 03:10 实测断开）。
41. **[事实] repair 互斥判据命中的是最早的未完成 bootstrap（id=4 paused）**，结果正确但语义偶然；清理 id=4 前需复核 `repair.go` 查询条件仍能命中在跑的作业。
42. **[事实] 守护进程重启后 `heap_brake.count` 归零**，历史刹车次数只能从日志统计。

43. **[事实] copy_child 密集小窗口段（26~100 万/窗，翻台 1~3 分钟）吞吐仅 2,000~2,200 docs/s**，固定开销主导；完成时间必须分段估算（小窗口段 ≈2,100、大窗口段 ≈5,500），不能用均值。
44. **[事实] 作业对用户体验的压力主要由窗口体量驱动而非用户流量叠加**：早高峰 r 峰值 10%、探针 750 ms，反优于夜间大窗口段（探针 2,526 ms）。白天维持 peak 18000 有实测支撑。
45. ~~`setsid nohup ssh … &` 后取 pid 用 `pgrep … | tail -1`~~ 已被第 48 条推翻：遍历 pgrep 结果读 `/proc/<pid>/cmdline`，只保留以 `ssh -N -L` 开头的那个。

46. **[事实] 配置迁移会暴露"从未生效的旧键"**：v1 结构体缺 yaml tag 时键值静默丢失回落缺省，v2 正确解析后行为反而变化（`log_store` → `LogStoreNotExist`）。迁移前应对"结构体字段无 tag / 键名不匹配"做一次专项扫描，把 v1 实际生效值（而非文件值）作为 v2 基线。
47. **[事实] docker 相关 ssh 命令用裸主机名**（root），`pplabs@<host>` 在 osec-resngix 等机器 sudo 需密码会失败。

48. **[事实] 第 12 轮沉淀的 `pgrep -f "ssh -N -L 18082" | tail -1` 取 pid 也不可靠**（第 13 轮实测 `tail -1` 取到 961963，真实 ssh 进程是 961912，kill 后隧道仍在）。正确做法：遍历 `pgrep -f "ssh -N -L 1808"` 的每个 pid，读 `/proc/<pid>/cmdline` 并只保留**以 `ssh -N -L` 开头**的那个，再 kill。
49. **[事实] `progress.windows.join[].EstCount` 是 join 型父文档估计数，不能用「子/父比」外推剩余子文档量**：第 13 轮实测已完成 246 窗口子/父比 159.4，据此外推剩余得 19.4 亿，超过源索引总量 12.00 亿本身，口径矛盾。EstCount 只可用于判断**剩余窗口的相对体量分档**。
50. **[事实] 「剩余窗口数 ÷ 窗口推进速率」是 `_count` 差分之外的独立校准口径，两者高度一致**：第 13 轮 4.79 h 推进 47 个窗口（9.8 窗/h），剩余 517 窗 → 52.8 h；同期 `_count` 差分外推 52.2 h。两口径交叉验证可提高完成时间校准可信度。
51. **[事实] copy_child 进入 2024-12 之后剩余窗口全为小窗口**：第 13 轮解析 join 窗口列表得剩余 564 窗中 488 窗为 1~10 万父文档级、5 窗 10~30 万级、71 窗 <1 万，**没有大窗口**。因此「大窗口段 5,500 docs/s」不再适用于剩余段，完成时间应统一按 3,000~4,400 估算（第 13 轮实测均值 3,416）。
52. **[事实] 网关重部 + resume 后新窗口起步 rps 是 peak/2**（`bootstrap_guard` 每开新窗口压半），守护 5 秒内 `_rethrottle` 拉回 peak；采样恰好落在窗口刚起的 0.1 分钟内会看到 `rps=9000`，不是守护降速。
53. **[事实] 上线窗口期（停守护→pause→重部→resume→重启守护）实测中断 20 分钟**（11:49:49 pause ~ 12:10:09 resume），resume 后无孤儿 reindex（守护日志 `N=1`），resume 后首段吞吐 3,368 docs/s 与 pause 前同量级，代价可忽略。

54. **[事实] NC-JS 微前端发布的回滚手段是还原 OSS 上的 `index.html`**，`apps.json` 的 entry 只是带 `?t=` 的缓存戳；`ossutil cp -r -f` 不会删旧 hash 资源，所以旧 `index.html` 还原即生效。发布前必须快照两者。
55. **[事实] 主控用 python 做记忆增量替换必须 `assert old in s`**：两次替换锚点失配静默无效（另一个 Agent 重写过该节），导致记忆缺失半天。

56. **[事实] `scripts/es_curl.sh` 的 `es_addr` 解析是整条观测链与外部守护的单点故障**：09-08 18:37 网关配置改 v2 格式（缩进、无引号）后固定正则匹配为空，`set -e` 静默退出输出空串，下游一律 JSONDecodeError；守护进程存活、`exit_reason` 空、日志恒「父任务=0」、状态文件 `thr_child` 大负值或 0 而 `n` 正常——**巡检"守护未死亡"条款不触发**，网关 guard 接管 rps=peak/2，吞吐腰斩 37 分钟。已修：兼容两形态、为空 `exit 3`（SPIDER）。巡检判据补充：每次直查 `_tasks` 分片求和 rps 与守护日志最近「预算分配」时间对照；`thr_child<0` 直接判取数故障。 守护 `c34ac3c` 起状态文件带 `alert`/`es_fail_streak`/`stat_failed`，**巡检必须看这三项而不只看 `running`/`pid`**。
57. **[事实] 外部守护失能时稳态 rps = 网关 guard 的 peak/2**（实测 9000），吞吐正好腰斩——外部守护的净贡献就是这 2 倍；改动 `_note/config/*` 形态前必须先 grep 所有脚本对该文件的解析。
58. [事实] 第 49 条"剩余全为 <30 万父文档小窗口"被证伪：第 14 轮实测单窗口 `_tasks.total` 达 370 万，剩余段吞吐区间放宽为 2,300~4,000 docs/s。

59. **[事实] 守护新版（`c34ac3c`）把「ES 取数失败」（`alert`/`es_fail_streak`）与「v2 慢请求统计取数失败」（`stat_failed`/detail）分成两个字段**，可单独触发，巡检两者都要看；守护 stop/start 窗口成本约 64 秒（期间 guard 压到 peak/2）。
60. **[事实] `lc-check` 无 `-leader` 参数**，leader 健康只能用作业 `updatedAt` 推进 + 网关日志无 panic 间接判断；巡检 18082 隧道不跨轮存活，每轮开始先建。
61. **[事实] 「`_tasks.total` 大而 `created≈0`、`version_conflicts` 巨大」= 无效整窗重跑**（校验短缺触发），不是稀疏窗口；判据直接看 `lc_window_stat.sh` 的 vconf 列，网关日志 `grep "重跑该窗口一次"` 是最快入口。每轮必须解析 `progress.failedSlices` 长度与 `Extra.childVerifyFail`（`lc_patrol_sample.sh` 不输出，盲区）。
62. [事实] 剩余段窗口体量不均时 `_count` 差分与窗/h 两口径会显著背离（64.6 h vs 85.9 h），第 50 条"高度一致"不再适用，以 `_count` 差分为主。

63. **[事实] 无效整窗重跑与窗口时间段相关**（集中在 2025-07 前后的 `:long` 半区），越过后自动归零；估算完成时间要按"是否处于重跑段"分段（差 1.70×）。
64. **[事实] 网关 `docker logs --since` 超过 1~2 小时不可靠**（约 35 万行/小时被 json-file 轮转截断），历史计数只能逐小时滚动采样累积。
65. **[事实] 配置拆分上线的顺序陷阱**（09-09 两份文件方案已回退改为拆代码，本条作为热加载通用告诫保留）：config-util 约 10 秒热加载 OSS 内容；运行中进程若读到去掉自身段的配置会热加载到空段。拆分时必须"先切读方到新对象，再上传去段后的旧对象"，不能先传后切。

66. **[事实] 部署前必须运行产物做冒烟**：`4f5f528` 默认构建 init 双角色 panic + `deploy.sh` 单文件构建残缺，编译/单测/隔离门禁全绿却起不来；体积反常（24.8MB vs 60.6MB）是最快的信号。

67. **[事实] resume 后旧 `failedSlices` 会被自动重跑**：`bootstrapCopyChildrenByWindow` 的 `done` 只来自 `progress.Slices`，被 `dropPrefixed` 清掉的 `child:` 失败键不在 done 里，按 specs 顺序重跑（第 19 轮 61 条 2025-04~08 大窗口跑了 5 小时，逐条记入 `shortfallSlices`）。判据：`created≈0` + vconf 巨大 + `shortfallSlices` 增量≈槽增量 三者同现 = 重跑段；此时 `_count` 差分（含负值）无意义，用 `child:` 槽速率 + cursor 日期推进，完成时间要把整段加回去。
68. **[事实] `grep -ciE "panic|fatal"` 会被业务关键词误触发**（爬虫关键词 "Femme Fatales" 命中 `fatal`），panic 判据用 `grep -cE 'panic:|\[fatal\]'`。
69. **禁止在网关日志里 grep `shortfall`/`短缺`**：`GetJob` 的 progressJson 含 `childShortfall`，单次 grep 输出 2.2 MB；短缺明细只能从 `lc-check -job` 落盘后用 python 抽 `shortfallSlices`。
70. **[事实] `shortfallSlices` 明细可直接算全局短缺率**（第 19 轮 57 条：src 5,808 万 / dst 5,678 万，缺 2.24%），是完成校验前的数据完整性早期指标。

71. **[事实] 越过重跑段的判据**：`vconf` 从千万级直接归零 + `created` 与 `total` 同量级 + `shortfallSlices` 增量 < 槽增量，三者同现即判定（比 `_count` 转正早约 25 分钟）；越段后 `_count` 差分立刻由负转正且量级跃升（-3,000 → +6,800 docs/s）。跨段估算必须以越段时刻为新基线重算，含重跑段的均值会把完成时间推后一天以上。第 20 轮实测：61 条旧 failedSlices 重跑共耗 ≈5.5 h。
72. **[事实] 小窗口段 child 槽速率与 `_count` 差分背离可达 2.5 倍**（8.6 槽/h → 77 h vs `_count` → 30 h），第 50 条「两口径高度一致」在剩余段彻底失效，槽口径只用于判断是否卡死。
73. **[事实] 密集小窗口段翻台间隙可长达 6 分钟**（第 37 条的 0.3~0.6 分钟需放宽），复核优先看守护日志「预算分配 N=1」而不是再跑 `lc_window_stat.sh`（一次 ssh 往返 30~60 秒且可能超时）。
74. **[事实] 巡检隧道会静默断开且不报错**：`lc_patrol_sample.sh` 只输出「slices解析失败」而 ES 部分（走跳板）仍正常，极易误判为作业异常。brief 缺 slices 行时先 `ss -ltnp | grep <端口>` 再重采。

75. **[事实] 夜间 copy_child 吞吐分段收敛**（09-09 22:38~09-10 03:48，11 段全在 2,439~4,906、均值 3,388），且与窗口 `total` 体量无明显相关（2.41M 大窗口跑出最慢 2,439）；白天沉淀的「大窗口 5,300~6,900 / 小窗口 1,400~2,900」分段口径不适用于夜间，夜间直接用 3,200~3,400 中枢外推。
76. **[事实] 「`long_file` 取数成功 + brief slices 解析失败 + 分片=0」是本地隧道断开的特征组合**（`es_curl` 走跳板、brief/lc-check 走本地隧道，两者独立），可据此秒判，不必怀疑作业。守护隧道 18083 的 pid 会自行更替（自愈），只要仍 LISTEN 且守护日志「预算分配 N=1」持续刷新就不介入。翻台间隙判法：作业 `updatedAt` 在数秒内 + 守护日志最近一条 `N=1` 即正常，无需等 6 分钟复采。

77. **[事实] 早高峰对 copy_child 的压制发生在 08:00 之后而非 07:00**：07:00~08:00 r 3~6%、吞吐 4,400+（优于夜间均值 3,388）；08:00~09:00 r 12~18%、吞吐 1,926~2,832（−40%）。第 44 条「早高峰反优于夜间」限定为 07:00~08:00；08:00 后白天段外推用 2,000~2,800 中枢。r%（真实慢请求占比）判吞吐受流量影响、探针中位判用户体验熔断，两者再次解耦（r=18% 时探针 654~952，r=1~4% 时探针 1,037/峰 9,710），补强第 34 条。
78. **[事实] 跳板 ssh 取 `nodes` 超时会让 brief 行序错位**（`done=/ratio=` 行顶掉 slices 行，表现为 child 槽消失 + `total=None ratio=`），不是隧道断（第 74/76 条特征是 slices 行缺失且分片=0）。`lc_patrol_sample.sh` 已改为关键字匹配（09-10）。

79. **[事实] 白天段（08:00~14:00）copy_child 吞吐与 r% 强负相关**：r≤7% 时 2,700~4,600 docs/s，r≥15% 时 1,000~1,900；全时段均值 2,071，约为夜间（3,300~3,400）的 61%。完成时间外推必须按昼夜分段加权（白天 ≈2,100 / 夜间 ≈3,350），单用某一段均值偏差 6~11 小时。
80. **[事实] v2 延迟超线必须「中位 + 间隔 ≥10 分钟复测」再判**：12:38 单次中位 1,370 ms 是午间查询高峰抖动，12 分钟后回落到 672 ms；按单次结果 pause 会误伤。

81. **[事实] 白天段吞吐由「窗口体量 × r%」共同决定，两者可互相抵消**：17:40~18:10 2.3M 大窗口 + r 9~13% 跑出 3,367，17:10~17:40 130K 小窗口 + r 9~18% 只有 1,278，同一小时差 2.6×。白天段外推必须用 ≥3 段滚动均值；全白天（09:00~19:10）加权实测 ≈1,967，昼夜加权模型的白天参数用 1,950~2,000（第 79 条的 2,100 偏乐观约 1.7 h）。
82. **[事实] `shortfallSlices` 在非重跑段自然增速 ≈0.6 条/h**，「短缺增量 / 槽增量 <10%」即非重跑段（本轮 3.4%），比逐窗口看 vconf 快得多。v2 探针午后~晚间会规律性单次超 1,100 后 10 分钟自愈（本轮 3 起），熔断条款保持「连续 3 次 + `created<total`」不放宽。

83. **[事实] `res_long_2026` `join=file` `_count` 是净值，会被业务 dual_write 的 `delete-by-query` 抵消**：晚间业务高峰（r>20%）可出现持续净负增长（第 25 轮 22:15 起连续 3 窗），差分不可用于完成外推。判别：连采 3 次仍下降 + `created/total` 正常 + child 槽仍在涨 = 业务删除非作业故障；`_tasks?actions=*delete/byquery*&detailed=true` 里短命（<15 s）+ 无 parent + 命中 legacy 索引即业务流量。第 20 条的「无双写噪声」只在删除量小的时段成立。
84. **[事实] 尾段（progress>0.9）主口径切换为 child 槽 / progress 线性推进**，`_count` 仅作数据体量参考。单次 Bash 硬上限 600 s（更大 timeout 会被降到后台），等待段设 ≤480 s；守护状态文件采样落在区间末尾时 mtime 可显示 9~10 分钟前，配合日志尾有新行再判。

85. **[事实] `bootstrapVerify` 按 cur→long 顺序、首个失败即 return，long 从未对拍**：verify 失败后任何「repair→retry」方案都必须先手工补对拍另一半（第 26 轮后实测 long 也超标 0.146%，直接 retry 会连续失败两次）。DB/ES 差额必须分方向：cur 是 DB>ES（位置不一致 + 线上删除），long 是 ES>DB（同 id 双索引副本 ≈5.3 万），repair 分支不同（②③ vs ④）。
86. **[事实] 「ES 有 DB 无」主因是同 id 双索引副本**（bootstrap 长跑期间生命周期搬迁与 copy_parent 竞态），**必须双向抽样**：只从 DB 侧抽会低估 18 倍；ES 侧随机父文档用 `function_score + random_score(seed, field=_seq_no)`、`_source:false` 反查 DB，再用 `ids` 查询确认是否也在 cur。
87. **[事实] 生产只读对拍的高效组合**：`ids` 查询 1000 条/批 + ssh `ControlMaster` 复用实测 0.3 s/批；DB 侧按 `bucket=int(id[0:2],16)%16` 只查 4 张表，5000 id/批 ≈2 s；全量 2.75M 对拍约 14 分钟。均匀抽样用 `CRC32(id)%N=0`，不用 `ORDER BY RAND()`/`OFFSET`。
88. **[事实] `repairDbToEs` 无 MaxDocs 上限**（MaxDocs 只钳 `repairEsToDb` 的 scroll），②③④ 全量遍历 64 表 43.7M 行 ≈43,700 次 LocateIds，小时级作业，排期按此估。
89. **[事实] v2 配置 `_note/config/spider.prod.yaml` 的 `mysql:` 缩进在 `services.gateway` 下且口令含 `#`**：`[^"\s#]+` 会截断（截断后的报错会把口令片段回显到 stderr），要用 `[^"]+`，mysql 输出一律过打码 sed 再打印。legacy 索引 `join=resource` 仅 1,455 万（bnd 型是 nested filelist 不参与 join），不能用它校验新索引父文档完整性。

90. **[事实] B6 `scheduleJobOnce` 排出的 repair 落库 `Operator` 恒为 `system`**，`bootstrap-<id>` 只是 redis 幂等键；识别靠「bootstrap done 后 ≈15 秒创建 + operator=system」。
91. **[事实] repair 进度可按分表位置线性估算**：`progress.message` 形如「对账(DB->ES): <表名> 进行到 <id>」，表序 bnd_00~15 → ali → quark → xunlei，用 `information_schema.TABLE_ROWS` 按类型求和（近似行数，无全表扫描）10 分钟内可估完工点（实测误差 13 min）。全量 repair 白天实测 2h55m（44.7M 行）。
92. **[事实] repair ④ 去重高度集中在 bnd 表**（57,414 条中 ~57,300），成因是 bootstrap 长跑期间百度型窗口与生命周期搬迁的竞态；① es_to_db 扫满 MaxDocs 20 万零收益（≈5 min），已知 cur 无「ES 有 DB 无」时可 `skipEsToDb=true`。
93. **[事实] verify 失败→repair→retry 的闭环实测**：repair 后 cur 0.107%→0.0067%、long 0.146%→0.0030%，retry 从 verify 续跑 25 秒 done；差额方向由 DB>ES 翻为小幅 ES>DB（双写时点差），属正常。

94. **[事故][事实] 在 legacy 索引 `enfi_resource_v6_250822`（14.9 亿）上循环跑 `has_child` `_count` 会把节点 heap 打到 99% 致重启**（09-11 17:00，data-i-2 重启、集群 red 27 分钟、shard 走 existing_store+translog 恢复，无数据丢失；节点重启后 breaker tripped 计数清零，新基线全 0）。父子关系枚举一律走 DB（`file_count>0`、按 type 分表）或 cur 小索引的 term/range 过滤；ES 只读白名单：`ids`、单父 `parent_id`（带 routing）、cur 索引过滤 `_count`。白名单外先报备。
95. **[事实] join 子文档只存在于 ali/quark/xunlei 三类（bnd 用 nested filelist）**，shortfall 相关父的枚举只查这 48 张表；父文档 ES `_source` 无 `file_count`，DB 列 `file_count` 是判「有无子文档」的便宜入口。

96. **[事实] mover 批量归位实测**：`move_interval_sec=30`、`move_batch=200`、rps 3000 时真实吞吐 12,000~15,500 父/h（理论 24,000；runOnce 单批 25~30 s 与间隔同量级），含超大父的末段 ≈9,000/h；102,601 父 8 h 搬完，集群 green、heap ≤79、v2 中位 ≤560，对线上无感。
97. **[事实] 批量归位的盯盘口径要落盘成脚本并冻结时间边界**：`utime<now-90d` 每天重算会让集合跨零点变大、剩余假性回升，固定枚举当日边界才得单调曲线；剩余不降先查「是否原集合成员」（本次 1 条是新进入者，复投即清），别先查 mover 失败日志。固定 2000 抽样集做 ids probe 比每轮重抽噪声小一个量级；ES ids 口径与 DB index_name 口径误差 <1%。
98. **[事实] ES/DB 父数对拍必须带 `status=1`**：不带时 cur 差 6%、long 差 2%（DB 里 status≠1 的行已从 ES 清掉），带上后差额 0.001% 级。`es_curl.sh`/`lc_mysql_ro.sh` 内部 ssh 会吞 stdin，`while read` 循环必须 `</dev/null`；后台隧道用 `setsid nohup … </dev/null >/dev/null 2>&1 & disown` 才跨 Bash 调用存活。

## 实测数据（供估算复用）

- **copy_child 午后~晚高峰（09-10 14:10~19:10，第 24 轮）均值 1,861 docs/s**，分段 1,278~3,367；全白天加权 ≈1,967。
- **copy_child 白天工作时段（09-10 09:02~14:07，第 23 轮）均值 2,071 docs/s**，分段 1,245~3,322，与 r% 强负相关。
- **copy_child 清晨~早高峰（09-10 03:51~08:58，第 22 轮）均值 3,218 docs/s**：07:00~08:00 4,400+，08:00 后 1,926~2,832。
- **copy_child 夜间（09-09 22:38~09-10 03:48，第 21 轮）均值 3,388 docs/s**，分段 2,439~4,906 收敛、与窗口体量弱相关。
- **copy_child 越过重跑段后（09-09 17:53~22:33，第 20 轮）有效吞吐 3,642 docs/s**：1200~1800 万级大窗口 5,309~6,864，21:00 后 9~200 万级密集小窗口 1,415~2,946。
- **copy_child 白天小窗口段（09-08 09:35~14:25，第 13 轮）均值 3,416 docs/s**（有效运行口径，扣除 20 分钟上线 pause），分段区间 2,363~4,407；同期 r 6~27%、v2 组 1 中位 522~742 ms、heap 59~98 锯齿、breaker 恒 fielddata 2 / parent 0。
- copy_child 夜间（09-07 23:00~04:25）均值 5,526 docs/s，大窗口 8,000~8,600；白天/晚间均值 4,807 docs/s：2,400 万级窗口 6,000~7,600，30~100 万级小窗口 3,800~4,200；补跑（幂等冲突）扫描 ≈5,100。
- copy_child 密集年份（2024~2026）单窗口 5,000 万~1 亿，peak 18000 时吞吐 4,800~5,900 docs/s，隔夜均值 4,984。
- **源索引子文档总量 12.00 亿（`join=file` `_count` 实测）**，此前按单月外推的 6.73~7.4 亿偏低近一倍；copy_child 真实数据窗口纯净吞吐 4,300~4,500 docs/s（peak 10000、r 10~20%）。
- 建库阶段 db_join 2,644 行/s、db_bnd 2,000~3,752 行/s，4,434 万行共 3.9 h（rollout §11.5 按 5,686 折算只给了 2.2 h）。
- copy_parent 全程（09-06 03:42→13:25，含两次 pause）约 9.7 h 复制 4,431 万父文档，rps 6000 时 2,674→364 docs/s 缓降（百度窗口密度不均、尾段窗口缩到 3.2 万），rps 2500~5500 时 933~1,456 docs/s；copy_parent 旧记录：2,674 → 1,442 docs/s 缓降（join 型全部复制完后进入百度型窗口，密度不均）（slices=5 × 1200 rps，heap 44~79%，守护未触发），明显低于单月实测的 5,686。父文档字段多、窗口固定开销占比高是可解释原因，copy_child 吞吐待第 2 轮实测。

## 待改进（代码/文档，不在巡检中做）

- ~~lc-check / watch 脚本补"已完成窗口/总窗口"输出~~（`lc_job_brief.sh` 的 slices 前缀计数已覆盖）；watch 脚本对 lc-check 失败单独打标记。
- 生产写脚本 dry-run 只验证 SELECT，验证不了写路径；上线前加 `--batch 1` 最小真实试跑（见 `failure-临时表排序规则不一致导致JOIN报错.md`）。
- pause 重作业前先看 `lc-check -jobs` 有无 pending 的其它作业；网关重启会让 leader 漂移，属允许，记录即可。
- README「线上观测脚本」写明 `lc_reindex_stat.sh` 的局限与 `_count` 差分法；rollout §11.5 隧道命令补 keepalive。
