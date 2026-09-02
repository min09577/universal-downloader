# -*- coding: utf-8 -*-
"""
从本机 Chrome 拉取小红书 cookie（用户已授权）。
原理: 复制 Chrome profile 的 Cookies/Network 数据库(绕开运行中的文件锁)
      → 无头 Chrome 加载该副本并开调试端口 → CDP 取解密后的 cookie。
产物: tests/cookies_xhs.txt (已被 .gitignore 排除, 不会进 git)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket  # websocket-client

HERE = Path(__file__).parent
OUT = HERE / "cookies_xhs.txt"

CHROME_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
]
PROFILE_DIRS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Default",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Profile 1",
]
DB_RELATIVES = ["Network/Cookies", "Cookies"]
PORT = 9777


def find_chrome():
    for p in CHROME_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("找不到 chrome.exe")


def copy_cookie_db(tmp: Path):
    for prof in PROFILE_DIRS:
        if not prof.exists():
            continue
        for rel in DB_RELATIVES:
            src = prof / rel
            if src.exists():
                dst = tmp / "User Data/Default" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                return prof.parent  # User Data 目录, 作为 --user-data-dir
    raise FileNotFoundError("找不到 Chrome Cookies 数据库")


def cdp(ws_url, cmd_id, method, params=None):
    ws = websocket.create_connection(ws_url, timeout=10)
    try:
        ws.send(json.dumps({"id": cmd_id, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == cmd_id:
                return msg
    finally:
        ws.close()


def main():
    chrome = find_chrome()
    tmp = Path(tempfile.mkdtemp(prefix="chrome_cookie_pull_"))
    user_data = copy_cookie_db(tmp)
    print(f"[1] cookie库副本: {tmp}")

    proc = subprocess.Popen(
        [str(chrome), "--headless=new", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={user_data}", "--no-first-run", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # 等调试端口就绪
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version") as r:
                    r.read()
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("调试端口未就绪")

        # 直接走 browser 端 Storage.getCookies（应用级加密由 Chrome 自己解）
        ver = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version").read())
        ws_url = ver["webSocketDebuggerUrl"]
        resp = cdp(ws_url, 1, "Storage.getCookies", {"browserContextId": None})
        cookies = resp.get("result", {}).get("cookies", [])

        xs = [c for c in cookies if "xiaohongshu.com" in c.get("domain", "")]
        print(f"[2] 共 {len(cookies)} 条 cookie, 其中小红书 {len(xs)} 条")

        if not xs:
            print("未取到小红书 cookie —— 请确认 Chrome 登录的是默认 profile")
            sys.exit(2)

        header = "; ".join(f"{c['name']}={c['value']}" for c in xs)
        OUT.write_text(header, encoding="utf-8")
        names = sorted({c["name"] for c in xs})
        print(f"[3] 写入 {OUT}  ({len(header)} chars)")
        print(f"    关键项: a1={'有' if 'a1' in names else '缺'} "
              f"webId={'有' if 'webId' in names else '缺'} "
              f"web_session={'有' if 'web_session' in names else '缺'}")
        print(f"    全部 cookie 名: {', '.join(names[:25])}{' ...' if len(names) > 25 else ''}")
    finally:
        proc.terminate()
        time.sleep(1)


if __name__ == "__main__":
    main()
