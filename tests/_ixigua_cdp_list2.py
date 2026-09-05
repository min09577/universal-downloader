# -*- coding: utf-8 -*-
import json, time, urllib.request, websocket
CTRL = "http://127.0.0.1:9789/json"
targets = json.load(urllib.request.urlopen(CTRL))
pages = [t for t in targets if t["type"] == "page"]
print("pages:", [t["url"][:70] for t in pages])
page = next(t for t in targets if t["type"] == "page" and "ixigua" in t["url"])
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
cmd("Network.enable")
cmd("Page.navigate", {"url": "https://www.ixigua.com/"})
urls = []
end = time.time() + 40
while time.time() < end:
    try:
        msg = json.loads(ws.recv())
    except Exception:
        break
    if msg.get("method") == "Network.responseReceived":
        u = msg["params"]["response"]["url"]
        if u.startswith("http") and not any(x in u for x in (".js",".css",".png",".webp",".avif",".gif",".ico",".woff","monitor","snssdk.com/v1/user","security.","abtest")):
            urls.append(u)
print("\n".join(urls[:50]))
