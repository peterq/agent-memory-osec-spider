#!/usr/bin/env bash
# 管理员邮件通知脚本(经 cf-worker 转发)
# 用法: scripts/notify-admin.sh "<主题>" "<html正文>" [source]
# 示例: scripts/notify-admin.sh "任务完成" "<p>队列监控系统已上线</p>" queue-admin
set -euo pipefail
SUBJECT="${1:?用法: notify-admin.sh <主题> <html正文> [source]}"
HTML="${2:?缺少 html 正文}"
SOURCE="${3:-agent-task}"
BODY=$(SUBJECT="$SUBJECT" HTML="$HTML" SOURCE="$SOURCE" python3 -c '
import json, os
print(json.dumps({"subject": os.environ["SUBJECT"],
                  "htmlContent": os.environ["HTML"],
                  "source": os.environ["SOURCE"]}))')
curl -sS -m 20 -X POST http://cf-worker.peterq.cn/notify_admin \
  -H 'Content-Type: application/json' --data "$BODY"
echo
