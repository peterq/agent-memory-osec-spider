#!/usr/bin/env bash
# 网盘「分享链接文件转存 → 链接解析 → 下载上传 OSS」链路体检（只读）
# 用法: scripts/dl_chain_health.sh [--no-mysql]
# 依赖: ssh 免密到 osec-res1/res2/resdb; 线上口令从 SPIDER/_note/config/spider.prod.yaml 读取, 不回显
# 输出: 进程/容器状态、worker 近 N 小时日志统计、账号池与队列积压(redis)、最新下载组进度(mysql)
set -uo pipefail
SPIDER=${SPIDER_ROOT:-/home/peterq/dev/projects/1s/osec-spider-go}
CONF="$SPIDER/_note/config/spider.prod.yaml"
SINCE=${SINCE:-72h}
NO_MYSQL=0; [[ "${1:-}" == "--no-mysql" ]] && NO_MYSQL=1
SSH="ssh -o ConnectTimeout=15 -o BatchMode=yes"

# redis(db1)口令与 mysql DSN 只进变量, 不打印
RPW=$(awk '/^redises:/{f=1} f&&/password:/{print $2; exit}' "$CONF")
DSN=$(grep -m1 "mysql:" "$CONF" | sed -E 's/^ *mysql: *//')
MU=${DSN%%:*}; MR=${DSN#*:}; MP=${MR%%@tcp(*}
MH=$(echo "$DSN" | sed -E 's/.*@tcp\(([^)]*)\).*/\1/'); MH=${MH%%:*}
MDB=$(echo "$DSN" | sed -E 's/.*\)\/([^?]*).*/\1/')
RCLI="sudo docker exec -e REDISCLI_AUTH=$RPW enfi-spider-redis redis-cli -h 192.168.7.145 -p 16379 -n 6"

echo "### 1. 容器与日志（近 $SINCE）"
for pair in "osec-res2 spider-share_download_resolve_link" "osec-res1 spider-share_download_download" "osec-resdb spider-share_download_push_resolve_ali_250918"; do
  set -- $pair
  echo "-- $1 / $2"
  timeout 90 $SSH "$1" "sudo docker ps --filter name=$2 --format '   状态: {{.Status}}'; \
    L=\$(sudo docker logs --since $SINCE $2 2>&1); \
    echo \"   日志行=\$(echo \"\$L\" | grep -c .) 错误行=\$(echo \"\$L\" | grep -c '\[error\]') 空闲行=\$(echo \"\$L\" | grep -c 'no available') refreshToken失效=\$(echo \"\$L\" | grep -c 'InvalidParameter.RefreshToken')\"; \
    echo '   最近 3 条错误:'; echo \"\$L\" | grep '\[error\]' | tail -3 | cut -c1-160 | sed 's/^/     /'" 2>&1 | grep -v '^Warning'
done

echo "### 2. 账号池与队列（redis db6）"
timeout 90 $SSH osec-res1 "R='$RCLI'; \
  for t in ali-share bnd; do echo \"-- \$t 账号: 配置 \$(\$R hlen downloadScheduler:account_conf:\$t) / 有错误标记 \$(\$R hlen downloadScheduler:account_error:\$t)\"; \
    \$R hgetall downloadScheduler:account_error:\$t | paste - - | awk -F'\t' '{print \"     \" substr(\$1,1,8) \" \" substr(\$2,1,25) \" \" substr(\$2,26,60)}' | sort -k2; done; \
  echo '-- 队列(waiting/pending; 空 zset 会被 redis 删除, none=0):'; \
  for q in aliAcc aliResolve2 aliDownload bndAcc bndResolve2 bndDownload; do for s in waiting pending; do k=\"queue:{downloadScheduler:\$q}:\$s\"; n=\$(\$R zcard \"\$k\"); \
    first=\$(\$R zrange \"\$k\" 0 0 withscores | tail -1); age=''; if [ -n \"\$first\" ]; then ms=\$(( first & ((1<<48)-1) )); age=\"最早入队 \$(date -d @\$((ms/1000)) '+%F %T')\"; fi; \
    printf '     %-45s %6s  %s\n' \"\$k\" \"\$n\" \"\$age\"; done; done" 2>&1 | grep -v '^Warning'

if [[ $NO_MYSQL -eq 0 ]]; then
  echo "### 3. 最新下载组进度（mysql, 组名按建表时间取最新）"
  timeout 120 $SSH osec-res1 "export MYSQL_PWD='$MP'; T=\$(mysql -h $MH -u $MU $MDB -N -e \"select table_name from information_schema.tables where table_schema='$MDB' and table_name like 'download_file_%' order by create_time desc limit 1\" 2>/dev/null); \
    S=\${T/download_file_/download_share_file_}; echo \"   组表: \$T (建于 \$(mysql -h $MH -u $MU $MDB -N -e \"select create_time from information_schema.tables where table_schema='$MDB' and table_name='\$T'\" 2>/dev/null))\"; \
    mysql -h $MH -u $MU $MDB -e \"select 'share_file' k, count(*) cnt, null size_gb from \$S union all select concat('download_file saved=',saved), count(*), round(sum(size)/1024/1024/1024,1) from \$T group by saved\" 2>/dev/null | sed 's/^/   /'"
fi
