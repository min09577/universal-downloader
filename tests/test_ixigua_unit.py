# -*- coding: utf-8 -*-
"""西瓜极简管线纯函数单测（合成数据，不联网）。随实现一起提交。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "standalone-android" / "app" / "src" / "main" / "python"))
import downloader  # noqa: E402


def test_normalize_url():
    assert downloader.normalize_url(
        "https://www.ixigua.com/7295466269036937786?wid=1"
    ) == "https://www.ixigua.com/7295466269036937786"
    short = "https://v.ixigua.com/ieABCD12/"
    assert downloader.normalize_url(short) == short  # 短链透传
    print("normalize_url OK")


def test_detect_platform():
    assert json.loads(downloader.detect_platform("https://www.ixigua.com/123"))["platform"] == "ixigua"
    assert json.loads(downloader.detect_platform("https://v.ixigua.com/ieABCD/"))["platform"] == "ixigua"
    print("detect_platform OK")


if __name__ == "__main__":
    test_normalize_url()
    test_detect_platform()
    print("=== 全部纯函数单测通过 ===")
