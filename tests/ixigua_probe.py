# -*- coding: utf-8 -*-
"""
PC 测试台：西瓜专管线端点探测（先行验证 _ixigua_* 全链路，再上真机）。
用法:
  python tests/ixigua_probe.py <ixigua_url> [--cookies-file tests/cookies_xhs.txt]
不传 cookies 则无登录态探测（验证风控面）。
"""
import base64
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "standalone-android" / "app" / "src" / "main" / "python"))
import downloader  # noqa: E402


def probe(url: str, cookies_file: str | None):
    print(f"=== 1. shortlink resolve: {url[:70]}")
    url2 = downloader._ixigua_shortlink_resolve(url)
    print(f"    -> {url2[:90]}")

    print("=== 2. extract item id")
    item_id = downloader._ixigua_extract_item_id(url2)
    print(f"    -> item_id={item_id}")
    if not item_id:
        print("FAIL: no item id")
        return

    print("=== 3. fetch video info (SSR)")
    # 测试台手动注入 cookie（App 内由 _ixigua_cookies_header() 从 WebView 拿）
    if cookies_file:
        pairs = []
        for line in Path(cookies_file).read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 7:
                    pairs.append(f"{parts[5]}={parts[6]}")
        orig = downloader._ixigua_cookies_header
        downloader._ixigua_cookies_header = lambda: "; ".join(pairs)
        print(f"    cookies injected: {len(pairs)} pairs")
    info = downloader._ixigua_fetch_video_info(url2)
    if cookies_file:
        downloader._ixigua_cookies_header = orig
    if not info:
        print("FAIL: no SSR video info (cookie wall / risk page / field drift)")
        return

    streams = info["streams"]
    print(f"    title={info['title'][:50]!r}")
    print(f"    duration={info['duration_s']}s  streams={len(streams)}")
    for s in streams:
        print(f"      [{s['kind']}] h={s['height']} fps={s['fps']} codec={s['codec']!r} "
              f"q={s['quality_type']} size={s['size']} br={s['bitrate']} url={s['url'][:60]}...")

    print("=== 4. pick streams")
    v, a = downloader._ixigua_pick_streams(streams)
    print(f"    video: h={v['height'] if v else None} q={v['quality_type'] if v else None}")
    print(f"    audio: br={a['bitrate'] if a else None}")

    print("=== 5. HEAD 直链探测（不下载）")
    import requests
    for label, s in (("video", v), ("audio", a)):
        if not s:
            continue
        try:
            r = requests.head(s["url"], headers={
                "User-Agent": downloader._IXIGUA_UA,
                "Referer": "https://www.ixigua.com/",
            }, timeout=15, allow_redirects=True)
            cl = r.headers.get("content-length", "?")
            ct = r.headers.get("content-type", "?")
            print(f"    {label}: HTTP {r.status_code} len={cl} type={ct}")
        except Exception as e:
            print(f"    {label}: ERR {type(e).__name__}: {str(e)[:100]}")

    print("=== DONE (管线各环节可用性如上; 实际下载交真机回归) ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cf = None
    if "--cookies-file" in sys.argv:
        cf = sys.argv[sys.argv.index("--cookies-file") + 1]
    probe(sys.argv[1], cf)
