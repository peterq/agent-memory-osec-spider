# 通用取数: python3 qqfetch.py <docid> <tab> <startrow> <endrow> <out.js> [block_start_row block_end_row]
import sys,json,urllib.request,http.cookiejar
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
docid,tab,sr,er,out=sys.argv[1:6]; bs=sys.argv[6] if len(sys.argv)>6 else '0'; be=sys.argv[7] if len(sys.argv)>7 else '1999'
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
r=op.open(urllib.request.Request('https://docs.qq.com/sheet/'+docid,headers={'User-Agent':UA}),timeout=30); r.read()
u='https://docs.qq.com/dop-api/opendoc?id=%s&tab=%s&normal=1&outformat=1&wb=1&nowb=0&noEscape=1&enableSmartsheetSplit=1&needSheetState=1&sliceStates=1&startrow=%s&endrow=%s&block_start_col=0&block_end_col=16383&block_start_row=%s&block_end_row=%s&callback=clientVarsCallback&xsrf='%(docid,tab,sr,er,bs,be)
body=op.open(urllib.request.Request(u,headers={'User-Agent':UA,'Referer':'https://docs.qq.com/sheet/'+docid}),timeout=60).read().decode()
open(out,'w').write(body)
d=json.loads(body[body.find('(')+1:body.rfind(')')]); cv=d.get('clientVars',{}); ccv=cv.get('collab_client_vars') or {}
iat=ccv.get('initialAttributedText') or {}
t=(iat.get('text') or [None])[0]
info={'dver':d.get('dver'),'padType':d.get('padType'),'retcode':cv.get('retcode'),'title':cv.get('title'),'padSubId':ccv.get('padSubId'),'maxRow':ccv.get('maxRow'),'sheets':len(ccv['header'][0]['d']) if ccv.get('header') else None,'text0':type(t).__name__,'bytes':len(body)}
if isinstance(t,list):
    import re
    rng=[op['c'][0] for grp in t if isinstance(grp,list) for op in grp if isinstance(op,dict) and op.get('t')==3]
    info['type3_ranges']=rng[:5]; info['type3_count']=len(rng)
    s=json.dumps(t,ensure_ascii=False); info['ids']=len(set(re.findall(r'(?:pan\.quark\.cn/s/|(?:aliyundrive|alipan)\.com/s/|pan\.baidu\.com/s/|pan\.xunlei\.com/s/)([a-zA-Z\d_\-]{5,})',s)))
elif isinstance(t,dict):
    info['max_row']=t.get('max_row'); info['blocks']=[(b.get('start_row_index'),b.get('end_row_index')) for b in t.get('block_datas',[])]
print(out,json.dumps(info,ensure_ascii=False))
