# -*- coding: utf-8 -*-
import json, time, urllib.request, websocket
CTRL = "http://127.0.0.1:9789/json"
targets = json.load(urllib.request.urlopen(CTRL))
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
urls, bodies = [], {}
end = time.time() + 35
while time.time() < end:
    try:
        msg = json.loads(ws.recv())
    except Exception:
        break
    if msg.get("method") == "Network.responseReceived":
        u = msg["params"]["response"]["url"]
        if "ixigua" in u and ("api" in u or "feed" in u or "list" in u):
            body = cmd("Network.getResponseBody", {"requestId": msg["params"]["requestId"]})
            b = body.get("body", "")
            if '"item_id' in b or '"itemId' in b or "videoResource" in b or "main_url" in b:
                urls.append(u)
                bodies[u] = b[:200000]
                print("HIT:", u[:100], "len:", len(b), flush=True)
json.dump(bodies, open(r"C:\Users\Min\universal-downloader\tests\_ixigua_feed_cap.json", "w", encoding="utf-8"), ensure_ascii=False)
print("total hits:", len(urls))
