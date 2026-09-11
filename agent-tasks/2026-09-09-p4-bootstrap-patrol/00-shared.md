# 00-shared —— P4 全量 bootstrap（作业 id=8）巡检：共享背景与硬性约束

> 2026-09-09 12:25 起由新会话主控接管。所有巡检/校验子 Agent 都要先读本文件。

## 1. 背景

- 资源 ES 索引生命周期改造 P4：全量 bootstrap 作业 **id=8**（operator `p4-full`，09-05 23:01 启动），
  当前 `step=copy_child`，进度 ≈61.9%（`res_long_2026` `join=file` `_count` 7.425 亿 / 源索引 12.00 亿）。
  完成校准 **09-11 10:00 ~ 18:00**（以 `_count` 差分 ≥25 分钟为主口径）。
- 网关已于 09-09 用 master `883daeb` 重部完成：res1 `93d1fb726816`（11:53）/ res2 `600e1a8c2738`（12:04，leader），
  二进制 md5 `bdd0c722…`；作业 12:13 resume，动态 rps 守护 12:17 重启（pid 以状态文件为准）。
  新代码要点：copy_child 结构性短缺**不再整窗重跑**，记入 `shortfallSlices`；resume 时会清掉
  `progress.failedSlices` 里 `child:` 前缀的旧记录（所以 brief 里 `failedSlices` 由 61 变 0，属预期）。
- 仓库：SPIDER `/home/peterq/dev/projects/1s/osec-spider-go`（脚本都在这里跑），
  COMMON `/home/peterq/dev/projects/1s/enfi-resource-common`（记忆与简报；子 Agent **不改** agent-memory，由主控改）。
- `_note/` 是仓外符号链接（不入 git），守护状态 `_note/adaptive_rps.state.json`、日志 `_note/adaptive_rps.log`。

## 2. 硬性约束（违反会造成生产事故，逐条遵守）

- 输出/报告/邮件**不得出现凭据**：ES 地址含账号口令、MySQL DSN、`deploy.sh` 内 OSS AK/SK、`_note/config/*` 内容、
  GitHub client_secret/session_secret、OSS 预签名 URL、`docker inspect` 的 Env（含 `OSS_CONFIG_URL`，**不要打印 Env**）。
  看 deploy.sh 用 `grep -v -iE 'access|secret|password|=.*key|http'`。
- 不碰 osec-resdb 主机；不 retry 作业 id=1；不动 id=9（canceled）；id=4（paused）**仅允许在 30-recover.md 任务中按用户 09-11 授权 cancel 一次**，其他任务仍不动；不碰旧检测进程 url_check；
  **不改热更新参数**（`enabled=true`、`dual_write_legacy=true` 必须保持）。
- 不 `git add -A`；不动用户未提交改动；不 rm -rf / force push / 删索引 / `_delete_by_query`；宿主机旧 `config.yaml` 不删；
  OSS 旧对象 `res/spider.gateway.prod.yaml` 不动。
- **禁止对目标索引未知字段做 terms 聚合**（触发 fielddata breaker，而 breaker 增长是守护的致命判据）。
- **禁止在 legacy 大索引 `enfi_resource_v6_250822`（14.9 亿文档）和 `res_long_2026`（13.5 亿）上执行 `has_child` / `has_parent` / 任何聚合 / 全索引 `_count`（带过滤也不行）**——09-11 17:00 一次 `has_child` `_count` 循环把 data-i-2 heap 打到 99% 致节点重启、集群 red 27 分钟。
  ES 只读查询**白名单**：`ids` 查询（≤1000/批）、`parent_id` 查询（带 routing=父 id、单父）、在 `res_short_202609`（2.7 M 父）上的 term/range 过滤 `_count`/`_search`（`_source:false`，size ≤1000，search_after 翻页）。白名单之外的查询必须先向主控报备并获准。
  枚举父/子关系优先走 **DB**（`scripts/lc_mysql_ro.sh`，按 type 分表，SELECT 加 LIMIT），不要用 ES 反推。
- 不与守护对着调 rps（不要手工 `_rethrottle`）。不重部网关、不改代码（发现代码问题只报告）。
- 生产操作一台一台、失败即停并报告。

## 3. 环境与工具（都在 SPIDER 仓库目录下执行）

- **隧道**：每轮自己建、用**独立端口 18085**（18082/18084 属旧会话 Agent，随时会被它收掉；18083 属守护，勿动；18081 勿建）：
  ```bash
  cd /home/peterq/dev/projects/1s/osec-spider-go
  setsid nohup ssh -N -L 18085:127.0.0.1:8082 osec-res2 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 >/dev/null 2>&1 &
  sleep 2; ss -ltnp | grep 18085
  ```
  取 pid：遍历 `pgrep -f "ssh -N -L 18085"`，读 `/proc/<pid>/cmdline` 只保留以 `ssh -N -L` 开头者（`pgrep|tail -1` 不可靠）。
  本轮结束 kill 该 pid，并 `ss -ltnp | grep 1808` 确认 18085 已不在（18083 守护隧道、18082/18084 旧会话隧道**不要动**）。
- lc-check 命令**必须以 `go run ./tools/lc-check` 开头**（项目级权限前缀放行），例如
  `go run ./tools/lc-check -addr 127.0.0.1:18085 -jobs`。`lc-check -job 8` 单次输出 344 KB，**不要直接看**，用 brief。
- 观测脚本（先读各脚本头部注释）：
  - `scripts/lc_patrol_sample.sh 8 _note/adaptive_rps.state.json 127.0.0.1:18085` —— 单次合并采样（long_file 计数 / brief / 分片 rps / 守护区间）。
  - `scripts/lc_job_brief.sh 8 127.0.0.1:18085` —— 作业摘要 + `failedSlices/childVerifyFail/childShortfall/shortfallSlices`。
  - `scripts/lc_window_stat.sh` —— 按父任务看 total/created/vconf（判无效整窗重跑）。
  - `scripts/es_curl.sh '<path>'` —— 经 osec-res2 跳板；**单次 ssh 连接超时会输出空串 / brief 父子计数为 0，视为瞬时故障，隔 30 秒重采**。
  - `scripts/v2_search_latency.sh osec-res2 1` —— v2 搜索延迟，**固定组 1**，基线 404 ms。
  - `scripts/es_curl.sh '_nodes/stats/breaker' | grep -o '"tripped":[0-9]*' | sort | uniq -c` —— 基线 fielddata 2 / parent 0（历史遗留）。
- 守护：`scripts/lc_adaptive_rps.sh`（README「动态 rps 守护」一节）。
  停：`scripts/lc_adaptive_rps.sh --stop --state _note/adaptive_rps.state.json`；
  启：`exec setsid nohup ./scripts/lc_adaptive_rps.sh --job 8 --peak <状态文件 peak> --step 1000 --max 18000 --window 600 --execute --state _note/adaptive_rps.state.json --log _note/adaptive_rps.log >/dev/null 2>&1 &`
  启动时「params.requestsPerSecond 读取失败」「未解析到 DSN」两条告警属预期。
- 邮件：`/home/peterq/dev/projects/1s/enfi-resource-common/scripts/notify-admin.sh "<主题>" "<html>" lifecycle-deploy`，正文精简（长 HTML 会被拦）。
- **前台等待**：`sleep 540` 会被拦，用 `T=$(( $(date +%s)+540 )); until [ $(date +%s) -ge $T ]; do sleep 20; done`（单次 Bash ≤9 分钟）。
  后台进程不会叫醒你，必须在自己的回合内循环等待到本轮结束再输出最终报告。

## 4. 必读（读之前先想清楚要提取什么）

1. COMMON `agent-memory/lessons/patterns-长周期生产巡检.md`（66 条）——所有口径与坑，尤其 5/6/9/10/16/20/22/24/27/30/33/37/48/52/56/59/61/62/63/64。
2. SPIDER `services/gateway/lifecycle/README.md` 的「动态 rps 守护」「线上观测脚本」两节。
3. SPIDER `scripts/lc_patrol_sample.sh`、`lc_window_stat.sh`、`lc_job_brief.sh`、`es_curl.sh` 头部注释。
