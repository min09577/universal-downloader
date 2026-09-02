# -*- coding: utf-8 -*-
"""Dry-run bilibili BV probe: list formats with acodec/vcodec, check audio-only presence."""
import json
import sys
sys.path.insert(0, r"C:\Users\Min\universal-downloader\standalone-android\app\src\main\python")
from yt_dlp import YoutubeDL
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor, FFmpegMergerPP

URL = "https://www.bilibili.com/video/BV1GJ411x7h7"

opts = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "http_headers": {
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
    },
}

with YoutubeDL(opts) as ydl:
    info = ydl.extract_info(URL, download=False)

formats = info.get("formats") or []
rows = []
for f in formats:
    rows.append({
        "id": f.get("format_id"),
        "ext": f.get("ext"),
        "vcodec": f.get("vcodec"),
        "acodec": f.get("acodec"),
        "h": f.get("height"),
        "tbr": f.get("tbr"),
        "note": f.get("format_note"),
        "proto": f.get("protocol"),
    })
print("=== formats (%d) ===" % len(formats))
print(json.dumps(rows, ensure_ascii=False, indent=1))

audio_only = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
print("\naudio_only count:", len(audio_only))
for f in audio_only:
    print("  AUDIO-ONLY:", f.get("format_id"), f.get("ext"), f.get("acodec"), f.get("tbr"))

# also check requested format under bv*+ba/b and b
for spec in ("bestvideo*+bestaudio/best", "best/bestvideo+bestaudio", "ba"):
    try:
        sel = [f for f in formats if ydl.build_format_selector(spec)]
    except Exception:
        pass
print("\n=== ffmpeg availability on PC (control) ===")
print("versions:", FFmpegPostProcessor.get_versions())

# simulate no-ffmpeg: ffmpeg_location pointing to nonexistent dir
opts2 = dict(opts)
opts2["ffmpeg_location"] = r"C:\definitely-not-exist-xyz"
with YoutubeDL(opts2) as ydl2:
    m = FFmpegMergerPP(ydl2)
    print("merger.available with bad ffmpeg_location:", m.available)
    print("default format spec would be:", ydl2._default_format_spec(info))
