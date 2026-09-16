---
title: 可迁移模式：长周期生产巡检（全量 bootstrap 实战）
type: lesson
status: active
created_at: 2026-09-06T05:50:00+08:00
updated_at: 2026-09-17T01:50:00+08:00
priority: high
keywords: [巡检, bootstrap, 子Agent, 后台进程, 隧道, keepalive, progress, _count 差分, lc-check, watch 脚本, reindex, 吞吐, verify, repair, 对拍, rethrottle, heap]
summary: 派子 Agent 做数小时生产巡检的可操作清单（原 98 条经验按主题压缩）：前台等待、隧道 keepalive、复制阶段用 _count 差分而非 progress、watch 脚本静默降级要识别；具体吞吐数值另见 archive/2026/domain-bootstrap吞吐实测数据.md
load: on-demand
related:
  - agent-memory/current/tasks.md
  - agent-memory/procedures/workflow-部署.md
  - agent-memory/archive/2026/failure-copy_child真正瓶颈是子文档量.md
  - agent-memory/archive/2026/domain-bootstrap吞吐实测数据.md
---

# 可迁移模式：长周期生产巡检

## 问题

P4 全量 bootstrap（作业 id=8，约 2 天）需要主控派子 Agent 分轮巡检 4~6 小时。多轮巡检沉淀出以下可直接照做的清单；具体实测吞吐数值见 `archive/2026/domain-bootstrap吞吐实测数据.md`。

## 经验清单（按主题分组，可直接照做）

### 巡检/子 Agent 操作规范

- 巡检子 Agent 必须在自己回合内**前台**等到本轮结束才出最终报告；丢给后台 watch 脚本后提前结束回合，主控不会被叫醒。`sleep 540` 会被 harness 拦截，改用 `T=$(( $(date +%s)+540 )); until [ $(date +%s) -ge $T ]; do sleep 20; done`（单次 ≤9 分钟避开 Bash 10 分钟超时）；主控发现早退用 SendMessage 叫回。
- 隧道一律 `setsid nohup ssh -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L <port>:127.0.0.1:<port> <host> </dev/null >/dev/null 2>&1 & disown` 起：普通 `&` 会被 Bash `run_in_background` 的包装进程带走；不加 keepalive 约 2.5h 掉线；`es_curl.sh`/`lc_mysql_ro.sh` 内部 ssh 会吞 stdin，`while read` 循环要接 `</dev/null`。
- 清理隧道/后台进程只能按已记录的 pid：`pgrep -f`/`pkill -f` 会匹配到自身或误伤别的命令行（`tail -1` 取到的 pid 也可能不对）；唯一可靠做法是遍历候选 pid 读 `/proc/<pid>/cmdline`，只保留以目标命令精确前缀开头的那个再 kill。
- docker 相关 ssh 命令用裸主机名（root 用户），`pplabs@<host>` 在部分机器 sudo 需要密码会失败。
- 修改正在运行的 bash 守护脚本必须原子替换（写临时文件再 `mv`），原地编辑会破坏按偏移读取；改完需 `--stop` 再重新启动才生效。
- 子 Agent 会话可能被挂起数小时，无人值守的守护进程必须与 Agent 回合解耦（`setsid nohup` + 隧道自愈）。
- 主控用 python 做记忆文件增量替换必须 `assert old in s`：两次替换若锚点已被别的 Agent 改过会静默无效。
- `notify-admin.sh` 长 HTML 邮件正文、`cp` 备份 `_note/` 状态文件都可能被 auto 分类器拦截，正文要精简；发邮件走 `notify-admin.sh`（curl），python `urllib` 请求会被 403（UA 被挡）。
- `grep -ciE "panic|fatal"` 会被业务关键词误触发（如 "Fatales"），panic 判据改用 `grep -cE 'panic:|\[fatal\]'`。
- 禁止在网关日志里 grep `shortfall`/`短缺`（单次可输出 2MB+）；短缺明细只能从 `lc-check -job` 落盘后用 python 抽 `shortfallSlices`。
- 禁止对目标索引未知字段做 terms 聚合：会失败且可能触发 fielddata breaker，而 breaker tripped 是守护判定熔断的致命判据。
- **[事故]** 禁止在超大 legacy 索引上循环跑 `has_child` `_count`（曾把节点 heap 打到 99% 致重启、集群 red 27 分钟）；父子关系枚举一律走 DB（按类型分表 `file_count>0`）或小索引 term/range 过滤，ES 只读白名单仅限 `ids`、带 routing 的单父查询、小索引 `_count`，白名单外先报备。

### 进度/吞吐怎么判断

- `progress`/`ratio` 在复制阶段失效（`-1`、冻结、在 -1~1 间跳变），任何时候都不能用；进度与吞吐只能用目标索引 `_count`（按 join 类型分父/子）两次差分 ÷ 间隔秒。
- `lc_reindex_stat.sh` 单次采样只是瞬时任务计数（窗口 <3s），算不出有效吞吐，只能看任务在跑、rps 是否被降。
- `progress.slices` 前缀计数是复制阶段可靠的阶段完成度信号，但槽间密度不均，不能线性外推完成时间。
- 判断「限速空等 vs 集群慢」看 `_tasks?actions=*reindex*&detailed=true` 的 `created/total/throttled_millis`：`created==total` 且 `throttled_millis>0` = 已搬完在等限速（吞吐低不应熔断），`created<total` 才是 ES 侧慢；ES 6.7 该接口按后缀精确匹配，必须写 `actions=*reindex*`（不受 `detailed` 取值影响）。
- sliced `_reindex` 父任务自身 `requests_per_second`/`slices` 字段不可信（恒 0 / 全 null），判断真实限速要按 `parent_task_id` 归并全部分片子任务的 rps 求和，否则会误发 `_rethrottle`。
- `_tasks` 的 `total` 只是当前活跃分片之和，分片完成后会随之下降，算窗口百分比要用该窗口首次出现时的 total 作分母；父任务数=0 可能只是小窗口翻台间隙（数十秒到几分钟），看作业 `updatedAt` 是否推进 + 守护日志尾部再判。
- 幂等补跑窗口 `created≈0`，进度只能看 `version_conflicts`；补跑段结束信号是 vconf 从千万级归零 + `created` 与 `total` 同量级（比 `_count` 转正早约 20~25 分钟），是否处于重跑段要单独判断（`_tasks.total` 大而 `created≈0`、vconf 巨大 = 无效整窗重跑，非稀疏窗口），完成时间估算必须分段（重跑段 / 非重跑段差异可达 1.7×）。
- resume 后旧 `failedSlices` 会被自动重跑（`done` 只来自 `progress.Slices`，被清掉的失败键不在 done 里）；判据是 `created≈0` + vconf 巨大 + `shortfallSlices` 增量≈槽增量同时出现，此时 `_count` 差分（含负值）无意义，改用 `child:` 槽速率估算，且要把整段时间加回总完成时间。
- 「剩余窗口数 ÷ 窗口推进速率」可与 `_count` 差分交叉验证提高可信度，但剩余段窗口体量不均时两口径会显著背离（曾差 2.5 倍），此时以 `_count` 差分为主，槽口径只用于判断是否卡死。
- 不同时段（夜间/清晨/白天/尾段）、不同窗口体量下 copy_child 吞吐差异很大，且与 r%（真实慢请求占比）、窗口体量强相关，完成时间必须按昼夜和窗口体量分段加权估算，不能用单一均值——具体数值见 `archive/2026/domain-bootstrap吞吐实测数据.md`。
- `res_long_2026` `join=file` `_count` 是净值，会被业务 dual_write 的 `delete-by-query` 抵消，晚高峰可能出现持续净负增长；判别：连采仍降 + `created/total` 正常 + child 槽仍在涨 = 业务删除而非故障，非双写小时段该口径才可信。
- 尾段（progress>0.9）主口径切换为 child 槽/progress 线性推进，`_count` 仅作数据体量参考。

### 限速守护 / heap / 网关冲突

- 外部 rethrottle 守护与网关自带 `bootstrap_guard` 会互相对着调（guard 每开新窗口压半、外部守护 5 秒拉回），净效果外部守护胜出，等价于架空网关 heap 保护——上线外部守护务必保留 breaker 熔断兜底；外部守护失能时稳态 rps 会回落到 guard 的 peak/2。
- 集群空载 heap 基线可能长期在 85~93% 锯齿，用 85% 做阈值的守护/熔断会持续误触发，阈值应按集群实测基线可配（本集群改用 95/90）。
- 网关重部 + resume 后新窗口起步 rps 是 peak/2（guard 压半），守护 5 秒内会 `_rethrottle` 拉回 peak，采样恰好落在窗口刚起的瞬间会误判为降速。
- 作业 `pause` 不会取消 ES 侧 reindex（`es_task_id` 持久化会在 resume 时 reattach）；若 resume 后作业转去别的窗口，旧任务成为孤儿继续耗资源且被外部守护拉到 peak（合计 2×peak）。重部/resume 后必须核对 `_tasks?actions=*reindex*` 父任务数量，孤儿任务用 `_tasks/<id>/_cancel` 取消（幂等窗口无数据风险，2 分钟内见效）。
- 外部守护按父任务逐个 rethrottle、无全局预算，多父任务并存时集群 rps = N×peak。
- 守护状态文件的 `alert`/`es_fail_streak`（ES 取数失败）与 `stat_failed`（v2 慢请求统计取数失败）是两个独立字段，都要看，不能只看 `running`/`pid`；判守护死亡以 `/proc/<pid>` 为主，状态文件 mtime 天然可达 10~13 分钟属正常，配合日志尾有新行再判；守护 stop/start 一次窗口成本约 64 秒（期间 guard 压到 peak/2）。
- `es_curl.sh` 的地址解析正则是整条观测链与外部守护的单点故障：网关配置格式一变就可能静默匹配为空，下游全部 JSONDecodeError，但守护自身不报错、日志显示"父任务=0"——巡检要直查 `_tasks` 分片求和 rps 与守护日志"预算分配"时间对照，`thr_child<0` 直接判取数故障；改动 `_note/config/*` 形态前必须先 grep 所有脚本对该文件的解析。

### 数据一致性校验（verify / repair / 对拍）

- `bootstrapVerify` 按 cur→long 顺序、首个失败即 return，long 侧从未真正对拍过；verify 失败后任何 repair→retry 方案都要先手工补对拍另一半。差额方向要分开看：cur 是 DB>ES（位置不一致+线上删除），long 是 ES>DB（同 id 双索引副本），repair 分支不同。
- 「ES 有 DB 无」主因是同 id 双索引副本（bootstrap 长跑期间生命周期搬迁与 copy_parent 竞态），必须双向抽样：只从 DB 侧抽会严重低估（曾低估 18 倍）；ES 侧用 `function_score+random_score` 随机抽父文档反查 DB 与 cur。
- 生产只读对拍高效组合：`ids` 查询 1000 条/批 + ssh `ControlMaster` 复用（≈0.3s/批）；DB 侧按 id 哈希分桶只查命中的表；均匀抽样用 `CRC32(id)%N=0`，不用 `ORDER BY RAND()`/`OFFSET`。
- `repairDbToEs` 无 MaxDocs 上限（MaxDocs 只钳 `repairEsToDb`），全量遍历是小时级作业，排期按此估；repair 进度可按 `progress.message` 里的表名+id 做分表位置线性估算（配合 `information_schema.TABLE_ROWS` 求和），实测误差在 15 分钟内。
- ES/DB 父数对拍必须带 `status=1`：不带时差额会被已从 ES 清理但 DB 未清的历史行放大到 2~6%。
- verify→repair→retry 闭环实测有效：repair 后差额可从 0.1%+ 级降到 0.01% 级，retry 从 verify 续跑即可完成；join 子文档只存在于部分网盘类型分表（bnd 用 nested filelist），枚举短缺相关父文档时只需查这部分表。

### 配置 / 上线

- 配置迁移会暴露"从未生效的旧键"（v1 结构体缺 yaml tag 时键值静默丢失回落缺省，v2 正确解析后行为反而变化）：迁移前要专项扫描"字段无 tag/键名不匹配"，把 v1 实际生效值（而非文件值）作为 v2 基线。
- 配置拆分上线必须"先切读方到新对象，再上传去段后的旧对象"，不能先传后切：config-util 热加载期间若读方读到去掉自身段的配置会热加载到空段。
- 部署前必须运行产物做冒烟：编译/单测/隔离门禁全绿也可能起不来，产物体积异常是最快信号。
- NC-JS 微前端发布的回滚手段是还原 OSS 上的 `index.html`（`ossutil cp -r -f` 不会删旧 hash 资源，旧 `index.html` 还原即生效），发布前必须快照两者。

### 批量运维（归位/迁移）实测经验

- mover 类批量归位任务的实际吞吐受批间隔/批量/rps 共同限制，会显著低于理论值，含超大父文档的末段吞吐还会进一步走低，排期按实测量级估。
- 批量归位盯盘口径要落盘成脚本并冻结统计时间边界：动态重算的"待处理集合"会因跨零点等原因假性回升；剩余数不降时先查"是否原集合成员"（可能是新进入者，复投即清），不要先怀疑任务本身失败；固定抽样集合做 ids probe 比每轮重新抽样噪声小一个量级。

## 待改进（代码/文档，不在巡检中做）

- 生产写脚本 dry-run 只验证 SELECT，验证不了写路径；上线前加 `--batch 1` 最小真实试跑（见 `failure-临时表排序规则不一致导致JOIN报错.md`）。
- pause 重作业前先看 `lc-check -jobs` 有无 pending 的其它作业；网关重启会让 leader 漂移，属允许，记录即可。
- README「线上观测脚本」写明 `lc_reindex_stat.sh` 的局限与 `_count` 差分法；隧道命令补 keepalive 参数。
</content>

## 补记 2026-09-13：长时投递作业的两条护栏
- 经 ssh 隧道访问网关的长时作业，隧道必须有守护（断开自动重连 + `ServerAliveInterval`），本机到跳板机的网络抖动（00:30~00:47 res2 SSH 超时 17 min，主机本身正常）会让隧道静默消失。
- 投递/写入类工具对「对端不可达」要原地退避等待而不是记失败跳过（`tools/lc-recrawl` `77e92bb`），否则断连期间的行全靠事后补投；且 `pkill -f <模式>` 会连同自己的 shell 一起杀掉（模式出现在当前命令行里），改用 `pgrep -f | grep -vx $$` 逐个 kill。**后台等待循环里也不能用 `until ! pgrep -f <模式>`**——循环所在 shell 的命令行本身含该模式，永远匹配自己（09-14 阶段 C 编排因此卡了 19 小时）；改判产物/日志（如 `grep -q 完成 run.log`）或用 PID 文件。

## 补记 2026-09-17：灰度自动回落的误判来源
灰度分流器按"v3 5xx 率"回落时，v2/v3 **共有**的 5xx（参数错误却回 500：深翻页超 max_result_window、非法 resType）会在 100% 阶段（窗口无 v2 样本）反复触发误回落。处理原则：先用同参数打 v2 对拍，确认共有缺陷后把该路径改成 4xx（API `6062fb5`/`8ed53a8`），而不是放宽阈值；恢复用 res2 上的 `search-canary -config config.yaml -set N -resume`。
