#!/usr/bin/env python3
"""
万能下载器 - 全网图片/视频智能下载
支持粘贴任意 URL 自动识别并下载图片或视频
"""

import os
import sys
import io
import re
import json
import hashlib
import threading
import time
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# ----- 配置 -----
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)
HISTORY_FILE = BASE_DIR / "history.json"

# 下载任务状态
download_tasks = {}
task_lock = threading.Lock()


# ========== 工具函数 ==========

def load_history():
    """加载下载历史"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []


def save_history(history):
    """保存下载历史"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_to_history(entry):
    """添加一条下载记录"""
    history = load_history()
    history.insert(0, entry)
    # 最多保留 200 条
    if len(history) > 200:
        history = history[:200]
    save_history(history)


def get_file_hash(url):
    """生成 URL 的文件名哈希"""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def detect_content_type(url):
    """
    智能识别 URL 类型
    返回: {"type": "video"|"image"|"page", "platform": str, "title": str}
    """
    url_lower = url.lower()

    # 视频平台识别
    video_platforms = {
        "bilibili": ["bilibili.com", "b23.tv"],
        "youtube": ["youtube.com", "youtu.be"],
        "douyin": ["douyin.com", "iesdouyin.com", "tiktok.com"],
        "kuaishou": ["kuaishou.com", "gifshow.com"],
        "weibo": ["weibo.com", "weibocdn.com"],
        "xiaohongshu": ["xiaohongshu.com", "xhslink.com"],
        "zhihu": ["zhihu.com"],
        "douban": ["douban.com"],
        "vimeo": ["vimeo.com"],
        "twitter": ["twitter.com", "x.com"],
        "instagram": ["instagram.com"],
        "facebook": ["facebook.com", "fb.com"],
        "pornhub": ["pornhub.com"],
        "xvideos": ["xvideos.com"],
        "reddit": ["reddit.com", "redd.it"],
        "tumblr": ["tumblr.com"],
        "pinterest": ["pinterest.com", "pin.it"],
        "twitch": ["twitch.tv"],
        "dailymotion": ["dailymotion.com"],
        "youku": ["youku.com"],
        "iqiyi": ["iqiyi.com"],
        "qq": ["v.qq.com"],
        "mgtv": ["mgtv.com"],
        "huya": ["huya.com"],
        "douyu": ["douyu.com"],
    }

    # 图片平台识别
    image_domains = [
        "imgur.com", "i.imgur.com", "pixiv.net", "i.pximg.net",
        "deviantart.com", "artstation.com", "flickr.com",
        "500px.com", "unsplash.com", "pexels.com",
    ]

    # 直接图片链接
    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico", ".heic", ".avif"]
    # 直接视频链接
    video_extensions = [".mp4", ".webm", ".mkv", ".flv", ".avi", ".mov", ".wmv", ".m3u8", ".ts", ".m4v"]

    parsed = urlparse(url)
    path_lower = parsed.path.lower()

    # 检查是否是直接媒体文件
    for ext in image_extensions:
        if path_lower.endswith(ext) or ext in url_lower:
            return {"type": "image", "platform": "direct", "title": os.path.basename(parsed.path)}

    for ext in video_extensions:
        if path_lower.endswith(ext) or ext in url_lower:
            return {"type": "video", "platform": "direct", "title": os.path.basename(parsed.path)}

    # 检查视频平台
    for platform, domains in video_platforms.items():
        for domain in domains:
            if domain in url_lower:
                return {"type": "video", "platform": platform, "title": f"{platform}_video"}

    # 检查图片平台
    for domain in image_domains:
        if domain in url_lower:
            return {"type": "image", "platform": "image_site", "title": "image"}

    # 默认尝试作为页面处理（用 yt-dlp 提取）
    return {"type": "page", "platform": "unknown", "title": parsed.netloc}


def extract_images_from_page(url):
    """
    从页面中提取所有图片链接
    返回: [{"url": str, "filename": str}, ...]
    """
    images = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        resp.raise_for_status()

        # 用正则提取所有图片
        img_patterns = [
            r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp|bmp|svg))["\']',
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'background-image:\s*url\(["\']?([^"\')\s]+)["\']?\)',
            r'<meta\s+property="og:image"\s+content=["\']([^"\']+)["\']',
            r'<meta\s+name="twitter:image"\s+content=["\']([^"\']+)["\']',
            r'<link\s+rel="image_src"\s+href=["\']([^"\']+)["\']',
        ]

        seen = set()
        for pattern in img_patterns:
            matches = re.findall(pattern, resp.text, re.IGNORECASE)
            for img_url in matches:
                # 处理相对路径
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
                elif not img_url.startswith("http"):
                    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    base_dir = base.rsplit("/", 1)[0]
                    img_url = f"{base_dir}/{img_url}"

                if img_url not in seen:
                    seen.add(img_url)
                    ext_match = re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|svg)(?:\?.*)?$', img_url, re.IGNORECASE)
                    ext = ext_match.group(1) if ext_match else "jpg"
                    filename = f"{get_file_hash(img_url)}.{ext}"
                    images.append({"url": img_url, "filename": filename})

        # 按图片大小排序（优先大图）
        # 过滤掉太小的图片（icon、logo等）
        filtered = [img for img in images if not any(
            x in img["url"].lower() for x in ["icon", "logo", "avatar", "favicon", "emoji", "pixel", "1x1", "blank"]
        )]
        if filtered:
            images = filtered

        return images[:50]  # 最多 50 张

    except Exception as e:
        print(f"提取图片失败: {e}")
        return []


def download_file(url, filepath):
    """下载单个文件到指定路径"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": url,
    }
    resp = requests.get(url, headers=headers, timeout=60, stream=True)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return True


# ========== yt-dlp 下载引擎 ==========

def ytdlp_download(url, task_id, options=None):
    """使用 yt-dlp 下载视频/音频"""
    task = download_tasks.get(task_id)
    if not task:
        return

    try:
        # 先获取信息
        from yt_dlp import YoutubeDL

        task["status"] = "fetching_info"
        task["message"] = "正在解析链接..."

        info_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        with YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        task["info"] = {
            "title": info.get("title", "未知"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "未知"),
            "thumbnail": info.get("thumbnail", ""),
            "formats_count": len(info.get("formats", [])),
        }

        task["status"] = "downloading"
        task["message"] = "正在下载..."

        # 下载配置
        output_template = str(DOWNLOAD_DIR / "%(title).100s_%(id)s.%(ext)s")

        download_opts = {
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [lambda d: progress_hook(d, task_id)],
            "merge_output_format": "mp4",
            "prefer_ffmpeg": True,
            # 优先下载最佳质量
            "format": "best[ext=mp4]/best",
            # 限制文件大小（默认最大 500MB）
            "max_filesize": options.get("max_filesize", 500 * 1024 * 1024) if options else 500 * 1024 * 1024,
        }

        # 如果用户选择仅音频
        if options and options.get("audio_only"):
            download_opts["format"] = "bestaudio/best"
            download_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }]

        with YoutubeDL(download_opts) as ydl:
            ydl.download([url])

        # 查找下载的文件
        downloaded_files = sorted(
            DOWNLOAD_DIR.glob("*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if downloaded_files:
            latest = downloaded_files[0]
            file_size = latest.stat().st_size

            task["status"] = "completed"
            task["result"] = {
                "filename": latest.name,
                "path": str(latest),
                "size": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
            }

            # 添加历史记录
            add_to_history({
                "url": url,
                "title": info.get("title", "未知"),
                "filename": latest.name,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "platform": task.get("platform", "unknown"),
                "type": "video",
                "time": datetime.now().isoformat(),
            })
        else:
            task["status"] = "error"
            task["message"] = "下载完成但未找到文件"

    except Exception as e:
        task["status"] = "error"
        task["message"] = f"下载失败: {str(e)}"
        print(f"yt-dlp 下载错误: {e}")


def progress_hook(d, task_id):
    """yt-dlp 下载进度回调"""
    task = download_tasks.get(task_id)
    if not task:
        return
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        downloaded = d.get("downloaded_bytes", 0)
        speed = d.get("speed", 0)
        if total > 0:
            task["progress"] = round(downloaded / total * 100, 1)
        task["downloaded_bytes"] = downloaded
        task["total_bytes"] = total
        task["speed"] = speed
        task["speed_str"] = f"{speed/1024/1024:.1f} MB/s" if speed else ""
    elif d["status"] == "finished":
        task["progress"] = 100
        task["message"] = "正在处理文件..."


# ========== 图片批量下载线程 ==========

def batch_download_images(images, task_id):
    """批量下载图片"""
    task = download_tasks.get(task_id)
    if not task:
        return

    total = len(images)
    downloaded_files = []

    task["status"] = "downloading"
    task["message"] = f"正在下载图片 (0/{total})..."
    task["total_count"] = total
    task["completed_count"] = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    for i, img in enumerate(images):
        try:
            filepath = DOWNLOAD_DIR / img["filename"]
            resp = requests.get(img["url"], headers=headers, timeout=30, stream=True)
            resp.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = filepath.stat().st_size
            if file_size > 1024:  # 过滤太小的文件
                downloaded_files.append({
                    "filename": img["filename"],
                    "path": str(filepath),
                    "size": file_size,
                    "size_kb": round(file_size / 1024, 1),
                    "source_url": img["url"],
                })

            task["completed_count"] = i + 1
            task["progress"] = round((i + 1) / total * 100, 1)
            task["message"] = f"正在下载图片 ({i+1}/{total})..."

        except Exception as e:
            print(f"下载图片失败 {img['url']}: {e}")
            continue

    if downloaded_files:
        task["status"] = "completed"
        task["result"] = {
            "files": downloaded_files,
            "total": len(downloaded_files),
        }
        # 添加历史记录
        add_to_history({
            "url": task["url"],
            "title": task.get("info", {}).get("title", "图片合集"),
            "count": len(downloaded_files),
            "platform": task.get("platform", "unknown"),
            "type": "image",
            "time": datetime.now().isoformat(),
        })
    else:
        task["status"] = "error"
        task["message"] = "未能成功下载任何图片"


# ========== API 路由 ==========

@app.route("/")
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/analyze", methods=["POST"])
def analyze_url():
    """分析 URL，识别类型并获取信息"""
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "请输入 URL"}), 400

    # 自动补全协议
    if not url.startswith("http"):
        url = "https://" + url

    # 智能识别
    detected = detect_content_type(url)

    result = {
        "url": url,
        "detected_type": detected["type"],
        "platform": detected["platform"],
        "title": detected["title"],
    }

    # 如果是页面类型，尝试提取图片
    if detected["type"] in ("image", "page"):
        images = extract_images_from_page(url)
        result["images_found"] = len(images)
        if images:
            result["images"] = images[:12]  # 预览前 12 张
            result["total_images"] = len(images)

    return jsonify(result)


@app.route("/api/download", methods=["POST"])
def start_download():
    """开始下载任务"""
    data = request.get_json()
    url = data.get("url", "").strip()
    options = data.get("options", {})

    if not url:
        return jsonify({"error": "请输入 URL"}), 400

    if not url.startswith("http"):
        url = "https://" + url

    # 创建任务
    task_id = hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:16]
    detected = detect_content_type(url)

    task = {
        "id": task_id,
        "url": url,
        "type": detected["type"],
        "platform": detected["platform"],
        "status": "pending",
        "progress": 0,
        "message": "准备中...",
        "created_at": datetime.now().isoformat(),
    }

    with task_lock:
        download_tasks[task_id] = task

    # 根据类型选择下载方式
    if detected["type"] in ("video", "page"):
        # 使用 yt-dlp
        thread = threading.Thread(
            target=ytdl_download,
            args=(url, task_id, options),
            daemon=True,
        )
        thread.start()
    elif detected["type"] == "image":
        # 提取并批量下载图片
        images = extract_images_from_page(url)
        if not images:
            task["status"] = "error"
            task["message"] = "未找到可下载的图片"
        else:
            task["total_count"] = len(images)
            thread = threading.Thread(
                target=batch_download_images,
                args=(images, task_id),
                daemon=True,
            )
            thread.start()

    return jsonify({"task_id": task_id, "status": "pending"})


@app.route("/api/task/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """获取下载任务状态"""
    with task_lock:
        task = download_tasks.get(task_id)

    if not task:
        return jsonify({"error": "任务不存在"}), 404

    return jsonify(task)


@app.route("/api/history", methods=["GET"])
def get_history():
    """获取下载历史"""
    history = load_history()
    return jsonify(history[:50])


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    """清空下载历史"""
    save_history([])
    # 同时清理下载文件
    for f in DOWNLOAD_DIR.glob("*"):
        try:
            f.unlink()
        except:
            pass
    return jsonify({"message": "已清空"})


@app.route("/api/files", methods=["GET"])
def list_files():
    """列出已下载的文件"""
    files = []
    for f in sorted(DOWNLOAD_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file():
            files.append({
                "filename": f.name,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return jsonify(files[:100])


@app.route("/downloads/<path:filename>")
def serve_download(filename):
    """提供文件下载"""
    return send_from_directory(str(DOWNLOAD_DIR), filename, as_attachment=True)


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """获取统计信息"""
    history = load_history()
    total_downloads = len(history)
    total_size = sum(h.get("size_mb", 0) for h in history)
    videos = sum(1 for h in history if h.get("type") == "video")
    images = sum(1 for h in history if h.get("type") == "image")

    files_on_disk = list(DOWNLOAD_DIR.glob("*"))
    disk_total_mb = round(sum(f.stat().st_size for f in files_on_disk if f.is_file()) / (1024 * 1024), 2)

    return jsonify({
        "total_downloads": total_downloads,
        "total_size_mb": round(total_size, 2),
        "disk_size_mb": disk_total_mb,
        "video_count": videos,
        "image_count": images,
    })


# ========== HTML 模板 ==========

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>万能下载器 - 全网图片视频下载</title>
    <meta name="description" content="粘贴任意链接，自动识别并下载全网图片/视频">
    <meta name="theme-color" content="#4f6ef7">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="万能下载器">
    <link rel="manifest" href="/static/manifest.json">
    <link rel="icon" type="image/png" sizes="192x192" href="/static/icons/icon-192.png">
    <link rel="apple-touch-icon" href="/static/icons/icon-192.png">
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="app">
        <!-- 头部 -->
        <header class="header">
            <h1>🌐 万能下载器</h1>
            <p class="subtitle">粘贴任意链接，自动识别并下载图片/视频</p>
        </header>

        <!-- 输入区 -->
        <div class="input-area">
            <div class="url-input-wrapper">
                <input
                    type="text"
                    id="urlInput"
                    placeholder="粘贴视频链接、帖子链接、图片链接... 支持 B站/抖音/YouTube/小红书/微博 等 1000+ 网站"
                    autocomplete="off"
                />
                <button id="analyzeBtn" class="btn-primary">
                    <span class="icon">🔍</span> 识别
                </button>
                <button id="downloadBtn" class="btn-download" disabled>
                    <span class="icon">⬇️</span> 下载
                </button>
            </div>
            <div class="quick-tips">
                <span>支持:</span>
                <span class="tag">B站</span>
                <span class="tag">抖音</span>
                <span class="tag">YouTube</span>
                <span class="tag">小红书</span>
                <span class="tag">微博</span>
                <span class="tag">快手</span>
                <span class="tag">Instagram</span>
                <span class="tag">Twitter/X</span>
                <span class="tag">直接图片/视频链接</span>
                <span class="tag">...1000+</span>
            </div>
        </div>

        <!-- 分析结果 -->
        <div id="analyzeResult" class="result-panel hidden">
            <div class="result-header">
                <span id="resultType" class="type-badge"></span>
                <span id="resultPlatform" class="platform-badge"></span>
                <span id="resultTitle" class="result-title"></span>
            </div>
            <div id="imagePreview" class="image-preview hidden"></div>
        </div>

        <!-- 下载进度 -->
        <div id="progressPanel" class="progress-panel hidden">
            <div class="progress-bar-wrapper">
                <div id="progressBar" class="progress-bar"></div>
            </div>
            <div class="progress-info">
                <span id="progressText">准备中...</span>
                <span id="progressPercent">0%</span>
            </div>
            <div id="speedInfo" class="speed-info"></div>
        </div>

        <!-- 下载结果 -->
        <div id="resultPanel" class="result-panel hidden">
            <div class="result-success">
                <span>✅ 下载完成!</span>
                <button id="openFolderBtn" class="btn-small">📁 打开文件夹</button>
            </div>
            <div id="resultFiles" class="result-files"></div>
        </div>

        <!-- 标签页 -->
        <div class="tabs">
            <button class="tab active" data-tab="history">📋 下载历史</button>
            <button class="tab" data-tab="files">📁 本地文件</button>
            <button class="tab" data-tab="stats">📊 统计</button>
        </div>

        <!-- 历史记录 -->
        <div id="historyTab" class="tab-content">
            <div class="history-actions">
                <button id="clearHistoryBtn" class="btn-danger btn-small">🗑️ 清空记录</button>
            </div>
            <div id="historyList" class="history-list">
                <div class="empty-state">暂无下载记录，快去下载吧~</div>
            </div>
        </div>

        <!-- 文件列表 -->
        <div id="filesTab" class="tab-content hidden">
            <div id="filesList" class="files-list">
                <div class="empty-state">暂无下载文件</div>
            </div>
        </div>

        <!-- 统计 -->
        <div id="statsTab" class="tab-content hidden">
            <div id="statsContent" class="stats-grid"></div>
        </div>
    </div>

    <script src="/static/js/app.js"></script>
    <script>
        // 注册 Service Worker (PWA)
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(function(reg) { console.log('[PWA] Service Worker 已注册'); })
                .catch(function(err) { console.log('[PWA] Service Worker 注册失败:', err); });
        }
        // URL 分享接收
        window.addEventListener('DOMContentLoaded', function() {
            var params = new URLSearchParams(window.location.search);
            var sharedUrl = params.get('url') || params.get('text');
            if (sharedUrl) {
                document.getElementById('urlInput').value = sharedUrl;
                // 触发分析
                setTimeout(function() {
                    document.getElementById('analyzeBtn').click();
                }, 500);
            }
        });
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    print("=" * 50)
    print("  🌐 万能下载器启动中...")
    print("  支持 1000+ 网站的视频/图片下载")
    print(f"  访问地址: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
