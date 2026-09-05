# -*- coding: utf-8 -*-
# 在已过 JS 挑战的 Chrome 页面上下文里 fetch 移动端 API（带全套挑战 cookie），
# 验证 m.ixigua.com/video/{id} 是否返回含 main_url 的真实数据。
import json
import urllib.request
import websocket

CTRL = "http://127.0.0.1:9789/json"
targets = json.load(urllib.request.urlopen(CTRL))
page = next(t for t in targets if t["type"] == "page")
print("page:", page["url"][:80])
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


expr = (
    "fetch('https://m.ixigua.com/video/7295466269036937786',{credentials:'include'})"
    ".then(r=>r.text()).then(t=>t.slice(0,800))"
)
res = cmd("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True})
val = res.get("result", {}).get("value", "")
print("FETCH_RESULT_HEAD:")
print(val)
print("HAS main_url:", "main_url" in val)
print("HAS videoResource:", "videoResource" in val)
