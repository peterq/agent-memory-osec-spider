#!/usr/bin/env bash
# 迅雷分享探针: 经线上 v2xlLoadShare/v2aliLoadShare 进程的 :9527 调试代理(走代理池), 用爬虫同款
# device/client 头部取一次验证码 token, 查分享信息 + 首个顶层文件夹的目录详情, 输出原始 JSON 与摘要.
# 用途: 排查 xlLoadShare 失败(顶层结构/空文件夹/分享状态码), 不依赖远端 python.
# 用法: scripts/xl_share_probe.sh <host> <shareId> [pwd]      host 如 osec-jenkins / osec-resngix
#       只想要原始 JSON 加 RAW=1
set -u
host=$1; sid=$2; pw=${3:-}
# 迅雷客户端标识常量从 SPIDER 源码 newCommon/refreshCaptchaToken 读取, 不在本仓库落明文
XL_SRC=${XL_SRC:-/home/peterq/dev/projects/1s/osec-spider-go/services/xunlei-pan/xl-client.go}
DEV=$(grep -m1 'DeviceID:' "$XL_SRC" | sed -E 's/.*"([^"]+)".*/\1/'); CID=$(grep -m1 'ClientID:' "$XL_SRC" | sed -E 's/.*"([^"]+)".*/\1/')
CVER=$(grep -m1 'ClientVersion:' "$XL_SRC" | sed -E 's/.*"([^"]+)".*/\1/'); SIGN=$(grep -m1 '"captcha_sign":' "$XL_SRC" | sed -E 's/.*:\s*"([^"]+)".*/\1/')
[ -z "$DEV$CID$CVER$SIGN" ] && { echo "未能从 $XL_SRC 读到迅雷客户端常量"; exit 1; }
remote='
P=http://127.0.0.1:9527/proxy; sid="$1"; pw="$2"; DEV="$3"; CID="$4"; CVER="$5"; SIGN="$6"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
H=(-H "X-Device-Id: $DEV" -H "X-Client-Id: $CID" -H "X-Client-Version: $CVER" -H "User-Agent: $UA")
tok() { curl -s -m 30 "${H[@]}" -H "Content-Type: application/json" -X POST "$P?method=POST&url=https%3A%2F%2Fxluser-ssl.xunlei.com%2Fv1%2Fshield%2Fcaptcha%2Finit" -d "{\"client_id\":\"$CID\",\"device_id\":\"$DEV\",\"action\":\"get:/drive/v1/share\",\"meta\":{\"package_name\":\"pan.xunlei.com\",\"client_version\":\"$CVER\",\"captcha_sign\":\"$SIGN\",\"timestamp\":\"1645241033384\"}}" | sed -nE "s/.*\"captcha_token\":\"([^\"]+)\".*/\1/p"; }
TOK=$(tok); [ -z "$TOK" ] && { sleep 2; TOK=$(tok); }; [ -z "$TOK" ] && { sleep 3; TOK=$(tok); }
[ -z "$TOK" ] && { echo "@@ERR 取验证码 token 失败"; exit 1; }
for i in 1 2 3; do S=$(curl -s -m 30 "${H[@]}" -H "X-Captcha-Token: $TOK" "$P?method=GET&url=https%3A%2F%2Fapi-pan.xunlei.com%2Fdrive%2Fv1%2Fshare%3Fshare_id%3D$sid%26pass_code%3D$pw%26limit%3D100"); case "$S" in \{*) break;; esac; sleep 1; done
echo "@@SHARE"; echo "$S"
PCT=$(echo "$S" | sed -nE "s/.*\"pass_code_token\":\"([^\"]*)\".*/\1/p" | sed "s/+/%252B/g; s/\//%252F/g; s/=/%253D/g")  # 双重编码: 调试代理先解一层, 目标站再解一层
FID=$(echo "$S" | grep -o "\"kind\":\"drive#folder\",\"id\":\"[^\"]*\"" | head -1 | sed -E "s/.*\"id\":\"([^\"]*)\"/\1/")
if [ -n "$FID" ]; then
  for i in 1 2 3; do D=$(curl -s -m 30 "${H[@]}" -H "X-Captcha-Token: $TOK" "$P?method=GET&url=https%3A%2F%2Fapi-pan.xunlei.com%2Fdrive%2Fv1%2Fshare%2Fdetail%3Fshare_id%3D$sid%26parent_id%3D$FID%26pass_code_token%3D$PCT%26limit%3D100%26thumbnail_size%3DSIZE_SMALL"); case "$D" in \{*) break;; esac; sleep 1; done
  echo "@@DETAIL $FID pct=$PCT"; echo "$D"
fi'
out=$(ssh -o ConnectTimeout=15 "$host" "bash -s -- '$sid' '$pw' '$DEV' '$CID' '$CVER' '$SIGN'" <<<"$remote")
if [ "${RAW:-}" = 1 ]; then echo "$out"; exit 0; fi
python3 - "$out" <<'PY'
import sys,json,re
txt=sys.argv[1]
if txt.startswith('@@ERR'): print(txt); sys.exit(1)
share=re.search(r'@@SHARE\n(.*?)(?=\n@@|\Z)',txt,re.S); det=re.search(r'@@DETAIL (\S+) pct=\S*\n(.*)',txt,re.S)
def load(s):
    try: return json.loads(s)
    except Exception: return {'error':'非JSON','error_description':s[:200]}
d=load(share.group(1))
if 'error' in d: print('分享接口错误:',d.get('error'),d.get('error_description')); sys.exit(1)
fs=d.get('files',[])
print(f"分享状态={d.get('share_status')} 标题={d.get('title')!r} file_num={d.get('file_num')} 顶层条目={len(fs)}")
for f in fs: print(f"  {f.get('kind')}  {f.get('name')!r}  size={f.get('size')}  audit={f.get('audit',{}).get('status')}")
if det:
    dd=load(det.group(2)); n=dd.get('files',[])
    print(f"首个文件夹 {det.group(1)} 详情: 状态={dd.get('share_status')} 文件数={len(n)} 错误={dd.get('error')}")
    for f in n[:5]: print(f"  {f.get('kind')}  {f.get('name')!r}  size={f.get('size')}")
    if len(n)>5: print(f"  ... 共 {len(n)} 项")
PY
