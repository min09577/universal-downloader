# -*- coding: utf-8 -*-
# 在已过挑战的浏览器上下文里，从西瓜「影视/放映厅」等还在运营的聚合页 HTML 里挖现存 item id。
import json
import time
import urllib.request
import websocket

CTRL = "http://127.0.0.1:9789/json"
targets = json.load(urllib.request.urlopen(CTRL))
page = next(t for t in targets if t["type"] == "page")
ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30)
mid = 0


def cmd(method, params=None):
    global mid
    mid += 1
    ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == mid:
            return msg.get("result", {})


cmd("Page.navigate", {"url": "https://www.ixigua.com/cinema/"})
time.sleep(10)
expr = (
    "(function(){"
    "var ids = (document.documentElement.innerHTML.match(/ixigua\\.com\\/(?:video\\/)?(\\d{15,})/g)||[]);"
    "return ids.slice(0, 20).join('|');"
    "})()"
)
res = cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True})
print("ids:", res.get("result", {}).get("value"))
