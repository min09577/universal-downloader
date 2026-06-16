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

# ========== Cookies (通过 Kotlin 桥接，主线程安全) ==========

def _get_cookies(domain):
    """安全获取 cookies——通过 Kotlin 桥接在主线程执行"""
    try:
        from com.min0777.universaldownloader import MyApp
        return MyApp.getCookiesSafe(domain)
    except:
        return ""


def _cookies_file(domain):
    """创建临时 cookies 文件"""
    c = _get_cookies(domain)
    if not c:
        return None
    try:
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix='.txt', prefix='cookies_')
        with os.fdopen(fd, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n\n")
            for item in c.split(';'):
                item = item.strip()
                if '=' in item:
                    name, _, value = item.partition('=')
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

        # 平台特殊处理
        domain = _get_domain(url)
        cf = _cookies_file(domain)
        if cf:
            opts["cookiefile"] = cf

        # B站特殊处理
        if "bilibili.com" in domain:
            opts["http_headers"] = {
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
            }

        # 小红书特殊处理：直接尝试 API
        if "xiaohongshu.com" in domain or "xhslink.com" in domain:
            xhs_result = _analyze_xhs(url)
            if xhs_result:
                parsed = json.loads(xhs_result)
                if parsed.get("success"):
                    return xhs_result  # API 成功，直接返回
                # API 失败：如果 is_image → 让调用方尝试图片提取
                if parsed.get("is_image"):
                    return xhs_result  # 返回错误（is_image=True 会让前端展示图片）
            # fall through to yt-dlp as last resort

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
    domain = _get_domain(url)
    dl_dir = get_download_dir()

    try:
        from yt_dlp import YoutubeDL

        opts = _ytdlp_base_opts()
        opts.update({
            "outtmpl": os.path.join(dl_dir, "UD_%(title).80s.%(ext)s"),
            "progress_hooks": [_make_progress_hook(progress_callback)] if progress_callback else [],
            "max_filesize": 500 * 1024 * 1024,
        })

        # === 平台特化 format ===
        if "bilibili.com" in domain:
            # B站全分轨 → 只下 bestvideo（无音频但能看）
            # 有 cookies（登录）→ 可以下原画；无cookies→ 限1080p
            if _get_cookies("bilibili.com"):
                opts["format"] = "bestvideo/best"  # 登录后可下原画
            else:
                opts["format"] = "bestvideo[height<=1080]/bestvideo/best"
            opts["http_headers"] = {"Referer": "https://www.bilibili.com/", "Origin": "https://www.bilibili.com"}
        elif "xiaohongshu.com" in domain or "xhslink.com" in domain:
            # 小红书直接用 requests 解析 HTML
            return _download_xhs(url, dl_dir, progress_callback)
        else:
            # 通用：best 单流
            opts["format"] = "best"

        cf = _cookies_file(domain)
        if cf: opts["cookiefile"] = cf

        with YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)

        return _find_downloaded(dl_dir)

    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:300]})


def _make_progress_hook(cb):
    class Hook:
        def __init__(s, c): s.c = c
        def __call__(s, d):
            if d.get("status") == "downloading" and s.c:
                t = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                dl = d.get("downloaded_bytes", 0)
                if t > 0:
                    try: s.c(int(dl*100/t), f"{d.get('speed',0)/1024/1024:.1f} MB/s" if d.get('speed') else "")
                    except: pass
            elif d.get("status") == "finished" and s.c:
                try: s.c(100, "处理中...")
                except: pass
    return Hook(cb)


def _download_xhs(url, dl_dir, progress_callback):
    """小红书下载：直接从HTML提取视频URL（兼容登录/未登录）"""
    try:
        import requests as req

        url = _resolve_shortlink(url)
        note_id = _extract_note_id(url)
        if not note_id:
            return _safe_json({"success": False, "error": f"无法提取 note_id: {url[:60]}"})

        headers = _xhs_headers()
        cookies = _xhs_cookies()

        # 抓取HTML
        page_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        resp = req.get(page_url, headers=headers, cookies=cookies, timeout=15)
        if resp.status_code != 200:
            return _safe_json({"success": False, "error": f"页面返回{resp.status_code}"})

        html = resp.text
        video_url = None
        title = f"xhs_{note_id}"

        # 策略1: __INITIAL_STATE__ (登录用户能看到完整数据)
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?})\s*</script>', html, re.DOTALL)
        if m:
            try:
                state = json.loads(m.group(1).replace('undefined', 'null'))
                nd = (state.get("note") or {}).get("noteDetailMap", {})
                d = nd.get(note_id) or (list(nd.values())[0] if nd else {})
                if d:
                    title = str(d.get("title") or title)[:60]
                    v = d.get("video", {})
                    stream = (v.get("media") or {}).get("stream", {})
                    for k in ["h265", "h264", "h266"]:
                        if stream.get(k):
                            video_url = stream[k][0].get("master_url", "")
                            break
            except:
                pass

        # 策略2: 直接从HTML匹配video URL (未登录也能匹配到缩略版数据)
        if not video_url:
            # 匹配 JSON 中的 video URLs
            for pat in [
                r'"master_url"\s*:\s*"(https?://[^"]+)"',
                r'"url"\s*:\s*"(https?://[^"]*video[^"]*\.(?:mp4|m3u8)[^"]*)"',
                r'"(?:backup_urls|url)"\s*:\s*\["?(https?://[^"\]]+)"?\]',
                r'<video[^>]+src="([^"]+)"',
                r'<source[^>]+src="([^"]+)"',
            ]:
                matches = re.findall(pat, html)
                if matches:
                    video_url = matches[0]
                    break

        if not video_url:
            return _safe_json({"success": False, "error": "未找到视频地址（需登录或非视频帖）"})

        # 下载
        safe_title = re.sub(r'[\\/*?:"<>|]', '', title)
        filename = f"UD_{safe_title}.mp4"
        filepath = os.path.join(dl_dir, filename)

        # 小红书视频可能需要Referer
        v_headers = dict(_xhs_headers())
        v_headers["Referer"] = "https://www.xiaohongshu.com/"

        resp2 = req.get(video_url, headers=v_headers, stream=True, timeout=120)
        total = int(resp2.headers.get('content-length', 0))
        downloaded = 0
        with open(filepath, "wb") as f:
            for chunk in resp2.iter_content(65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0 and progress_callback:
                    try: progress_callback(int(downloaded*100/total), f"{downloaded/1048576:.1f}/{total/1048576:.1f}MB")
                    except: pass

        size = os.path.getsize(filepath)
        return _safe_json({
            "success": True, "filename": filename, "path": filepath,
            "size_mb": round(size/(1024*1024), 2),
        })

    except Exception as e:
        return _safe_json({"success": False, "error": f"下载异常: {str(e)[:150]}"})


# ========== 小红书工具函数 ==========

def _resolve_shortlink(url):
    """跟踪短链接重定向获取真实 URL"""
    if "xhslink.com" in url:
        try:
            import requests as req
            resp = req.get(url, headers=_xhs_headers(), cookies=_xhs_cookies(),
                          allow_redirects=True, timeout=10)
            return resp.url
        except:
            pass
    return url


def _extract_note_id(url):
    """从小红书URL提取 note_id"""
    m = re.search(r'/item/([a-f0-9]{16,26})', url)
    if m: return m.group(1)
    m = re.search(r'/explore/([a-f0-9]{16,26})', url)
    if m: return m.group(1)
    m = re.search(r'([a-f0-9]{16,26})', url)
    if m: return m.group(1)
    return None


def _xhs_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://www.xiaohongshu.com/",
        "Origin": "https://www.xiaohongshu.com",
        "Accept": "application/json, text/plain, */*",
    }


def _xhs_cookies():
    """获取小红书 cookies dict"""
    cookies = {}
    c = _get_cookies("www.xiaohongshu.com")
    if c:
        for item in c.split(';'):
            item = item.strip()
            if '=' in item:
                k, v = item.split('=', 1)
                cookies[k.strip()] = v.strip()
    return cookies


def _download_fallback(url, dl_dir, domain, progress_callback):
    """回退到 yt-dlp 下载"""
    try:
        from yt_dlp import YoutubeDL
        opts = _ytdlp_base_opts()
        opts.update({
            "outtmpl": os.path.join(dl_dir, "UD_%(title).80s.%(ext)s"),
            "format": "best",
            "progress_hooks": [_make_progress_hook(progress_callback)] if progress_callback else [],
        })
        cf = _cookies_file(domain)
        if cf: opts["cookiefile"] = cf
        with YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
        return _find_downloaded(dl_dir)
    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:200]})


def _find_downloaded(dl_dir):
    """查找最新下载的文件"""
    files = sorted(
        [f for f in Path(dl_dir).iterdir() if f.is_file()],
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    if files:
        f = files[0]
        return _safe_json({"success": True, "filename": f.name, "path": str(f), "size_mb": round(f.stat().st_size/(1024*1024), 2)})
    return _safe_json({"success": False, "error": "下载完成但未找到文件"})


def _analyze_xhs(url):
    """小红书分析：抓HTML提取 __INITIAL_STATE__"""
    try:
        import requests as req

        resolved = _resolve_shortlink(url)
        note_id = _extract_note_id(resolved)
        if not note_id:
            return _safe_json({"success": False, "error": f"无法提取 note_id", "is_image": True})

        headers = _xhs_headers()
        cookies = _xhs_cookies()

        page_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        resp = req.get(page_url, headers=headers, cookies=cookies, timeout=15)

        if resp.status_code != 200:
            return _safe_json({"success": False, "error": f"页面返回 {resp.status_code}", "is_image": True})

        html = resp.text
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?})\s*</script>', html, re.DOTALL)
        if not m:
            return _safe_json({"success": False, "error": "未找到页面数据", "is_image": True})

        state = json.loads(m.group(1).replace('undefined', 'null'))
        nd = (state.get("note") or {}).get("noteDetailMap", {})
        detail = nd.get(note_id) or (list(nd.values())[0] if nd else {})
        if not detail:
            return _safe_json({"success": False, "error": "页面不含笔记", "is_image": True})

        title = str(detail.get("title") or f"xhs_{note_id[:8]}")[:60]
        v = detail.get("video", {})
        has_video = bool(v and (v.get("media") or v.get("url")))

        return _safe_json({
            "success": True, "title": title,
            "duration": v.get("duration", 0) if v else 0,
            "uploader": str((detail.get("user") or {}).get("nickname", "")),
            "thumbnail": "", "formats_count": 1 if has_video else 0, "ext": "mp4",
        })
    except Exception as e:
        return _safe_json({"success": False, "error": f"分析异常: {str(e)[:100]}", "is_image": True})


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
