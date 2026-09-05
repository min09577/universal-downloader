# -*- coding: utf-8 -*-
import json, time, urllib.request, websocket, base64
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
cmd("Page.reload")
end = time.time() + 35
out = []
while time.time() < end:
    try:
        msg = json.loads(ws.recv())
    except Exception:
        break
    if msg.get("method") == "Network.responseReceived":
        u = msg["params"]["response"]["url"]
        if "/video/" in u and "ixigua" in u:
            body = cmd("Network.getResponseBody", {"requestId": msg["params"]["requestId"]})
            b = body.get("body", "")
            if body.get("base64Encoded"):
                b = base64.b64decode(b).decode("utf-8", "replace")
            out.append({"url": u, "body": b})
            print("captured:", u, "len:", len(b))
            break
json.dump(out, open(r"C:\Users\Min\universal-downloader\tests\_ixigua_api_cap.json", "w", encoding="utf-8"), ensure_ascii=False)
print("saved", len(out))
