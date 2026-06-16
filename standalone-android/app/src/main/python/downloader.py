"""
万能下载器 - Android 端 Python 下载引擎
通过 Chaquopy 在 Android 上直接运行 yt-dlp
"""

import sys
import json
import os
import traceback
from pathlib import Path

# ========== yt-dlp 环境修复 ==========

def _fix_ssl():
    """修复 Android 上的 SSL 证书问题"""
    try:
        import certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    except:
        pass

_fix_ssl()


# ========== 工具函数 ==========

def get_download_dir():
    """获取 Android 下载目录"""
    try:
        downloads_dir = "/sdcard/Download"
        dl_dir = os.path.join(downloads_dir, "UniversalDownloader")
        os.makedirs(dl_dir, exist_ok=True)
        return dl_dir
    except:
        return "/sdcard/Download/UniversalDownloader"


def is_image_url(url):
    """判断是否为图片直链"""
    image_exts = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".avif"]
    url_lower = url.lower()
    return any(url_lower.endswith(ext) or (ext + "?") in url_lower for ext in image_exts)


def _safe_json(obj):
    """安全序列化 JSON，处理各种异常"""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except:
        return json.dumps({"success": False, "error": "JSON 序列化失败"})


# ========== 核心功能 ==========

def analyze_url(url):
    """
    分析 URL，返回视频/图片信息
    """
    try:
        # 先导入 yt-dlp
        from yt_dlp import YoutubeDL

        # Android 环境特化配置
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "nocheckcertificate": False,
            "ignoreerrors": False,
            # Android 上的 User-Agent
            "user_agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        }

        with YoutubeDL(ydl_opts) as ydl:
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
        return _safe_json({
            "success": False,
            "error": f"yt-dlp 未正确安装: {e}",
            "is_image": is_image_url(url),
        })
    except Exception as e:
        err_msg = str(e)
        # 常见错误提示
        if "SSL" in err_msg or "certificate" in err_msg.lower():
            err_msg = f"SSL证书错误（可尝试直链图片）: {err_msg[:100]}"
        elif "Unsupported URL" in err_msg:
            err_msg = f"不支持的链接格式: {err_msg[:100]}"
        elif "HTTP Error" in err_msg:
            err_msg = f"网络请求失败: {err_msg[:100]}"
        
        return _safe_json({
            "success": False,
            "error": err_msg,
            "is_image": is_image_url(url),
        })


def download_video(url, progress_callback=None):
    """下载视频到 Android 设备"""
    try:
        from yt_dlp import YoutubeDL
        import certifi

        download_dir = get_download_dir()
        output_template = os.path.join(download_dir, "%(title).80s_%(id)s.%(ext)s")

        class AndroidProgressHook:
            def __init__(self, callback):
                self.callback = callback
            def __call__(self, d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                    downloaded = d.get("downloaded_bytes", 0)
                    speed = d.get("speed", 0)
                    if total > 0 and self.callback:
                        pct = int(downloaded * 100 / total)
                        spd = f"{speed/1024/1024:.1f} MB/s" if speed else ""
                        try: self.callback(pct, spd)
                        except: pass
                elif d.get("status") == "finished" and self.callback:
                    try: self.callback(100, "处理中...")
                    except: pass

        ydl_opts = {
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [AndroidProgressHook(progress_callback)] if progress_callback else [],
            "merge_output_format": "mp4",
            "format": "best[height<=1080]/best",
            "max_filesize": 500 * 1024 * 1024,
            "user_agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        downloaded_files = sorted(
            Path(download_dir).glob("*"),
            key=lambda p: p.stat().st_mtime, reverse=True
        )

        if downloaded_files:
            latest = downloaded_files[0]
            size = latest.stat().st_size
            return _safe_json({
                "success": True,
                "filename": latest.name,
                "path": str(latest),
                "size_mb": round(size / (1024 * 1024), 2),
            })
        return _safe_json({"success": False, "error": "下载完成但未找到文件"})

    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:200]})


def download_image(url):
    """下载单张图片"""
    try:
        import requests as req
        import hashlib

        download_dir = get_download_dir()
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36"}
        resp = req.get(url, headers=headers, timeout=30, stream=True)
        resp.raise_for_status()

        ct = resp.headers.get("content-type", "").lower()
        ext_map = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp", "gif": "gif", "avif": "avif"}
        ext = "jpg"
        for k, v in ext_map.items():
            if k in ct:
                ext = v
                break

        filename = f"{url_hash}.{ext}"
        filepath = os.path.join(download_dir, filename)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        size = os.path.getsize(filepath)
        if size < 1024:
            os.remove(filepath)
            return _safe_json({"success": False, "error": "文件太小，可能是无效图片"})

        return _safe_json({
            "success": True, "filename": filename,
            "path": filepath, "size_mb": round(size / (1024*1024), 2),
        })

    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:200]})


def extract_images_from_page(url):
    """从网页中提取所有图片链接"""
    try:
        import requests as req
        import re

        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36"}
        resp = req.get(url, headers=headers, timeout=15)
        html = resp.text

        patterns = [
            r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif|avif))["\']',
            r'<meta\s+property="og:image"\s+content=["\']([^"\']+)["\']',
        ]

        images, seen = [], set()
        for pattern in patterns:
            for img in re.findall(pattern, html, re.IGNORECASE):
                if img not in seen:
                    seen.add(img)
                    if img.startswith("//"): img = "https:" + img
                    elif img.startswith("/"):
                        from urllib.parse import urlparse
                        p = urlparse(url)
                        img = f"{p.scheme}://{p.netloc}{img}"
                    elif not img.startswith("http"): continue
                    skip = ["icon", "logo", "avatar", "favicon", "emoji", "pixel", "1x1"]
                    if not any(k in img.lower() for k in skip):
                        images.append(img)

        return _safe_json({"success": True, "images": images[:20], "total": len(images)})

    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:200]})


def detect_platform(url):
    """检测 URL 所属平台 - 返回 JSON 对象"""
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
                return _safe_json({
                    "platform": platform,
                    "is_image": is_image_url(url),
                })
    return _safe_json({
        "platform": "unknown",
        "is_image": is_image_url(url),
    })
