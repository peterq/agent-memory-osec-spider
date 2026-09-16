#!/usr/bin/env bash
# 用本机 fc-chrome(COMMON fc-chrome/bootstrap) + 本机 Chrome, 对云端文档爬虫脚本做端到端验证:
#   起 fc-chrome(:9000, 资产白名单放开 127.0.0.1) → 用 python http.server 托管 dist-cloud → localverify 以 inject 模式打开文档页,
#   等 [[DOC_SPIDER]] 协议终态。退出码 0 = 收到终态(result final / error)。
# 用法:
#   scripts/docspider/e2e-local-fcchrome.sh <文档URL> [脚本目录=userscripts-wt-qqdoc/dist-cloud] [超时秒=150]
# 前置: /usr/bin/google-chrome 可用; COMMON fc-chrome 已 make build 出 bootstrap; userscripts 已 pnpm build:cloud。
# 说明: 不会碰线上 FC 与线上 OSS 脚本; 线上验证请改用 procedures/workflow-fc-chrome上线.md 里的 wss 地址 + 测试 OSS 路径。
set -euo pipefail
PAGE=${1:?文档 URL}
DIST=${2:-/home/peterq/dev/projects/peterq/userscripts-wt-qqdoc/dist-cloud}
TIMEOUT=${3:-150}
FC_DIR=/home/peterq/dev/projects/1s/enfi-resource-common/fc-chrome
LOG_DIR=${LOG_DIR:-/tmp/docspider-e2e}; mkdir -p "$LOG_DIR"
PORT_HTTP=${PORT_HTTP:-8765}; PORT_FC=${PORT_FC:-9000}

# 1) fc-chrome(已在跑就复用)
if ! curl -sf "localhost:$PORT_FC/health" >/dev/null 2>&1; then
  (cd "$FC_DIR" && CHROME_PATH=/usr/bin/google-chrome FC_SERVER_PORT=$PORT_FC INSTANCE_RECYCLE_EVERY=0 \
     ALLOWED_ASSET_HOSTS=127.0.0.1,localhost nohup ./bootstrap >"$LOG_DIR/fcchrome.log" 2>&1 &)
  for _ in $(seq 1 20); do curl -sf "localhost:$PORT_FC/health" >/dev/null 2>&1 && break; sleep 0.5; done
fi
curl -sf "localhost:$PORT_FC/health" >/dev/null || { echo "fc-chrome 未就绪, 见 $LOG_DIR/fcchrome.log"; exit 2; }

# 2) 托管脚本目录(已在跑就复用)
if ! curl -sf "http://127.0.0.1:$PORT_HTTP/kdoc-cloud.user.js" >/dev/null 2>&1; then
  (cd "$DIST" && nohup python3 -m http.server "$PORT_HTTP" --bind 127.0.0.1 >"$LOG_DIR/http.log" 2>&1 &)
  sleep 0.5
fi
curl -sf "http://127.0.0.1:$PORT_HTTP/kdoc-cloud.user.js" >/dev/null || { echo "脚本未托管成功: $DIST/kdoc-cloud.user.js"; exit 2; }

# 3) localverify(inject 模式), nonce 随机, 输出落盘
NONCE="e2e-$(date +%s)-$RANDOM"
OUT="$LOG_DIR/verify-$(echo "$PAGE" | md5sum | cut -c1-8)-$(date +%H%M%S).log"
set +e
(cd "$FC_DIR" && go run ./cmd/localverify -mode inject -timeout "$TIMEOUT" \
   -fc "ws://127.0.0.1:$PORT_FC/chrome" -script "http://127.0.0.1:$PORT_HTTP/kdoc-cloud.user.js" \
   -page "$PAGE" -nonce "$NONCE") 2>&1 | tee "$OUT"
RC=${PIPESTATUS[0]}
set -e
echo "---- exit=$RC log=$OUT"
# 摘要: 终态 result 的 linkCount/docType, 或 error 的 message
grep -o '\[\[DOC_SPIDER\]\].*' "$OUT" | python3 -c '
import sys,json
for line in sys.stdin:
    try: d=json.loads(line[len("[[DOC_SPIDER]]"):])
    except Exception: continue
    ev=d.get("event")
    if ev=="result" and d.get("final"): print("RESULT docType=%s linkCount=%s version=%s docMtime=%s"%(d.get("docType"),d.get("linkCount"),d.get("version"),d.get("docMtime")))
    elif ev=="error": print("ERROR permanent=%s message=%s"%(d.get("permanent"),d.get("message")))
'
exit "$RC"
