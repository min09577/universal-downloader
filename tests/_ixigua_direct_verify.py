# -*- coding: utf-8 -*-
"""快速验证：分享短链 → 302 → iesdouyin 页面 → video_id → play API 直链（用户实测路径）"""
import re
import requests

UA_PAGE = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
UA_PLAY = "com.ss.android.ugc.aweme/110101"

s = requests.Session()
# ① 短链 302
r0 = s.get("https://v.douyin.com/p9iIYoK3k18/", headers={"User-Agent": UA_PAGE}, allow_redirects=False, timeout=15)
print("short:", r0.status_code, "->", r0.headers.get("Location", "")[:100])
# 逐跳跟随
cur = "https://v.douyin.com/p9iIYoK3k18/"
for i in range(5):
    r0 = s.get(cur, headers={"User-Agent": UA_PAGE}, allow_redirects=False, timeout=15)
    loc = r0.headers.get("Location")
    print(f"hop{i}: {r0.status_code} -> {cur[:80]}")
    if not loc:
        break
    cur = loc if loc.startswith("http") else f"https://{__import__('urllib.parse', fromlist=['urlparse']).urlparse(cur).netloc}{loc}"
final = cur
print("final:", final[:120])
m = re.search(r"(\d{15,})", final)
item_id = m.group(1) if m else None
print("item_id:", item_id)

# ② 页面提取 video_id
r1 = s.get(final, headers={"User-Agent": UA_PAGE, "Referer": "https://www.douyin.com/"}, timeout=15)
t = r1.text
print("page len:", len(t))
vids = re.findall(r'"video_id"\s*:\s*"(v0[0-9a-f]{20,})"', t) or re.findall(r'(v0[0-9a-f]{20,})', t)
print("video_ids:", list(dict.fromkeys(vids))[:3])
vid = vids[0] if vids else None

# ③ play API 直链
if vid:
    api = f"https://www.iesdouyin.com/aweme/v1/play/?video_id={vid}&ratio=1080p&line=0"
    r2 = s.get(api, headers={"User-Agent": UA_PLAY}, allow_redirects=False, timeout=15)
    print("play api:", r2.status_code, "->", r2.headers.get("Location", "")[:100])
    r3 = s.get(r2.headers["Location"] if r2.headers.get("Location") else api,
               headers={"User-Agent": UA_PLAY}, stream=True, timeout=20)
    print("direct:", r3.status_code, "ct:", r3.headers.get("content-type"), "len:", r3.headers.get("content-length"))
    total = 0
    with open(r"C:\Users\Min\universal-downloader\tests\_ixigua_direct_test.mp4", "wb") as f:
        for chunk in r3.iter_content(1 << 16):
            f.write(chunk)
            total += len(chunk)
            if total > 3 * 1024 * 1024:
                break
    print("downloaded:", total, "bytes")
