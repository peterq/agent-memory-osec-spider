# 用本机 Chrome(headless) + CDP 把云端脚本注入(document-start), 打开页面, 抓 console 与 JS 异常, 用于排查"脚本注入后无回传"
# 用法: python3 cdp_inject_debug.py <script.user.js> <page url(不含 #taskNonce)> [等待秒=60]
import sys,json,subprocess,time,re,tempfile,urllib.request,websocket
script_path,page=sys.argv[1],sys.argv[2]; wait=int(sys.argv[3]) if len(sys.argv)>3 else 60
src=open(script_path,encoding='utf-8').read()
src=re.sub(r'^// ==UserScript==.*?// ==/UserScript==\s*','',src,flags=re.S)
prof=tempfile.mkdtemp(prefix='cdpdbg-')
port=9444
chrome=subprocess.Popen(['/usr/bin/google-chrome','--headless=new','--no-sandbox','--disable-gpu',f'--remote-debugging-port={port}',f'--user-data-dir={prof}','--no-first-run','--remote-allow-origins=*','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        try: ver=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version')); break
        except Exception: time.sleep(0.2)
    tgt=json.loads(urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}/json/new?about:blank',method='PUT')).read())
    ws=websocket.create_connection(tgt['webSocketDebuggerUrl'],timeout=5)
    mid=[0]
    def call(m,p=None):
        mid[0]+=1; ws.send(json.dumps({'id':mid[0],'method':m,'params':p or {}}))
        while True:
            r=json.loads(ws.recv())
            if r.get('id')==mid[0]: return r
            handle(r)
    def handle(ev):
        m=ev.get('method')
        if m=='Runtime.consoleAPICalled':
            args=[a.get('value',a.get('description','')) for a in ev['params']['args']]
            line=' '.join(str(a) for a in args)
            if '[[DOC_SPIDER]]' in line: print('[DOC_SPIDER]',line[:300])
        elif m=='Runtime.exceptionThrown':
            d=ev['params']['exceptionDetails']; print('[EXCEPTION]',d.get('text'),json.dumps(d.get('exception',{}),ensure_ascii=False)[:600],'url',d.get('url'),'line',d.get('lineNumber'))
        elif m in('Page.frameNavigated',):
            f=ev['params']['frame']; print('[NAV]',f.get('url')[:150],'parent' if f.get('parentId') else 'main')
    call('Page.enable'); call('Runtime.enable')
    call('Page.addScriptToEvaluateOnNewDocument',{'source':src,'runImmediately':True})
    call('Page.navigate',{'url':page+'#taskNonce=dbg-'+str(int(time.time()))})
    ws.settimeout(1); end=time.time()+wait
    while time.time()<end:
        try: handle(json.loads(ws.recv()))
        except websocket.WebSocketTimeoutException: pass
    r=call('Runtime.evaluate',{'expression':'JSON.stringify({href:location.href,hash:location.hash,ls:localStorage.getItem("__doc_spider_pending_nonce__"),cookie:document.cookie.slice(0,200)})','returnByValue':True})
    print('[STATE]',r.get('result',{}).get('result',{}).get('value'))
finally:
    chrome.terminate()
