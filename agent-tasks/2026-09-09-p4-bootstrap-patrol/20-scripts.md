# 20-scripts —— 固化取证用的只读对拍脚本（Sonnet）

先读 00-shared.md §2 硬性约束（尤其：任何凭据片段不得出现在代码、注释、提交、输出里）。

## 来源

取证 Agent 留在 scratchpad 的三个临时脚本（只读，已在生产验证）：
- `/tmp/claude-1000/-home-peterq-dev-projects-1s-enfi-resource-common/99c08a5e-e35a-431b-9d5c-d648bed77429/scratchpad/mysql_ro.sh`
  —— 经跳板 osec-res1 的 mysql 客户端执行**只读 SELECT**（有只读守卫 + DSN 脱敏），DSN 从 `_note/config/spider.prod.yaml` 现读（`^\s*mysql:`，值用 `[^"]+`，口令含 `#`）。
- `.../scratchpad/es_ids_probe.sh` —— 用 `ids` 查询按 1000/批探测一批 id 在某索引/别名是否存在（ssh ControlMaster 复用，0.3 s/批）。
- `.../scratchpad/db_lookup.py` —— 按 `bucket=int(id[0:2],16)%16` 分桶反查 DB 行（只查 4 张表）。

## 任务

1. 把三者整理为 SPIDER `scripts/lc_mysql_ro.sh`、`scripts/lc_es_ids_probe.sh`、`scripts/lc_db_lookup.py`：
   - 头部中文注释：用途、用法、口径、来源（2026-09-11 P4 id=8 校验取证）、安全说明（只读、脱敏）。
   - `lc_mysql_ro.sh` 必须保留只读守卫（拒绝非 SELECT/SHOW/EXPLAIN）与输出打码；DSN 解析同 `scripts/lc_rollback_repair_marked.sh` 的风格但修正两处坑（缩进、`#`）。
   - 不要硬编码任何主机 IP、账号、口令、索引凭据；跳板主机名用 `osec-res1`/`osec-res2`。
2. 在 `services/gateway/lifecycle/README.md`「线上观测脚本」表格追加三行，并加一小节「bootstrap verify 失败后的只读对拍」：
   两索引 DB/ES 对拍 SQL 与 `_count` 查询、`CRC32(id)%N` 抽样、双向抽样要点（参考 COMMON `agent-memory/lessons/patterns-长周期生产巡检.md` #85~#89）。
3. 本地静态检查：`bash -n` 三个 sh、`python3 -m py_compile`；**不要连生产执行**（只做语法与 `--help`/无参用法输出）。
4. 提交：只 `git add` 这 4 个文件（仓库里有用户未提交的 `.vscode/launch.json`，不要碰），commit 信息中文，`git pull --rebase --autostash` 后 push。

## 交付

汇报：三个脚本路径与各自的用法一行、README 改动位置、提交 hash、静态检查结果。
