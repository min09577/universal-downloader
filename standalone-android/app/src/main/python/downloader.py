"""
万能下载器 - Android 端 Python 下载引擎
通过 Chaquopy 在 Android 上直接运行 yt-dlp
"""

import sys
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ========== SSL 修复 ==========

def _fix_ssl():
    try:
        import certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    except:
        pass
_fix_ssl()

# ========== Cookies ==========

def _get_android_cookies(domain):
    """从 Android WebView CookieManager 获取 cookies"""
    try:
        from android.webkit import CookieManager
        cm = CookieManager.getInstance()
        cookie_str = cm.getCookie(f"https://{domain}")
        return cookie_str if cookie_str else ""
    except:
        return ""


def _cookie_jar_for_domain(domain):
    """创建包含 Android cookies 的 MozillaCookieJar"""
    try:
        import http.cookiejar
        cookie_str = _get_android_cookies(domain)
        if not cookie_str:
            return None
        cj = http.cookiejar.MozillaCookieJar()
        # 写入临时文件
        fd, path = tempfile.mkstemp(suffix='.txt', prefix='cookies_')
        with os.fdopen(fd, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    f.write(f"{domain}\tFALSE\t/\tFALSE\t0\t{name.strip()}\t{value.strip()}\n")
        return path
    except:
        return None


# ========== URL 处理 ==========

def normalize_url(url):
    """预处理各平台特殊 URL"""
    parsed = urlparse(url)
    path = parsed.path
    netloc = parsed.netloc
    qs = parse_qs(parsed.query)

    # 小红书 shortlink → 完整 URL (保留 xsec_token)
    if "xhslink.com" in netloc or ("xiaohongshu.com" in netloc and "/discovery/item/" in path):
        m = re.search(r'/discovery/item/([a-f0-9]+)', path)
        if m:
            note_id = m.group(1)
            xsec = qs.get('xsec_token', [None])[0] or ''
            if xsec:
                return f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec}"
            return f"https://www.xiaohongshu.com/explore/{note_id}"

    # B站: 清理参数，只保留 BV/av 号
    if "bilibili.com" in netloc:
        bv = re.search(r'BV[a-zA-Z0-9]+', url)
        if bv:
            return f"https://www.bilibili.com/video/{bv.group(0)}"
        av = re.search(r'av(\d+)', url, re.IGNORECASE)
        if av:
            return f"https://www.bilibili.com/video/av{av.group(1)}"

    return url


def get_download_dir():
    """获取临时下载目录"""
    dl_dir = os.path.join(tempfile.gettempdir(), "ud_downloads")
    os.makedirs(dl_dir, exist_ok=True)
    return dl_dir


def is_image_url(url):
    """判断是否为图片直链"""
    image_exts = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".avif"]
    url_lower = url.lower()
    return any(url_lower.endswith(ext) or (ext + "?") in url_lower for ext in image_exts)


def _safe_json(obj):
    try:
        return json.dumps(obj, ensure_ascii=False)
    except:
        return json.dumps({"success": False, "error": "JSON 序列化失败"})


def _get_domain(url):
    """从 URL 提取域名"""
    return urlparse(url).netloc


def _ytdlp_base_opts():
    """yt-dlp 基础配置，包含 cookies"""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "nocheckcertificate": False,
        "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    }
    return opts


# ========== 核心功能 ==========

def analyze_url(url):
    url = normalize_url(url)
    try:
        from yt_dlp import YoutubeDL

        opts = _ytdlp_base_opts()
        opts["extract_flat"] = False

        # 尝试传入 cookies
        domain = _get_domain(url)
        cookie_file = _cookie_jar_for_domain(domain)
        if cookie_file:
            opts["cookiefile"] = cookie_file

        # B站特殊处理
        if "bilibili.com" in domain:
            opts["http_headers"] = {
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
            }

        # 小红书特殊处理
        if "xiaohongshu.com" in domain:
            opts["http_headers"] = {
                "Referer": "https://www.xiaohongshu.com/",
                "Origin": "https://www.xiaohongshu.com",
            }

        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return _safe_json({
            "success": True,
            "title": str(info.get("title", ""))[:200],
            "duration": info.get("duration", 0),
            "uploader": str(info.get("uploader", "")),
            "thumbnail": str(info.get("thumbnail", "")),
            "formats_count": len(info.get("formats", [])),
            "ext": str(info.get("ext", "mp4")),
        })

    except ImportError as e:
        return _safe_json({"success": False, "error": f"yt-dlp 未安装: {e}", "is_image": is_image_url(url)})
    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:300], "is_image": is_image_url(url)})


def download_video(url, progress_callback=None):
    url = normalize_url(url)
    try:
        from yt_dlp import YoutubeDL

        dl_dir = get_download_dir()
        output_template = os.path.join(dl_dir, "UD_%(title).80s.%(ext)s")

        class AndroidProgressHook:
            def __init__(self, cb):
                self.cb = cb
            def __call__(self, d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                    downloaded = d.get("downloaded_bytes", 0)
                    speed = d.get("speed", 0)
                    if total > 0 and self.cb:
                        pct = int(downloaded * 100 / total)
                        spd = f"{speed/1024/1024:.1f} MB/s" if speed else ""
                        try: self.cb(pct, spd)
                        except: pass
                elif d.get("status") == "finished" and self.cb:
                    try: self.cb(100, "处理中...")
                    except: pass

        opts = _ytdlp_base_opts()
        opts.update({
            "outtmpl": output_template,
            "progress_hooks": [AndroidProgressHook(progress_callback)] if progress_callback else [],
            "merge_output_format": "mp4",
            "format": "best[height<=1080]/best",
            "max_filesize": 500 * 1024 * 1024,
        })

        domain = _get_domain(url)
        cookie_file = _cookie_jar_for_domain(domain)
        if cookie_file:
            opts["cookiefile"] = cookie_file

        if "bilibili.com" in domain:
            opts["http_headers"] = {"Referer": "https://www.bilibili.com/", "Origin": "https://www.bilibili.com"}
        if "xiaohongshu.com" in domain:
            opts["http_headers"] = {"Referer": "https://www.xiaohongshu.com/", "Origin": "https://www.xiaohongshu.com"}

        with YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)

        downloaded = sorted(
            [f for f in Path(dl_dir).iterdir() if f.is_file()],
            key=lambda p: p.stat().st_mtime, reverse=True
        )

        if downloaded:
            latest = downloaded[0]
            size = latest.stat().st_size
            return _safe_json({
                "success": True,
                "filename": latest.name,
                "path": str(latest),
                "size_mb": round(size / (1024 * 1024), 2),
            })
        return _safe_json({"success": False, "error": "下载完成但未找到文件"})

    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:300]})


def download_image(url):
    try:
        import requests as req, hashlib

        dl_dir = get_download_dir()
        url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36"}
        resp = req.get(url, headers=headers, timeout=30, stream=True)
        resp.raise_for_status()

        ct = resp.headers.get("content-type", "").lower()
        ext = "jpg"
        for k in ["jpeg", "jpg", "png", "webp", "gif"]:
            if k in ct: ext = k; break

        filename = f"UD_{url_hash}.{ext}"
        filepath = os.path.join(dl_dir, filename)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        size = os.path.getsize(filepath)
        if size < 1024:
            os.remove(filepath)
            return _safe_json({"success": False, "error": "文件太小"})

        return _safe_json({
            "success": True, "filename": filename, "path": filepath,
            "size_mb": round(size / (1024*1024), 2),
        })
    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:200]})


def extract_images_from_page(url):
    try:
        import requests as req
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36"}
        resp = req.get(url, headers=headers, timeout=15)
        html = resp.text

        patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'<meta\s+property="og:image"\s+content=["\']([^"\']+)["\']',
        ]
        images, seen = [], set()
        for pattern in patterns:
            for img in re.findall(pattern, html, re.IGNORECASE):
                if img in seen: continue
                seen.add(img)
                if img.startswith("//"): img = "https:" + img
                elif img.startswith("/"):
                    p = urlparse(url)
                    img = f"{p.scheme}://{p.netloc}{img}"
                elif not img.startswith("http"): continue
                skip = ["icon", "logo", "avatar", "favicon", "emoji", "pixel"]
                if not any(k in img.lower() for k in skip):
                    images.append(img)
        return _safe_json({"success": True, "images": images[:20], "total": len(images)})
    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:200]})


def detect_platform(url):
    url_lower = url.lower()
    platforms = {
        "bilibili": ["bilibili.com", "b23.tv"],
        "youtube": ["youtube.com", "youtu.be"],
        "douyin": ["douyin.com", "tiktok.com"],
        "kuaishou": ["kuaishou.com"],
        "xiaohongshu": ["xiaohongshu.com", "xhslink.com"],
        "weibo": ["weibo.com", "weibo.cn"],
        "twitter": ["twitter.com", "x.com"],
        "instagram": ["instagram.com"],
        "facebook": ["facebook.com", "fb.com", "fb.watch"],
        "reddit": ["reddit.com", "redd.it"],
        "zhihu": ["zhihu.com"],
        "vimeo": ["vimeo.com"],
        "twitch": ["twitch.tv"],
        "pinterest": ["pinterest.com", "pin.it"],
    }
    for platform, domains in platforms.items():
        for domain in domains:
            if domain in url_lower:
                return _safe_json({"platform": platform, "is_image": is_image_url(url)})
    return _safe_json({"platform": "unknown", "is_image": is_image_url(url)})
