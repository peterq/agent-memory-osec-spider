#!/usr/bin/env bash
# 以 Remote Control 模式后台启动当前工作空间的 Claude Code 会话
# (主目录 = 本记忆仓库, --add-dir 挂上 1s 下的五个业务仓库), 日志写 rc.log
# 用法: scripts/claude-rc.sh [会话名] [permission-mode]   默认: osec-spider / auto
# 环境变量 ONE_S_ROOT 可覆盖 1s 仓库根目录
# 停止: pkill -f 'claude --remote-control osec-spider'
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ONE_S="${ONE_S_ROOT:-/home/peterq/dev/projects/1s}"
NAME="${1:-osec-spider}"
MODE="${2:-auto}"
cd "$ROOT"
nohup claude --remote-control "$NAME" --permission-mode "$MODE" \
  --add-dir "$ONE_S/enfi-resource-common" \
            "$ONE_S/osec-spider-go" \
            "$ONE_S/osec-resource-api" \
            "$ONE_S/enfi-resource-storage" \
            "$ONE_S/nc-js" \
  > "$ROOT/rc.log" 2>&1 &
echo "已后台启动 (pid $!), 日志: $ROOT/rc.log"
