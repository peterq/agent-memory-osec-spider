# 腾讯文档 sheet 区块 protobuf 结构化提取原型: 输出行文本 + 单元格类型分布
import sys,json,base64,zlib,re,struct,collections
exec(open('pbwalk.py').read().split("if __name__")[0])
def fields(b): 
    try: return parse(b)
    except Exception: return []
def get(items,f): return [v for ff,w,v in items if ff==f]
def first(items,f,default=None):
    l=get(items,f); return l[0] if l else default
def txt(b):
    try: return b.decode('utf-8')
    except: return ''
def rich_text(entry):
    # entry = f2 msg: repeated f3 run { f3{f1 text}, f7{f11{f1 url}} }
    s='';urls=[]
    for run in get(fields(entry),3):
        ri=fields(run)
        t=first(ri,3); 
        if t is not None: s+=txt(first(fields(t),1,b''))
        h=first(ri,7)
        if h is not None:
            u=first(fields(h),11)
            if u is not None:
                url=txt(first(fields(u),1,b''))
                if url: urls.append(url)
    for u in urls:
        if u not in s: s+='(%s)'%u
    return s
types=collections.Counter(); unknown=[]
def extract_block(inf):
    rows=collections.defaultdict(dict)
    top=first(parse(inf),1)
    for sec in get(fields(top),5):
        si=fields(sec)
        if first(si,1)!=18: continue
        p=fields(first(si,19))
        plain=[];rich=[]
        for f,w,v in p:
            if f==5:
                for ef,ew,ev in fields(v):
                    if ef==1: plain.append(txt(first(fields(ev),1,b'')))
                    elif ef==2: rich.append(rich_text(ev))
        for cell in get(p,6):
            ci=fields(cell); r=first(ci,1,0); c=first(ci,2,0)
            val=first(ci,3)
            if val is None: continue
            vi=fields(val); t=first(vi,1,0); types[t]+=1
            idxm=first(vi,2); idx=first(fields(idxm),1,0) if idxm else 0
            if t==4: s=plain[idx] if idx<len(plain) else '<?plain %d>'%idx
            elif t==6: s=rich[idx] if idx<len(rich) else '<?rich %d>'%idx
            else:
                s=None
                for ff,ww,vv in vi:
                    if ww=='f64': s=repr(struct.unpack('<d',vv)[0])
                if s is None:
                    s=''; unknown.append((t,[(ff,ww,vv if ww!='b' else vv[:30]) for ff,ww,vv in vi]))
            rows[r][c]=s
    return rows
LINK=re.compile(r'pan\.quark\.cn/s/[a-z\d]{5,32}|www\.(?:aliyundrive|alipan)\.com/s/[a-zA-Z\d]{5,}|pan\.baidu\.com/s/1[0-9a-zA-Z\-_]+|pan\.xunlei\.com/s/[a-zA-Z\d_\-]{5,}')
for fn in sys.argv[1:]:
    s=open(fn,encoding='utf-8').read(); d=json.loads(s[s.find('(')+1:s.rfind(')')])
    t=d['clientVars']['collab_client_vars']['initialAttributedText']['text'][0]
    allrows=0; links=set(); rawlinks=set()
    for b in t['block_datas']:
        inf=zlib.decompress(base64.b64decode(b['related_sheet']))
        rawlinks|=set(m.group(0) for m in LINK.finditer(inf.decode('utf-8','replace')))
        rows=extract_block(inf)
        for r in sorted(rows):
            line='\t'.join(rows[r][c] or '' for c in sorted(rows[r]))
            allrows+=1
            if allrows<=6: print('  row',r,':',line[:200])
            links|=set(m.group(0) for m in LINK.finditer(line))
    print(fn,'rows',allrows,'structured links',len(links),'raw links',len(rawlinks),'missing',len(rawlinks-links))
print('cell types',types); print('unknown samples',unknown[:5])
