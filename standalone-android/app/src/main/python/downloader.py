"""
万能下载器 - Android 端 Python 下载引擎
通过 Chaquopy 在 Android 上直接运行 yt-dlp
"""

import sys
import json
import os
import traceback
from pathlib import Path

# ========== 下载引擎 ==========

def get_download_dir():
    """获取 Android 下载目录"""
    try:
        from android.os import Environment
        downloads = Environment.getExternalStoragePublicDirectory(
            Environment.DIRECTORY_DOWNLOADS
        ).getAbsolutePath()
        dl_dir = os.path.join(downloads, "UniversalDownloader")
        os.makedirs(dl_dir, exist_ok=True)
        return dl_dir
    except:
        dl_dir = "/sdcard/Download/UniversalDownloader"
        os.makedirs(dl_dir, exist_ok=True)
        return dl_dir


def analyze_url(url):
    """
    分析 URL，返回视频/图片信息
    返回 JSON 字符串
    """
    try:
        from yt_dlp import YoutubeDL

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        result = {
            "success": True,
            "title": info.get("title", "")[:200],
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", ""),
            "thumbnail": info.get("thumbnail", ""),
            "formats_count": len(info.get("formats", [])),
            "ext": info.get("ext", "mp4"),
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        # 如果 yt-dlp 解析失败，尝试作为图片下载
        return json.dumps({
            "success": False,
            "error": str(e),
            "is_image": is_image_url(url),
        }, ensure_ascii=False)


def download_video(url, progress_callback=None):
    """
    下载视频到 Android 设备
    progress_callback 是 Chaquopy 传入的 Java 回调函数
    """
    try:
        from yt_dlp import YoutubeDL

        download_dir = get_download_dir()
        output_template = os.path.join(download_dir, "%(title).80s_%(id)s.%(ext)s")

        class AndroidProgressHook:
            def __init__(self, callback):
                self.callback = callback

            def __call__(self, d):
                if d["status"] == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes", 0)
                    speed = d.get("speed", 0)
                    if total > 0 and self.callback:
                        percent = int(downloaded * 100 / total)
                        speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else ""
                        try:
                            self.callback(percent, speed_str)
                        except:
                            pass
                elif d["status"] == "finished":
                    if self.callback:
                        try:
                            self.callback(100, "处理文件中...")
                        except:
                            pass

        ydl_opts = {
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [AndroidProgressHook(progress_callback)] if progress_callback else [],
            "merge_output_format": "mp4",
            "format": "best[height<=1080][ext=mp4]/best[height<=1080]/best[ext=mp4]/best",
            "max_filesize": 500 * 1024 * 1024,  # 500MB 上限
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # 查找下载的文件
        downloaded_files = sorted(
            Path(download_dir).glob("*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if downloaded_files:
            latest = downloaded_files[0]
            file_size = latest.stat().st_size
            return json.dumps({
                "success": True,
                "filename": latest.name,
                "path": str(latest),
                "size_mb": round(file_size / (1024 * 1024), 2),
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": False,
                "error": "下载完成但未找到文件",
            }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


def download_image(url):
    """下载单张图片"""
    try:
        import requests as req

        download_dir = get_download_dir()
        # 生成文件名
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36"
        }
        resp = req.get(url, headers=headers, timeout=30, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "jpeg" in content_type or "jpg" in content_type:
            ext = "jpg"
        elif "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"
        elif "gif" in content_type:
            ext = "gif"
        else:
            ext = "jpg"

        filename = f"{url_hash}.{ext}"
        filepath = os.path.join(download_dir, filename)

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        file_size = os.path.getsize(filepath)
        if file_size < 1024:
            os.remove(filepath)
            return json.dumps({"success": False, "error": "文件太小，可能是无效图片"})

        return json.dumps({
            "success": True,
            "filename": filename,
            "path": filepath,
            "size_mb": round(file_size / (1024 * 1024), 2),
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


def extract_images_from_page(url):
    """从网页中提取所有图片链接"""
    try:
        import requests as req
        import re

        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36"
        }
        resp = req.get(url, headers=headers, timeout=15)
        html = resp.text

        # 提取图片
        patterns = [
            r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))["\']',
            r'<meta\s+property="og:image"\s+content=["\']([^"\']+)["\']',
            r'<meta\s+name="twitter:image"\s+content=["\']([^"\']+)["\']',
        ]

        images = []
        seen = set()
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for img_url in matches:
                if img_url not in seen:
                    seen.add(img_url)
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    elif img_url.startswith("/"):
                        from urllib.parse import urlparse as up
                        p = up(url)
                        img_url = f"{p.scheme}://{p.netloc}{img_url}"
                    elif not img_url.startswith("http"):
                        continue

                    # 过滤小图
                    skip_keywords = ["icon", "logo", "avatar", "favicon", "emoji", "pixel", "1x1"]
                    if not any(k in img_url.lower() for k in skip_keywords):
                        images.append(img_url)

        return json.dumps({
            "success": True,
            "images": images[:20],
            "total": len(images),
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


def is_image_url(url):
    """判断是否为图片直链"""
    image_exts = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"]
    url_lower = url.lower()
    return any(url_lower.endswith(ext) or f"{ext}?" in url_lower for ext in image_exts)


def detect_platform(url):
    """检测 URL 所属平台"""
    url_lower = url.lower()
    platforms = {
        "bilibili": ["bilibili.com", "b23.tv"],
        "youtube": ["youtube.com", "youtu.be"],
        "douyin": ["douyin.com", "tiktok.com"],
        "kuaishou": ["kuaishou.com"],
        "xiaohongshu": ["xiaohongshu.com", "xhslink.com"],
        "weibo": ["weibo.com"],
        "twitter": ["twitter.com", "x.com"],
        "instagram": ["instagram.com"],
        "facebook": ["facebook.com", "fb.com"],
        "reddit": ["reddit.com", "redd.it"],
        "zhihu": ["zhihu.com"],
        "vimeo": ["vimeo.com"],
        "twitch": ["twitch.tv"],
    }
    for platform, domains in platforms.items():
        for domain in domains:
            if domain in url_lower:
                return platform
    return "unknown"


# ========== CLI 入口（Chaquopy 调用） ==========

if __name__ == "__main__":
    """
    命令行用法（由 Kotlin 通过 Chaquopy 调用）:
    
    python downloader.py analyze <url>
    python downloader.py download_video <url>
    python downloader.py download_image <url>
    python downloader.py extract_images <url>
    python downloader.py detect <url>
    """
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: downloader.py <action> <url>"}))
        sys.exit(1)

    action = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else ""

    if action == "analyze":
        print(analyze_url(url))
    elif action == "download_video":
        print(download_video(url))
    elif action == "download_image":
        print(download_image(url))
    elif action == "extract_images":
        print(extract_images_from_page(url))
    elif action == "detect":
        print(json.dumps({
            "platform": detect_platform(url),
            "is_image": is_image_url(url),
        }, ensure_ascii=False))
    else:
        print(json.dumps({"error": f"Unknown action: {action}"}))
