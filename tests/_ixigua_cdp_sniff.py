
# -*- coding: utf-8 -*-
import json, time, base64, sys, urllib.request
import websocket  # websocket-client

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
def wait_event(name, timeout=40):
    ws.settimeout(timeout)
    end = time.time() + timeout
    while time.time() < end:
        try:
            msg = json.loads(ws.recv())
        except Exception:
            return None
        if msg.get("method") == name:
            return msg["params"]
    return None

cmd("Network.enable")
cmd("Page.enable")
cmd("Page.reload")
found = []
deadline = time.time() + 45
seen = set()
while time.time() < deadline:
    try:
        msg = json.loads(ws.recv())
    except Exception:
        break
    if msg.get("method") == "Network.responseReceived":
        resp = msg["params"]["response"]
        url = resp["url"]
        if ("play" in url or "video" in url or "stream" in url) and url not in seen:
            seen.add(url)
            body = cmd("Network.getResponseBody", {"requestId": msg["params"]["requestId"]})
            b = body.get("body", "")
            if "main_url" in b or "video_list" in b:
                found.append({"url": url[:120], "body": b[:100000]})
                print("CAPTURED:", url[:120], flush=True)
                if len(found) >= 3:
                    break
json.dump(found, open(r"C:\Users\Min\universal-downloader\tests\_ixigua_cdp_cap.json", "w", encoding="utf-8"), ensure_ascii=False)
print("saved", len(found), "responses")
