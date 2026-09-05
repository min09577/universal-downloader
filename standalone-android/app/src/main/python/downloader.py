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


def _bili_cookie_value(name):
    """从 WebView cookie 存储取指定 B站 cookie 值"""
    c = _get_cookies("bilibili.com")
    if not c:
        return ""
    for item in c.split(';'):
        item = item.strip()
        if item.startswith(name + "="):
            return item.partition('=')[2].strip()
    return ""


def _bili_extract_ids(url):
    """BV/av 号 → (aid, cid, title)。走 B站公开 view API，多 P 取第一 P。"""
    try:
        import requests as req
        bv = re.search(r'BV[a-zA-Z0-9]+', url)
        if bv:
            api = f"https://api.bilibili.com/x/web-interface/view?bvid={bv.group(0)}"
        else:
            av = re.search(r'av(\d+)', url, re.IGNORECASE)
            if not av:
                return None
            api = f"https://api.bilibili.com/x/web-interface/view?aid={av.group(1)}"
        resp = req.get(api, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
        }, timeout=15)
        data = resp.json()
        if data.get("code") != 0:
            return None
        d = data.get("data") or {}
        aid = d.get("aid")
        pages = d.get("pages") or []
        cid = pages[0].get("cid") if pages else None
        title = str(d.get("title") or "bilibili")[:60]
        if aid and cid:
            return int(aid), int(cid), title
    except Exception:
        pass
    return None


def _bili_log(msg):
    """降级可观测性：print 进 stdout，Chaquopy 会桥接到 logcat（tag: python.stdout）"""
    try:
        print(f"[bili4k] {msg}", flush=True)
    except Exception:
        pass


def _requests_download_retry(url, filepath, headers, tries=3, progress_cb=None):
    """requests 流式下载，带重试（设备 SSL EOF 属瞬态网络抖动；PC 同 SESSDATA 已证流可用）"""
    import requests as req
    import time
    last_err = None
    for attempt in range(1, tries + 1):
        try:
            resp = req.get(url, headers=headers, stream=True, timeout=30)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            done = 0
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(1 << 16):
                    f.write(chunk)
                    done += len(chunk)
                    if progress_cb and total:
                        try:
                            progress_cb(done, total)
                        except Exception:
                            pass
            return True
        except Exception as e:
            last_err = e
            _bili_log(f"download attempt {attempt}/{tries} failed: {type(e).__name__}: {str(e)[:120]}")
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)  # 清掉半截文件再重试
            except Exception:
                pass
            if attempt < tries:
                time.sleep(2 * attempt)
    _bili_log(f"download gave up after {tries} tries: {type(last_err).__name__}: {str(last_err)[:160]}")
    return False


def _bili_4k(url, dl_dir, progress_callback=None):
    """
    B站 web playurl 4K 路径（bilibili + 目标 qn>=120 + yt-dlp 无高画质流时触发）:
    web playurl API（SESSDATA cookie + qn=120 + fourk=1 + fnval=16）拿 DASH 双流直链
    → requests 带 Referer 下载（含重试） → needs_remux 交现有 FFmpegKit 管线。
    SESSDATA 即 web 端合法凭证（4K 需 VIP 账号）；无登录态/拿不到 4K 流一律返回 None，
    调用方降级回 yt-dlp 旧路径。所有降级分支均打日志（logcat 可见）。
    """
    _bili_log(f"enter: url={url[:80]}")
    try:
        import requests as req

        ids = _bili_extract_ids(url)
        if not ids:
            _bili_log("abort: extract aid/cid failed (view API)")
            return None
        aid, cid, title = ids

        sessdata = _bili_cookie_value("SESSDATA")
        if not sessdata:
            _bili_log("abort: no SESSDATA (not logged in)")
            return None  # 无登录态，web playurl 4K 必失败，尽早降级
        buvid = _bili_cookie_value("buvid3")

        api = "https://api.bilibili.com/x/player/playurl"
        params = {"avid": aid, "cid": cid, "qn": 120, "fnval": 16, "fourk": 1}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
        }
        cookies = {"SESSDATA": sessdata}
        if buvid:
            cookies["buvid3"] = buvid
        resp = req.get(api, params=params, headers=headers, cookies=cookies, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            _bili_log(f"abort: playurl api code={data.get('code')} msg={str(data.get('message'))[:80]}")
            return None
        d = data.get("data") or {}
        dash = d.get("dash") or {}
        videos = dash.get("video") or []
        audios = dash.get("audio") or []
        # 仅接受 qn=120 的视频流（API 在无 4K 权限/片源时会静默降档到 1080，
        # 此时 dash.video 里没有 id==120，直接降级交 yt-dlp，绝不把低清流标成 4K）
        v4k = [v for v in videos if int(v.get("id") or 0) == 120]
        if not v4k:
            ids_avail = sorted({int(v.get("id") or 0) for v in videos})
            _bili_log(f"abort: no qn=120 stream, available={ids_avail}")
            return None

        def _bw(v):
            try:
                return int(v.get("bandwidth") or 0)
            except Exception:
                return 0

        v = max(v4k, key=_bw)
        v_url = v.get("baseUrl") or v.get("base_url") or ""
        if audios:
            a = max(audios, key=_bw)
            a_url = a.get("baseUrl") or a.get("base_url") or ""
        else:
            a_url = ""
        if not v_url or not a_url:
            _bili_log(f"abort: empty stream url (v={bool(v_url)} a={bool(a_url)})")
            return None

        safe_title = re.sub(r'[\\/*?:"<>|]', '', title) or f"bili_{aid}"
        dl_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
        }

        v_file = os.path.join(dl_dir, f"UD_{safe_title}_video.m4s")
        a_file = os.path.join(dl_dir, f"UD_{safe_title}_audio.m4s")

        def _report(done, total, base_pct, span_pct):
            if progress_callback and total:
                pct = base_pct + int(done * span_pct / total)
                try:
                    progress_callback(min(pct, 99), f"{done/1048576:.1f}MB")
                except Exception:
                    pass

        _bili_log("downloading video stream (4K)...")
        if not _requests_download_retry(v_url, v_file, dl_headers, tries=3,
                                        progress_cb=lambda dn, tt: _report(dn, tt, 0, 70)):
            return None  # 视频流重试耗尽 → 降级
        _bili_log("downloading audio stream...")
        if not _requests_download_retry(a_url, a_file, dl_headers, tries=3,
                                        progress_cb=lambda dn, tt: _report(dn, tt, 70, 29)):
            return None  # 音频流重试耗尽 → 降级
        if progress_callback:
            try:
                progress_callback(100, "处理中...")
            except Exception:
                pass

        v_size = os.path.getsize(v_file)
        a_size = os.path.getsize(a_file)
        if v_size < 100 * 1024:
            _bili_log(f"abort: video stream too small ({v_size}B), suspected risk-control")
            return None  # 流过小，疑似风控/无效响应
        total = v_size + a_size
        _bili_log(f"ok: v={v_size/1048576:.1f}MB a={a_size/1048576:.1f}MB")
        return _safe_json({
            "success": True, "needs_remux": True,
            "filename": safe_title,
            "path": v_file, "files": [v_file, a_file],
            "size_mb": round(total / (1024 * 1024), 2),
            "note": f"B站 4K 流(web playurl qn=120)",
        })
    except Exception as e:
        _bili_log(f"abort: unexpected {type(e).__name__}: {str(e)[:200]}")
        return None  # 任何异常 → 降级回 yt-dlp 旧路径


# ========== 西瓜视频专管线（纯 Python 极简链路） ==========
# 分享短链(v.douyin.com/v.ixigua.com) → 302 到 iesdouyin.com/xg/video/{item_id}
# → 页面 regex 提取 video_id(v0xx...) → GET /aweme/v1/play/?video_id=...&ratio=1080p
# → 302 douyinvod 直链 → 标准 MP4（h264+aac 已拼好），无需登录/签名/拼装。

_IXIGUA_UA_PAGE = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
_IXIGUA_UA_PLAY = "com.ss.android.ugc.aweme/110101"


def _ixigua_log(msg):
    """降级可观测性：print 进 stdout，Chaquopy 桥接到 logcat（tag: python.stdout）"""
    try:
        print(f"[ixigua] {msg}", flush=True)
    except Exception:
        pass


def _ixigua_shortlink_resolve(url):
    """分享短链逐跳 302（最多 5 跳），返回最终页面 URL；失败原样返回"""
    import requests as req
    cur = url
    try:
        for _ in range(5):
            r = req.get(cur, headers={"User-Agent": _IXIGUA_UA_PAGE},
                        allow_redirects=False, stream=True, timeout=15)
            loc = r.headers.get("Location")
            r.close()
            if not loc or r.status_code not in (301, 302, 303, 307, 308):
                break
            cur = loc if loc.startswith("http") else f"https://{urlparse(cur).netloc}{loc}"
    except Exception as e:
        _ixigua_log(f"shortlink resolve failed: {type(e).__name__}: {str(e)[:120]}")
    return cur


def _ixigua_4k(url, dl_dir, progress_callback=None):
    """
    西瓜极简管线：短链 302 → iesdouyin 页面 regex 提取 video_id → play API 302 直链
    → requests 直下完整 MP4（音轨已拼好，needs_remux=False）。
    任一步失败打 [ixigua] 日志并返回 None，调用方降级 yt-dlp 通用路径。
    ratio=1080p 为服务端最高可用档（4K 片源亦从此口下发实际最优）。
    """
    _ixigua_log(f"enter: url={url[:80]}")
    try:
        import requests as req

        # ① 短链 302 拿最终页（含 item_id）
        page_url = _ixigua_shortlink_resolve(url)
        m = re.search(r"/(?:xg/)?video/(\d{15,})", page_url)
        if not m:
            # 标准长链两种形态：ixigua.com/{id}（无 video/ 前缀）与 ixigua.com/video/{id}
            m = re.search(r"ixigua\.com/(?:video/)?(\d{15,})", page_url)
        if not m:
            _ixigua_log("abort: no item id after resolve")
            return None
        item_id = m.group(1)

        # ② 页面 regex 提取 video_id
        # 标准长链直访会被 jsvmp 风控壳拦截（分享链 302 落点 iesdouyin 无此拦截），
        # 统一改走 iesdouyin 移动页：m.ixigua.com 与 iesdouyin/xg/video 同源同构
        page = page_url
        if "iesdouyin.com" not in page_url:
            page = f"https://www.iesdouyin.com/xg/video/{item_id}/"
        headers = {"User-Agent": _IXIGUA_UA_PAGE, "Referer": "https://www.douyin.com/"}
        resp = req.get(page, headers=headers, timeout=20)
        resp.raise_for_status()
        # 优先 video_id 上下文命中（页面含封面 vid 等干扰串，无上下文匹配会选错）
        vm = re.search(r'video_id["\':= ]{1,4}(v0[0-9a-zA-Z]{18,})', resp.text)
        vid = vm.group(1) if vm else None
        vids = [vid] if vid else []
        if not vids:
            _ixigua_log("abort: no video_id in page (deleted/risk?)")
            return None
        _ixigua_log(f"item_id={item_id} video_id={vid[:20]}...")

        # ③ play API → 302 直链
        api = f"https://www.iesdouyin.com/aweme/v1/play/?video_id={vid}&ratio=1080p&line=0"
        r2 = req.get(api, headers={"User-Agent": _IXIGUA_UA_PLAY}, allow_redirects=False, timeout=15)
        direct = r2.headers.get("Location") or api
        if r2.status_code not in (301, 302, 303, 307, 308):
            _ixigua_log(f"abort: play api no redirect ({r2.status_code})")
            return None

        safe_title = f"ixigua_{item_id}"
        out_file = os.path.join(dl_dir, f"UD_{safe_title}.mp4")

        def _cb(done, total):
            if progress_callback and total:
                try:
                    progress_callback(min(int(done * 99 / total), 99), f"{done/1048576:.1f}MB")
                except Exception:
                    pass

        # ④ 直下完整 MP4（复用重试逻辑）
        if not _requests_download_retry(direct, out_file,
                                        {"User-Agent": _IXIGUA_UA_PLAY, "Referer": "https://www.ixigua.com/"},
                                        progress_cb=_cb):
            return None
        if progress_callback:
            try:
                progress_callback(100, "处理中...")
            except Exception:
                pass

        size = os.path.getsize(out_file)
        if size < 100 * 1024:
            _ixigua_log(f"file too small ({size}B), suspected risk response")
            try:
                os.remove(out_file)
            except Exception:
                pass
            return None
        _ixigua_log(f"ok: {size/1048576:.1f}MB direct mp4 (h264+aac muxed)")
        return _safe_json({
            "success": True,
            "needs_remux": False,  # 服务端已拼好音轨
            "filename": f"{safe_title}.mp4",
            "path": out_file,
            "size_mb": round(size / (1024 * 1024), 2),
            "note": "ixigua 极简直链 (ratio=1080p)",
        })
    except Exception as e:
        _ixigua_log(f"exception: {type(e).__name__}: {str(e)[:200]}")
        return None


# ========== 抖音专管线（Kotlin WebView 渲染解析 + play 网关直链） ==========
# 服务端 API 全被 Argus 拦（aweme/detail 需 a_bogus 签名），纯 Python 拿不到 video_id；
# video_id 由 Kotlin DouyinWebViewResolver 在真渲染 WebView 里捕获（三路：play 请求 query /
# douyinvod 媒体 URL / _ROUTER_DATA 轮询）。拿到 video_id 后走 aweme/v1/play 网关 302 直链
# （无签名，UA 用 app 标识；ratio 阶梯 540p/720p/1080p 实测递增，2k/4k 接受但片源封顶 1080）。

_DY_UA_PLAY = "com.ss.android.ugc.aweme/110101"


def _douyin_log(msg):
    try:
        print(f"[douyin] {msg}", flush=True)
    except Exception:
        pass


def _douyin_is_share(url):
    """抖音链接形态识别：v.douyin.com 分享码 / iesdouyin share 页 / douyin.com 长链"""
    return ("v.douyin.com" in url
            or "iesdouyin.com/share" in url
            or "iesdouyin.com/video" in url
            or re.search(r'douyin\.com/(?:video/)?\d{15,}', url) is not None)


def _douyin_direct(url, dl_dir, progress_callback=None):
    """
    抖音直链管线：Kotlin DouyinWebViewResolver.resolve(短链) 拿 video_id
    → aweme/v1/play 网关 302 直链 → requests 直下完整 MP4（音轨已拼好，needs_remux=False）。
    ratio 从 1080p 起阶梯降级探测（4k/2k 对无高画源服务端自动回落 1080p）。
    任一步失败打 [douyin] 日志并返回 None，调用方降级 yt-dlp DouyinIE。
    """
    _douyin_log(f"enter: url={url[:80]}")
    try:
        import requests as req

        # ① Kotlin WebView 渲染解析 → video_id
        from com.min0777.universaldownloader import DouyinWebViewResolver
        page_url = _ixigua_shortlink_resolve(url)  # v.douyin.com 短链先 302 展开（无风险，纯 302）
        target = page_url if ("iesdouyin.com/share" in page_url or "iesdouyin.com/video" in page_url) else url
        vid = DouyinWebViewResolver.resolve(target)
        DouyinWebViewResolver.cleanup()
        if not vid:
            _douyin_log("abort: resolver returned no video_id")
            return None
        _douyin_log(f"video_id={vid[:26]}...")

        # ② play 网关 302 → 直链（ratio 阶梯：1080p 起步，服务端无高画源自动回落）
        direct = None
        for ratio in ("1080p", "720p", "540p", "default"):
            api = f"https://www.iesdouyin.com/aweme/v1/play/?video_id={vid}&ratio={ratio}&line=0"
            r2 = req.get(api, headers={"User-Agent": _DY_UA_PLAY}, allow_redirects=False, timeout=15)
            if r2.status_code in (301, 302, 303, 307, 308):
                loc = r2.headers.get("Location") or ""
                if loc.startswith("http"):
                    direct = loc
                    _douyin_log(f"ratio={ratio} -> 302 ok")
                    break
        if not direct:
            _douyin_log("abort: play gateway no redirect on all ratios")
            return None

        safe_title = f"dy_{vid[:26]}"
        out_file = os.path.join(dl_dir, f"UD_{safe_title}.mp4")

        def _cb(done, total):
            if progress_callback and total:
                try:
                    progress_callback(min(int(done * 99 / total), 99), f"{done/1048576:.1f}MB")
                except Exception:
                    pass

        # ③ 直下完整 MP4（UA 用 app 标识 + douyin Referer；实测 302 落点 HEAD 200）
        if not _requests_download_retry(direct, out_file,
                                        {"User-Agent": _DY_UA_PLAY, "Referer": "https://www.douyin.com/"},
                                        progress_cb=_cb):
            return None
        if progress_callback:
            try:
                progress_callback(100, "处理中...")
            except Exception:
                pass

        size = os.path.getsize(out_file)
        if size < 100 * 1024:
            _douyin_log(f"file too small ({size}B), suspected risk response")
            try:
                os.remove(out_file)
            except Exception:
                pass
            return None
        _douyin_log(f"ok: {size/1048576:.1f}MB direct mp4 (muxed)")
        return _safe_json({
            "success": True,
            "needs_remux": False,  # 服务端已拼好音轨
            "filename": f"{safe_title}.mp4",
            "path": out_file,
            "size_mb": round(size / (1024 * 1024), 2),
            "note": "douyin WebView 直链 (aweme/v1/play 302)",
        })
    except Exception as e:
        _douyin_log(f"exception: {type(e).__name__}: {str(e)[:200]}")
        return None


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

    # 西瓜/字节分享链: v.ixigua.com 与 v.douyin.com 分享码 → 由 _ixigua_4k 内部 302 解析
    # （短链码≠item_id，需网络跳转；此处透传不做破坏性改写）
    if "ixigua.com" in netloc:
        m = re.search(r'ixigua\.com/(?:video/)?(\d{6,})', url)
        if m:
            return f"https://www.ixigua.com/{m.group(1)}"
        return url  # v.ixigua.com 分享码等

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
        if "xiaohongshu.com" in domain or "xhslink.com" in domain or "xhslink.cn" in domain:
            xhs_result = _analyze_xhs(url)
            if xhs_result:
                parsed = json.loads(xhs_result)
                if parsed.get("success"):
                    return xhs_result  # API 成功，直接返回
                # API 失败：如果 is_image → 让调用方尝试图片提取
                if parsed.get("is_image"):
                    return xhs_result  # 返回错误（is_image=True 会让前端展示图片）
            # fall through to yt-dlp as last resort

        # 抖音/西瓜特殊处理：识别阶段不跑 yt-dlp（DouyinIE/IxiguaIE 强依赖 fresh
        # cookies，识别必失败 → btnDownload 永不 enable → 下载阶段直链管线死锁不可达）。
        # 识别只需确认链接形态即放行，真实解析留给下载阶段直链管线（_douyin_direct/_ixigua_4k）。
        if ("douyin.com" in domain or "iesdouyin.com" in domain or "ixigua.com" in domain):
            label = "西瓜视频" if "ixigua.com" in domain else "抖音视频"
            title = label
            try:
                # 尽力补可读标题：短链 302 展开（纯 302 无风控），失败不影响放行
                page_url = _ixigua_shortlink_resolve(url)
                m = (re.search(r"/video/(\d{15,})", page_url)
                     or re.search(r"ixigua\.com/(?:video/)?(\d{15,})", page_url))
                if m:
                    if "xg/video" in page_url:
                        label = "西瓜视频"  # v.douyin.com 落点 xg/video = 西瓜分享码
                    title = f"{label}_{m.group(1)}"
            except Exception:
                pass
            return _safe_json({
                "success": True,
                "title": title[:200],
                "duration": 0,
                "uploader": "",
                "thumbnail": "",
                "formats_count": 1,
                "ext": "mp4",
            })

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


def _has_ffmpeg():
    """检测 ffmpeg 是否可用（Android Chaquopy 默认无；PC/内置 ffmpeg-kit 时有）"""
    try:
        import subprocess
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        pass
    loc = os.environ.get("UD_FFMPEG_PATH")
    if loc and os.path.isfile(loc):
        return True
    return False


def _pick_newest_by_template(dl_dir, template_prefix, exts, min_mtime=0):
    """
    按 outtmpl 模板前缀匹配产物文件（UD_<title>.<ext>），mtime 需晚于 min_mtime 兜底，
    消除目录内历史残留文件被误认成本次下载的问题。
    """
    cands = []
    for name in os.listdir(dl_dir):
        if not name.startswith(template_prefix):
            continue
        ext = os.path.splitext(name)[1].lower().strip(".")
        if ext not in exts:
            continue
        path = os.path.join(dl_dir, name)
        if os.path.isfile(path) and os.path.getmtime(path) >= min_mtime:
            cands.append(path)
    if not cands:
        return None
    return max(cands, key=os.path.getmtime)


def _pick_newest(names, dl_dir, exts):
    """从文件名集合中选出最新的指定扩展名文件（返回绝对路径或 None）"""
    cands = [os.path.join(dl_dir, n) for n in names
             if os.path.splitext(n)[1].lower().strip(".") in exts]
    if not cands:
        return None
    return max(cands, key=os.path.getmtime)


def _two_pass_streams(url, dl_dir, v_format, a_format, base_opts, progress_callback=None):
    """
    无 ffmpeg 两遍单流下载（B站 ai.1.0.11~14 已验证方案的通用化）：
    先视频流再音频流，单流不触发 yt-dlp 合并器，产物交 Kotlin MediaMuxer/FFmpegKit 拼装。
    产物按 UD_ 模板前缀 + mtime 时间窗匹配。返回 _safe_json 结果 JSON 串。
    """
    import time as _time
    from yt_dlp import YoutubeDL
    opts = dict(base_opts)
    ts_v = _time.time()
    opts_v = dict(opts); opts_v["format"] = v_format
    with YoutubeDL(opts_v) as ydl:
        ydl.extract_info(url, download=True)
    v_file = _pick_newest_by_template(dl_dir, "UD_", ("mp4", "mkv", "webm"), min_mtime=ts_v)
    if not v_file:
        v_file = _pick_newest_by_template(dl_dir, "UD_", ("mp4", "mkv", "webm"))

    ts_a = _time.time()
    opts_a = dict(opts); opts_a["format"] = a_format
    with YoutubeDL(opts_a) as ydl:
        ydl.extract_info(url, download=True)
    a_file = _pick_newest_by_template(dl_dir, "UD_", ("m4a", "mp3", "mp4"), min_mtime=ts_a)
    if a_file and a_file == v_file:
        a_file = None
    if not a_file:
        a_cands = []
        for name in os.listdir(dl_dir):
            if not name.startswith("UD_"):
                continue
            ext = os.path.splitext(name)[1].lower().strip(".")
            if ext in ("m4a", "mp3", "mp4") and os.path.isfile(os.path.join(dl_dir, name)):
                p = os.path.join(dl_dir, name)
                if p != v_file:
                    a_cands.append(p)
        if a_cands:
            a_file = max(a_cands, key=os.path.getmtime)

    if not v_file:
        return _safe_json({"success": False, "error": "视频流下载失败(可能触发风控, 请重试或保持登录)"})
    if not a_file:
        return _safe_json({"success": True, "filename": os.path.basename(v_file),
                           "path": v_file, "size_mb": round(os.path.getsize(v_file)/(1024*1024), 2),
                           "note": "音频流下载失败, 本次无声音"})
    total = os.path.getsize(v_file) + os.path.getsize(a_file)
    return _safe_json({
        "success": True, "needs_remux": True,
        "filename": os.path.splitext(os.path.basename(v_file))[0],
        "path": v_file, "files": [v_file, a_file],
        "size_mb": round(total/(1024*1024), 2),
    })


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

        has_ff = _has_ffmpeg()
        if has_ff:
            opts["ffmpeg_location"] = os.environ.get("UD_FFMPEG_PATH") or "ffmpeg"

        # === 平台特化 format ===
        if "bilibili.com" in domain:
            # 4K 路径优先：直接以 playurl 实际下发为准（SESSDATA+qn=120+fourk=1，
            # 严格筛 id==120 流），不用猜 yt-dlp 元数据（元数据里的 2160 流可能是
            # 需 VIP 的 HEVC Main10，实际不可下载）。拿不到（非VIP/无限免/无4K片源）
            # 自动降级 yt-dlp 现有双轨逻辑。
            grpc_result = _bili_4k(url, dl_dir, progress_callback)
            if grpc_result:
                return grpc_result
            # B站 DASH: 视频/音频分轨
            if has_ff:
                # ffmpeg 可用 → 单次下载并合并出有声视频（实证 1080P+AAC）
                opts["format"] = "bestvideo+bestaudio/best"
                opts["http_headers"] = {"Referer": "https://www.bilibili.com/", "Origin": "https://www.bilibili.com"}
                cf = _cookies_file(domain)
                if cf: opts["cookiefile"] = cf
                with YoutubeDL(opts) as ydl:
                    ydl.extract_info(url, download=True)
                return _find_downloaded(dl_dir)
            # 无 ffmpeg → 两遍单流下载（通用化方案，交 MediaMuxer 拼装）
            # 视频流必须 H.264(avc1)+mp4: MediaMuxer 不支持 AV1(100026) / HEVC 兼容性差(100113)
            opts["http_headers"] = {"Referer": "https://www.bilibili.com/", "Origin": "https://www.bilibili.com"}
            cf = _cookies_file(domain)
            if cf: opts["cookiefile"] = cf
            return _two_pass_streams(
                url, dl_dir,
                "bestvideo[vcodec^=avc1][height<=1080]/bestvideo[vcodec^=avc1]/bestvideo[vcodec^=avc1][ext=mp4]",
                "bestaudio[ext=m4a]/bestaudio",
                opts, progress_callback)

        elif "v.douyin.com" in domain:
            # v.douyin.com 分享码既可能是抖音也可能是西瓜：先走西瓜管线 302 解析
            # （解析出 /xg/video/ 即西瓜），失败再走抖音 WebView 直链，最后 yt-dlp
            ixg = _ixigua_4k(url, dl_dir, progress_callback)
            if ixg:
                return ixg
            dy = _douyin_direct(url, dl_dir, progress_callback)
            if dy:
                return dy
            # 抖音降级：走 yt-dlp DouyinIE（无 ffmpeg 时同样避免 bv*+ba 合并需求）
            if has_ff:
                opts["format"] = "bv*+ba/b"
            else:
                return _two_pass_streams(
                    url, dl_dir,
                    "bestvideo[ext=mp4]/bestvideo",
                    "bestaudio[ext=m4a]/bestaudio",
                    opts, progress_callback)
        elif "douyin.com" in domain or "iesdouyin.com" in domain:
            # 抖音主域（www.douyin.com 长链 / iesdouyin share 页）：WebView 直链优先
            dy = _douyin_direct(url, dl_dir, progress_callback)
            if dy:
                return dy
            if has_ff:
                opts["format"] = "bv*+ba/b"
            else:
                return _two_pass_streams(
                    url, dl_dir,
                    "bestvideo[ext=mp4]/bestvideo",
                    "bestaudio[ext=m4a]/bestaudio",
                    opts, progress_callback)
        elif "ixigua.com" in domain:
            # 西瓜专管线（极简）：分享短链 302 → video_id → play API 直链 MP4（h264+aac 已拼好）
            ixg = _ixigua_4k(url, dl_dir, progress_callback)
            if ixg:
                return ixg
            opts["format"] = "bestvideo*+bestaudio/best" if has_ff else "best"
            opts["http_headers"] = {"Referer": "https://www.ixigua.com/", "Origin": "https://www.ixigua.com"}
        elif "xiaohongshu.com" in domain or "xhslink.com" in domain or "xhslink.cn" in domain:
            # 小红书直接用 requests 解析 HTML
            return _download_xhs(url, dl_dir, progress_callback)
        else:
            # 通用/YouTube：新 yt-dlp 无合并流站点 'best' 直接报 not available。
            # 按 _has_ffmpeg 分流（bv*+ba 无合并器时触发 Need merger，与 B站 ai.1.0.9 同款问题）：
            # 有 ffmpeg → bestvideo+bestaudio/best 合并；无 ffmpeg → 两遍单流交 MediaMuxer
            if has_ff:
                opts["format"] = "bestvideo+bestaudio/best"
            else:
                return _two_pass_streams(
                    url, dl_dir,
                    "bestvideo[ext=mp4]/bestvideo",
                    "bestaudio[ext=m4a]/bestaudio",
                    opts, progress_callback)

        cf = _cookies_file(domain)
        if cf: opts["cookiefile"] = cf

        with YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)

        return _find_downloaded(dl_dir)

    except Exception as e:
        return _safe_json({"success": False, "error": str(e)[:300]})


def _make_progress_hook(cb):
    """cb 可为 Python callable 或 Chaquopy 传入的 Java DownloadProgressCallback 对象"""
    class Hook:
        def __init__(s, c): s.c = c
        def __call__(s, d):
            if d.get("status") == "downloading" and s.c:
                t = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                dl = d.get("downloaded_bytes", 0)
                if t > 0:
                    try: s.c(int(dl*100/t), f"{d.get('speed',0)/1024/1024:.1f} MB/s" if d.get('speed') else "")
                    except Exception: pass
            elif d.get("status") == "finished" and s.c:
                try: s.c(100, "处理中...")
                except Exception: pass
    return Hook(cb)


def _fetch_note_detail(note_id, resolved_url):
    """请求笔记页并解析详情，返回 (state, detail) 或 (None, None)。保留 xsec_token。"""
    try:
        import requests as req
        headers = _xhs_headers()
        cookies = _xhs_cookies()
        page_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        qs = urlparse(resolved_url).query
        if qs:
            page_url += "?" + qs  # xsec_token 缺失时详情页不放数据
        resp = req.get(page_url, headers=headers, cookies=cookies, timeout=15)
        if resp.status_code != 200:
            return None, None
        from parse_state import parse_initial_state, unwrap_note_detail
        state = parse_initial_state(resp.text)
        if not state:
            return None, None
        return state, unwrap_note_detail(state, note_id)
    except Exception:
        return None, None


def _download_xhs(url, dl_dir, progress_callback):
    """
    小红书下载 (2026-09 适配版):
      统一先解析页面详情 → 图文帖直接批量下载 / 视频帖直连 masterUrl 下载。
      yt-dlp 仅作视频兜底（其对小红书适配常滞后）。
    """
    clean_url = normalize_url(url)
    clean_url = _resolve_shortlink(clean_url)
    clean_url = normalize_url(clean_url)
    note_id = _extract_note_id(clean_url)

    if note_id:
        state, detail = _fetch_note_detail(note_id, clean_url)
        if detail:
            # 图文帖 → 批量下载
            if (detail.get("imageList") or detail.get("image_list")) and detail.get("type") != "video":
                return _download_xhs_images(detail, dl_dir, progress_callback)
            # 视频帖 → 直连 masterUrl 下载
            media = ((detail.get("video") or {}).get("media")) or {}
            stream = media.get("stream") or {}
            # stream 分组键不固定(旧版 h264/h265, 2026 版 EF4~EF7), 遍历所有组按码率取最优
            candidates = []
            for tier, arr in stream.items():
                if isinstance(arr, list):
                    for s in arr:
                        if isinstance(s, dict) and s.get("masterUrl"):
                            candidates.append(s)
            video_url = ""
            if candidates:
                best = max(candidates, key=lambda s: s.get("videoBitrate") or 0)
                video_url = best.get("masterUrl", "")
            if not video_url:
                video_url = media.get("url") or (detail.get("video") or {}).get("url") or ""
            if video_url:
                if video_url.startswith("//"):
                    video_url = "https:" + video_url
                return _download_xhs_video_direct(video_url, detail, note_id, dl_dir, progress_callback)

    # 兜底: yt-dlp（视频帖解析失败或非 XHS 结构变化）
    result = _download_fallback(clean_url, dl_dir, "www.xiaohongshu.com", progress_callback)
    parsed = json.loads(result)
    if parsed.get("success"):
        return result

    # yt-dlp 也失败 → 最后再试一次页面图片提取（防风控临时失败）
    if note_id:
        state, detail = _fetch_note_detail(note_id, clean_url)
        if detail and (detail.get("imageList") or detail.get("image_list")):
            return _download_xhs_images(detail, dl_dir, progress_callback)

    return result  # 返回原始错误


def _download_xhs_video_direct(video_url, detail, note_id, dl_dir, progress_callback):
    """直连视频 masterUrl 下载（h264 stream，requests 流式）"""
    try:
        import requests as req
        title = str(detail.get("title") or f"xhs_{note_id[:8]}")[:40]
        safe_title = re.sub(r'[\\/*?:"<>|]', '', title) or f"xhs_{note_id[:8]}"
        filepath = os.path.join(dl_dir, f"UD_{safe_title}.mp4")
        headers = dict(_xhs_headers())
        headers["Referer"] = "https://www.xiaohongshu.com/"
        resp = req.get(video_url, headers=headers, stream=True, timeout=30)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        done = 0
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(1 << 16):
                f.write(chunk)
                done += len(chunk)
                if progress_callback and total:
                    try:
                        progress_callback(int(done * 100 / total), f"{done/1048576:.1f}/{total/1048576:.1f}MB")
                    except Exception:
                        pass
        size = os.path.getsize(filepath)
        if size < 10 * 1024:
            os.remove(filepath)
            return _safe_json({"success": False, "error": f"视频文件过小({size}B)，可能被风控"})
        return _safe_json({"success": True, "filename": f"{safe_title}.mp4",
                           "path": filepath, "size_mb": round(size / 1048576, 2)})
    except Exception as e:
        return _safe_json({"success": False, "error": f"视频直连下载失败: {str(e)[:150]}"})


def _download_raw_images(img_urls, note_id, dl_dir, progress_callback):
    """直接从 HTML 中匹配到的图片 URL 下载"""
    try:
        import requests as req
        total = len(img_urls)
        downloaded = []
        for i, img_url in enumerate(img_urls):
            ext = "jpg"
            if ".png" in img_url.lower(): ext = "png"
            if ".webp" in img_url.lower(): ext = "webp"
            filename = f"UD_xhs_{note_id[:8]}_{i+1}.{ext}"
            filepath = os.path.join(dl_dir, filename)
            resp = req.get(img_url, headers=_xhs_headers(), stream=True, timeout=30)
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
            downloaded.append(filepath)
            if progress_callback:
                try: progress_callback(int((i+1)*100/total), f"{i+1}/{total}")
                except: pass
        if downloaded:
            tsize = sum(os.path.getsize(p) for p in downloaded)
            return _safe_json({"success": True, "filename": f"xhs_{note_id[:8]} ({len(downloaded)}张)",
                              "path": os.path.dirname(downloaded[0]), "size_mb": round(tsize/(1024*1024), 2)})
    except:
        pass
    return _safe_json({"success": False, "error": "无法下载图片"})


def _download_xhs_images(detail, dl_dir, progress_callback):
    """下载小红书图文帖的所有图片（URL 提取统一走 _xhs_image_urls，兼容新旧字段）"""
    try:
        import requests as req
        title = str(detail.get("title") or f"xhs_images")[:40]
        safe_title = re.sub(r'[\\/*?:"<>|]', '', title)
        img_list = _xhs_image_urls(detail)

        downloaded = []
        total = len(img_list)
        if not total:
            return _safe_json({"success": False, "error": "未找到可下载的图片"})
        for i, img_url in enumerate(img_list):

            ext = "jpg"
            if ".png" in img_url.lower(): ext = "png"
            elif ".webp" in img_url.lower(): ext = "webp"
            elif ".gif" in img_url.lower(): ext = "gif"

            filename = f"UD_{safe_title}_{i+1}.{ext}"
            filepath = os.path.join(dl_dir, filename)

            headers = _xhs_headers()
            resp = req.get(img_url, headers=headers, stream=True, timeout=30)
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)

            downloaded.append(filepath)
            if progress_callback:
                try: progress_callback(int((i+1)*100/total), f"{i+1}/{total}")
                except: pass

        if downloaded:
            total_size = sum(os.path.getsize(p) for p in downloaded)
            return _safe_json({
                "success": True, "filename": f"{safe_title} ({len(downloaded)}张图)",
                # path 指向真实首图文件；files 为全部落盘文件（App 端逐个 MediaStore 落盘）
                "path": downloaded[0],
                "files": downloaded,
                "size_mb": round(total_size/(1024*1024), 2),
            })
        return _safe_json({"success": False, "error": "未找到可下载的图片"})
    except Exception as e:
        return _safe_json({"success": False, "error": f"图片下载异常: {str(e)[:150]}"})


# ========== 小红书工具函数 ==========

def _resolve_shortlink(url):
    """跟踪短链接重定向获取真实 URL (支持 xhslink.com / xhslink.cn)"""
    if "xhslink.com" in url or "xhslink.cn" in url:
        try:
            import requests as req
            resp = req.get(url, headers=_xhs_headers(), cookies=_xhs_cookies(),
                          allow_redirects=True, timeout=10)
            return resp.url
        except:
            pass
    return url


def _extract_note_id(url):
    """从小红书URL提取 note_id (兼容路径式与query式: /explore?target_note_id=xxx)"""
    m = re.search(r'/item/([a-f0-9]{16,26})', url)
    if m: return m.group(1)
    m = re.search(r'/explore/([a-f0-9]{16,26})', url)
    if m: return m.group(1)
    # App 分享长链: id 在 query 里 (target_note_id/note_id)，勿被 appuid 干扰
    try:
        qs = parse_qs(urlparse(url).query)
        for k in ("target_note_id", "note_id", "noteId"):
            v = qs.get(k, [None])[0]
            if v and re.fullmatch(r'[a-f0-9]{16,26}', v):
                return v
    except Exception:
        pass
    # 兜底仅在路径内找（全 URL 扫描会误抓 appuid 等十六进制参数）
    m = re.search(r'([a-f0-9]{16,26})', urlparse(url).path)
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
    """小红书分析：抓HTML提取 __INITIAL_STATE__ (2026-09 适配 new Map/camelCase/xsec_token)"""
    try:
        import requests as req
        try:
            from parse_state import parse_initial_state, unwrap_note_detail
        except ImportError:
            return _safe_json({"success": False, "error": "parse_state 模块缺失", "is_image": True})

        resolved = _resolve_shortlink(url)
        note_id = _extract_note_id(resolved)
        if not note_id:
            return _safe_json({"success": False, "error": f"无法提取 note_id", "is_image": True})

        headers = _xhs_headers()
        cookies = _xhs_cookies()

        page_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        qs = urlparse(resolved).query
        if qs:
            page_url += "?" + qs  # 保留 xsec_token，缺它详情页不给数据

        resp = req.get(page_url, headers=headers, cookies=cookies, timeout=15)
        if resp.status_code != 200:
            return _safe_json({"success": False, "error": f"页面返回 {resp.status_code}", "is_image": True})

        state = parse_initial_state(resp.text)
        if not state:
            return _safe_json({"success": False, "error": "页面数据解析失败(可能被风控)", "is_image": True})

        detail = unwrap_note_detail(state, note_id)
        if not detail:
            return _safe_json({"success": False, "error": "页面不含笔记", "is_image": True})

        title = str(detail.get("title") or detail.get("desc") or f"xhs_{note_id[:8]}")[:60]
        v = detail.get("video") or {}
        has_video = bool(detail.get("type") == "video" or v.get("media") or v.get("url"))

        images = _xhs_image_urls(detail)

        result = {
            "success": True, "title": title,
            "uploader": str((detail.get("user") or {}).get("nickname", "")),
            "thumbnail": "", "ext": "mp4",
        }
        if has_video:
            result["duration"] = v.get("duration", 0)
            result["formats_count"] = 1
        if images:
            result["images"] = images
            result["images_count"] = len(images)
            result["note_id"] = note_id  # for downloading

        return _safe_json(result)
    except Exception as e:
        return _safe_json({"success": False, "error": f"分析异常: {str(e)[:100]}", "is_image": True})


def _xhs_image_urls(detail):
    """
    从笔记详情提取图片 URL 列表，兼容新旧两种字段命名:
      新版 camelCase: imageList / urlDefault / infoList[].url
      旧版 snake_case: image_list / url_default / info_list[].url_default
    质量优先级: urlDefault(WB_DFT 档) > infoList 非预览场景 > 预览图
    """
    images = []
    img_list = detail.get("imageList") or detail.get("image_list") or []
    for img in img_list:
        if not isinstance(img, dict):
            continue
        u = img.get("urlDefault") or img.get("url_default") or ""
        if not u:
            infos = img.get("infoList") or img.get("info_list") or []
            # 优先非预览(WB_DFT等)，预览(WB_PRV)垫底
            ordered = sorted(infos, key=lambda it: ("PRV" in str(it.get("imageScene", "")), ))
            for it in ordered:
                if isinstance(it, dict):
                    cand = it.get("url") or it.get("urlDefault") or it.get("url_default") or ""
                    if cand:
                        u = cand
                        break
        u = u or img.get("url") or ""
        if u.startswith("//"):
            u = "https:" + u
        if u.startswith("http"):
            if u not in images:
                images.append(u)
    return images


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
        "ixigua": ["ixigua.com", "v.douyin.com"],
        "youtube": ["youtube.com", "youtu.be"],
        "douyin": ["douyin.com", "iesdouyin.com", "tiktok.com"],
        "kuaishou": ["kuaishou.com"],
        "xiaohongshu": ["xiaohongshu.com", "xhslink.com", "xhslink.cn"],
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
