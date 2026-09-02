#!/usr/bin/env python3
"""
小红书/通用管线 PC 测试台 — 不经 Android 构建直接测 downloader.py

把「改代码 → push → CI 构建 → 装APK → 手测」的分钟级循环
变成「改代码 → 回车」的秒级循环。管线验证通过后同步进仓库即可。

用法:
  python tests/xhs_harness.py probe <url>      # 只分析，打印解析结果
  python tests/xhs_harness.py download <url>   # 走完整下载管线，存到 downloads/
  python tests/xhs_harness.py regress          # 跑 tests/xhs_urls.txt 回归清单

Cookies（强烈建议）:
  浏览器登录 xiaohongshu.com → F12 → Network → 任意请求 → 复制 Cookie 请求头
  原始串粘贴到 tests/cookies_xhs.txt（格式: "a1=xxx; webId=yyy; ..."）
  匿名模式也能跑，但小红书大概率 461/验证页，B站无登录限 1080P。
"""
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DL_PATH = ROOT / "standalone-android" / "app" / "src" / "main" / "python" / "downloader.py"
URLS_FILE = Path(__file__).resolve().parent / "xhs_urls.txt"
COOKIE_FILE = Path(__file__).resolve().parent / "cookies_xhs.txt"
OUT_DIR = ROOT / "downloads"


def load_module():
    """直接加载 Android 端 downloader.py，保证测的就是仓库里的代码"""
    py_dir = str(DL_PATH.parent)
    if py_dir not in sys.path:
        sys.path.insert(0, py_dir)  # 让 downloader 能 import 同目录的 parse_state
    spec = importlib.util.spec_from_file_location("downloader", DL_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    inject_cookies(mod)
    return mod


def inject_cookies(mod):
    raw_lines = [l for l in COOKIE_FILE.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.strip().startswith("#")]
    raw = "\n".join(raw_lines).strip().splitlines()
    if raw and raw[-1].strip():
        header = raw[-1].strip()  # 取最后一行有效内容作为 cookie 串
        mod._get_cookies = lambda domain: (header if "xiaohongshu" in domain else "")
        print(f"[cookies] 已注入 ({len(header)} chars)")
        return
    print("[cookies] 匿名模式 — 小红书无 cookie 大概率失败，见文件头说明")


def short(url, n=46):
    return url if len(url) <= n else url[:n - 3] + "..."


def cmd_probe(url):
    mod = load_module()
    print(f"\n== probe: {short(url)}")
    result = json.loads(mod.analyze_url(url))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("success"):
        n_img = result.get("images_count", 0)
        kind = f"图文 {n_img} 张" if n_img else "视频"
        print(f"\n>>> 判定: {kind} | 标题: {result.get('title', '')[:40]}")
    return result


def cmd_download(url):
    mod = load_module()
    OUT_DIR.mkdir(exist_ok=True)
    print(f"\n== download: {short(url)}")
    result = json.loads(mod.download_video(url))  # XHS 域名内部自动分流 _download_xhs
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("success"):
        print(f"\n>>> 成功: {result.get('filename')} -> {result.get('path')}")
    return result


def cmd_regress():
    if not URLS_FILE.exists():
        URLS_FILE.write_text(
            "# 每行一个链接，# 开头是注释。支持 xhslink.com 短链 / www.xiaohongshu.com/explore/... 长链\n"
            "# 图文帖和视频帖混着放，覆盖你踩过的所有坑\n",
            encoding="utf-8")
        print(f"已生成空清单 {URLS_FILE}，把测试链接贴进去后重跑")
        return []

    urls = [l.strip() for l in URLS_FILE.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]
    if not urls:
        print("清单是空的，先往 xhs_urls.txt 贴链接")
        return []

    mod = load_module()
    rows, n_ok = [], 0
    print(f"\n== 回归: {len(urls)} 条链接")
    print(f"{'#':>3} {'结果':<6} {'类型':<6} {'说明'}")
    print("-" * 78)
    for i, url in enumerate(urls, 1):
        try:
            r = json.loads(mod.analyze_url(url))
        except Exception as e:
            r = {"success": False, "error": f"harness异常: {e}"}
        if r.get("success"):
            n_img = r.get("images_count", 0)
            kind, note = ("图文", f"{n_img}张 | {r.get('title', '')[:36]}") if n_img \
                else ("视频", r.get("title", "")[:40])
            mark, n_ok = "✓", n_ok + 1
        elif r.get("is_image"):
            kind, mark, note = "直链", "△", r.get("error", "")[:44]
        else:
            kind, mark, note = "-", "✗", r.get("error", "")[:44]
        rows.append({"url": url, "success": r.get("success", False), "kind": kind,
                     "note": note, "raw_error": r.get("error", "")})
        print(f"{i:>3} {mark:<6} {kind:<6} {note}")

    rate = n_ok / len(urls) * 100
    print("-" * 78)
    print(f">>> 通过 {n_ok}/{len(urls)} ({rate:.0f}%)  匿名跑失败多属正常，带 cookie 再看")

    (Path(__file__).parent / "regress_last.json").write_text(
        json.dumps({"time": datetime.now().isoformat(timespec="seconds"),
                    "rate": rate, "rows": rows}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f">>> 明细已存 tests/regress_last.json（下次跑完可 diff 对比）")
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("probe", "download", "regress"):
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "regress":
        cmd_regress()
    else:
        if len(sys.argv) < 3:
            print(f"用法: python tests/xhs_harness.py {cmd} <url>")
            sys.exit(1)
        (cmd_probe if cmd == "probe" else cmd_download)(sys.argv[2])
