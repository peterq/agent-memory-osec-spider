# 通用 protobuf wire-format 遍历: 打印字段树, 用于摸清腾讯文档 sheet 区块结构
import sys,json,base64,zlib
def varint(b,i):
    r=0;s=0
    while True:
        c=b[i];i+=1;r|=(c&0x7f)<<s;s+=7
        if c<0x80: return r,i
def parse(b):
    i=0;out=[]
    while i<len(b):
        tag,i=varint(b,i);f=tag>>3;w=tag&7
        if w==0: v,i=varint(b,i);out.append((f,'v',v))
        elif w==1: out.append((f,'f64',b[i:i+8]));i+=8
        elif w==5: out.append((f,'f32',b[i:i+4]));i+=4
        elif w==2:
            l,i=varint(b,i);d=b[i:i+l];i+=l
            if i>len(b): raise ValueError('overrun')
            out.append((f,'b',d))
        else: raise ValueError('bad wire %d'%w)
    return out
def is_text(d):
    try: s=d.decode('utf-8')
    except: return False
    return all(ch>=' ' or ch in '\n\r\t' for ch in s)
def dump(b,depth=0,maxdepth=8,limit=40,out=None):
    try: items=parse(b)
    except Exception: return False
    cnt={}
    for f,w,v in items:
        cnt[f]=cnt.get(f,0)+1
        if cnt[f]>limit: continue
        pre='  '*depth+'f%d'%f
        if w=='v': print(pre,'=',v)
        elif w in('f64','f32'): print(pre,w,v.hex())
        else:
            if len(v)==0: print(pre,'b empty')
            elif is_text(v) and (len(v)<3 or not looks_msg(v)): print(pre,'str',repr(v.decode('utf-8'))[:120])
            elif depth<maxdepth and looks_msg(v):
                print(pre,'msg(%d)'%len(v)); dump(v,depth+1,maxdepth,limit)
            else: print(pre,'bytes',len(v),v[:20].hex())
    return True
def looks_msg(v):
    try:
        items=parse(v)
        return all(1<=f<100 for f,_,_ in items) and len(items)>0
    except Exception: return False
if __name__=='__main__':
    src=sys.argv[1]; which=sys.argv[2] if len(sys.argv)>2 else 'block0'
    s=open(src,encoding='utf-8').read(); d=json.loads(s[s.find('(')+1:s.rfind(')')])
    t=d['clientVars']['collab_client_vars']['initialAttributedText']['text'][0]
    b64=t['workbook'] if which=='workbook' else t['block_datas'][int(which[5:])]['related_sheet']
    inf=zlib.decompress(base64.b64decode(b64)); open(which+'.bin','wb').write(inf)
    dump(inf,limit=int(sys.argv[3]) if len(sys.argv)>3 else 12)
