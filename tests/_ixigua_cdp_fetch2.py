# -*- coding: utf-8 -*-
# 导航到真实视频页等待加载完成，再在页面上下文里 fetch 移动 API 并搜索视频数据。
import json
import time
import urllib.request
import websocket

CTRL = "http://127.0.0.1:9789/json"
targets = json.load(urllib.request.urlopen(CTRL))
page = next(t for t in targets if t["type"] == "page")
ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30)
mid = 0


def cmd(method, params=None, wait=True):
    global mid
    mid += 1
    ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    if not wait:
        return {}
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == mid:
            return msg.get("result", {})


cmd("Page.navigate", {"url": "https://www.ixigua.com/7295466269036937786"})
time.sleep(10)

expr = (
    "fetch('https://m.ixigua.com/video/7295466269036937786',{credentials:'include'})"
    ".then(r=>r.status+'|LEN|'+String(r.text()).length)"
)
res = cmd("Runtime.evaluate", {
    "expression": "fetch('https://m.ixigua.com/video/7295466269036937786',{credentials:'include'}).then(r=>r.text()).then(t=>{window.__cap=t; return 'STATUS_OK len='+t.length+' main_url='+(t.indexOf('main_url')>=0)+' videoResource='+(t.indexOf('videoResource')>=0)+' httpStatus404='+(t.indexOf('httpStatus\\\":404')>=0||t.indexOf('\"httpStatus\":404')>=0)})",
    "awaitPromise": True, "returnByValue": True})
print("probe:", res.get("result", {}).get("value"))
res2 = cmd("Runtime.evaluate", {"expression": "window.__cap ? window.__cap.slice(0,700) : 'no cap'", "returnByValue": True})
print("body head:", res2.get("result", {}).get("value", "")[:700])
