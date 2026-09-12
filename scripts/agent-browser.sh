#!/usr/bin/env bash
# 供 Agent 复用的 Chrome 调试会话
#
# 背景: Chrome 出于安全策略, 默认 profile(~/.config/google-chrome) 上开 --remote-debugging-port
# 会被拦截并提示换 user-data-dir。所以这里用项目内的独立 profile 目录, 人工登录一次(GitHub / 各种
# 后台)之后长期复用, 后续 Agent 需要"带登录态的浏览器"时直接连 9222, 不用重复人工授权。
#
# profile 目录 .agent-browser/profile 已在 .gitignore 中排除(含 cookie 等敏感数据, 严禁提交)。
#
# 用法:
#   ./scripts/agent-browser.sh start [url]   # 启动(已在跑则不重复启动)
#   ./scripts/agent-browser.sh status        # 查看调试端口是否可用
#   ./scripts/agent-browser.sh stop          # 关闭
#   ./scripts/agent-browser.sh tabs          # 列出当前标签页(id/title/url)
set -euo pipefail

PORT="${AGENT_BROWSER_PORT:-9222}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="$ROOT/.agent-browser/profile"
LOG="$ROOT/.agent-browser/chrome.log"
CHROME="${CHROME_BIN:-$(command -v google-chrome || command -v google-chrome-stable || command -v chromium)}"

case "${1:-start}" in
  start)
    if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
      echo "已在运行: http://127.0.0.1:$PORT"
      exit 0
    fi
    mkdir -p "$PROFILE"
    # DISPLAY 缺省取 :1(本机图形会话); 无图形环境时可自行导出 DISPLAY 或加 --headless=new
    export DISPLAY="${DISPLAY:-:1}"
    nohup "$CHROME" \
      --remote-debugging-port="$PORT" \
      --user-data-dir="$PROFILE" \
      --no-first-run --no-default-browser-check \
      --disable-features=Translate \
      "${2:-about:blank}" >"$LOG" 2>&1 &
    for _ in $(seq 1 30); do
      sleep 0.5
      curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1 && { echo "已启动: http://127.0.0.1:$PORT"; exit 0; }
    done
    echo "启动超时, 看日志: $LOG" >&2; exit 1
    ;;
  status)
    curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" || { echo "未运行"; exit 1; }
    ;;
  tabs)
    curl -s --max-time 3 "http://127.0.0.1:$PORT/json/list" |
      python3 -c 'import json,sys;[print(t["id"],"|",t.get("title","")[:60],"|",t.get("url","")[:120]) for t in json.load(sys.stdin) if t.get("type")=="page"]'
    ;;
  stop)
    pkill -f -- "--user-data-dir=$PROFILE" && echo "已关闭" || echo "未在运行"
    ;;
  *) echo "用法: $0 {start|status|tabs|stop}" >&2; exit 2 ;;
esac
