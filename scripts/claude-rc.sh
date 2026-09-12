#!/usr/bin/env bash
# 前台启动本工作空间的 Claude Code Remote Control 服务(headless, 无需 TTY / nohup)。
# 主目录 = 本记忆仓库; 1s 下五个业务仓库通过 .claude/settings.local.json 的
# permissions.additionalDirectories 挂载(`claude remote-control` 子命令不支持 --add-dir)。
# 由 systemd 用户服务 scripts/claude-rc.service 托管(后台/开机自启/日志 rc.log):
#   systemctl --user enable --now "$PWD/scripts/claude-rc.service"   # 首次
#   systemctl --user status|restart|stop claude-rc
#   loginctl enable-linger "$USER"                                      # 开机无需登录即启动
# 前置: 该目录必须已在终端里跑过一次 `claude` 并接受信任对话框, 否则报 "Workspace not trusted"。
# 手工前台运行: scripts/claude-rc.sh [会话名] [permission-mode]   默认: osec-spider / 沿用全局默认
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
NAME="${1:-osec-spider}"
MODE="${2:-}"
cd "$ROOT"
exec claude remote-control --name "$NAME" ${MODE:+--permission-mode "$MODE"}
