#!/usr/bin/env python3
"""通过 Chrome DevTools Protocol 驱动 scripts/agent-browser.sh 启动的调试浏览器。

依赖: python3 的 websockets 包(本机已装)。默认连 127.0.0.1:9222, 可用 AGENT_BROWSER_PORT 覆盖。

用法:
    ./scripts/cdp.py tabs                        # 列出页面标签(序号/标题/地址)
    ./scripts/cdp.py nav <url> [--tab N]         # 当前(或第 N 个)标签导航到 url 并等加载完成
                                                 # --tab 也可给 tabs 输出的 target id(前缀即可), 多会话共用浏览器时序号会漂移
    ./scripts/cdp.py new <url>                   # 新开标签
    ./scripts/cdp.py eval '<js 表达式>' [--tab N] # 在页面里求值, 打印 JSON 结果(支持 await)
    ./scripts/cdp.py text [--tab N] [--max 4000] # 打印 body.innerText
    ./scripts/cdp.py shot <文件路径> [--tab N]    # 截图存为 png

说明:
- eval 的表达式会被包进 async 函数, 因此可以直接写 `await fetch(...)` 这类异步代码;
  返回值必须能 JSON 序列化(DOM 节点请自己取属性)。
- 页面里输入表单的可靠做法: 用 eval 直接设 value 再派发 input/change 事件(见本文件末尾示例)。
"""
import asyncio
import json
import os
import sys
import urllib.request

import websockets

PORT = os.environ.get("AGENT_BROWSER_PORT", "9222")
BASE = f"http://127.0.0.1:{PORT}"


def http_json(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        return json.loads(r.read().decode())


def pages():
    return [t for t in http_json("/json/list") if t.get("type") == "page"]


async def send(ws, method, params=None, _id=[0]):
    _id[0] += 1
    mid = _id[0]
    await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("id") == mid:
            if "error" in msg:
                raise RuntimeError(msg["error"])
            return msg.get("result", {})


async def with_page(idx, fn):
    ps = pages()
    if not ps:
        raise SystemExit("没有可用的页面标签, 先跑 ./scripts/agent-browser.sh start")
    # --tab 既可以是序号, 也可以是 /json/list 里的 target id(浏览器被多个会话共用时序号会漂移, 用 id 更稳)
    if isinstance(idx, str):
        found = [t for t in ps if t["id"] == idx or t["id"].startswith(idx)]
        if not found:
            raise SystemExit("找不到 id 为 %s 的标签, 用 tabs 命令查看" % idx)
        target = found[0]
    else:
        target = ps[idx]
    async with websockets.connect(target["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024) as ws:
        return await fn(ws)


async def do_eval(ws, expr, await_promise=True):
    wrapped = "(async () => { return (%s) })()" % expr
    res = await send(ws, "Runtime.evaluate", {
        "expression": wrapped,
        "awaitPromise": await_promise,
        "returnByValue": True,
        "userGesture": True,
    })
    if "exceptionDetails" in res:
        d = res["exceptionDetails"]
        raise RuntimeError(d.get("exception", {}).get("description") or d.get("text"))
    return res.get("result", {}).get("value")


async def wait_load(ws, timeout=30):
    """轮询 document.readyState, 比监听事件简单可靠(导航后 execution context 会换)。"""
    for _ in range(timeout * 4):
        await asyncio.sleep(0.25)
        try:
            if await do_eval(ws, "document.readyState") == "complete":
                return True
        except Exception:
            continue
    return False


def arg(flag, default=None, cast=str):
    if flag in sys.argv:
        return cast(sys.argv[sys.argv.index(flag) + 1])
    return default


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    tab_raw = arg("--tab", "0")
    tab = int(tab_raw) if tab_raw.isdigit() else tab_raw

    if cmd == "tabs":
        for i, t in enumerate(pages()):
            print(i, "|", t["id"][:8], "|", (t.get("title") or "")[:60], "|", (t.get("url") or "")[:120])
        return

    if cmd == "new":
        url = sys.argv[2]
        req = urllib.request.Request(BASE + "/json/new?" + urllib.parse.quote(url, safe=""), method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                print(json.loads(r.read().decode()).get("id"))
        except urllib.error.HTTPError:
            with urllib.request.urlopen(BASE + "/json/new?" + url, timeout=10) as r:
                print(json.loads(r.read().decode()).get("id"))
        return

    async def run(ws):
        if cmd == "nav":
            await send(ws, "Page.navigate", {"url": sys.argv[2]})
            ok = await wait_load(ws)
            print(json.dumps({"loaded": ok, "url": await do_eval(ws, "location.href")}, ensure_ascii=False))
        elif cmd == "eval":
            print(json.dumps(await do_eval(ws, sys.argv[2]), ensure_ascii=False, indent=2))
        elif cmd == "text":
            mx = arg("--max", 4000, int)
            print((await do_eval(ws, "document.body.innerText"))[:mx])
        elif cmd == "shot":
            res = await send(ws, "Page.captureScreenshot", {"format": "png"})
            import base64
            open(sys.argv[2], "wb").write(base64.b64decode(res["data"]))
            print(sys.argv[2])
        else:
            raise SystemExit("未知命令: " + cmd)

    asyncio.run(with_page(tab, run))


if __name__ == "__main__":
    import urllib.parse  # noqa: E402  (new 命令用)
    main()

# 表单填写示例(供后续 Agent 复用):
#   ./scripts/cdp.py eval '(() => {
#      const el = document.querySelector("#oauth_application_name");
#      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
#      setter.call(el, "nc-admin");
#      el.dispatchEvent(new Event("input", {bubbles:true}));
#      return el.value;
#   })()'
