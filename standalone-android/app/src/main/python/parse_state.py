# -*- coding: utf-8 -*-
"""
__INITIAL_STATE__ 解析器（v2，2026-09 适配）

小红书改版后页面内联的 window.__INITIAL_STATE__ 不再是纯 JSON：
  1. 含裸 undefined 字面量
  2. 含 new Map([...]) / new Set([...]) JS 构造（如 AiNoteDetailStore.noteDetailMap）
本模块用括号配平扫描器把 JS 构造还原成 JSON，再交给 json.loads。
Android(Chaquopy) 与 PC 测试台共用。
"""
import json
import re

_BS = chr(92)
_JS_CONSTRUCTOR = re.compile(r"new (Map|Set)" + _BS + "(")
_INITIALIZER = re.compile(r"window" + _BS + r".__INITIAL_STATE__" + _BS + r"s*=" + _BS + r"s*({.+?})" + _BS + r"s*</script>", re.DOTALL)


def _match_balanced(s, start):
    """从 start(指向'(') 起做括号配平扫描，考虑字符串转义。返回闭括号下标。"""
    depth, i, in_str = 1, start + 1, None
    while i < len(s) and depth:
        ch = s[i]
        if in_str:
            if ch == _BS:
                i += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in ('"', "'"):
            in_str = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        i += 1
    return i - 1 if depth == 0 else -1


def strip_js_literals(s):
    """把 new Map([...]) / new Set([...]) 替换为等价 JSON。"""
    out, i = [], 0
    while True:
        mo = _JS_CONSTRUCTOR.search(s, i)
        if not mo:
            out.append(s[i:])
            break
        out.append(s[i:mo.start()])
        close = _match_balanced(s, mo.end() - 1)
        if close < 0:
            out.append(s[mo.start():mo.end()])
            i = mo.end()
            continue
        inner = s[mo.end():close].strip().replace("undefined", "null")
        try:
            data = json.loads(inner) if inner else []
        except Exception:
            data = []
        if mo.group(1) == "Map" and isinstance(data, list):
            out.append(json.dumps({str(k): v for k, v in data}, ensure_ascii=False))
        else:
            out.append(json.dumps(data if isinstance(data, list) else [], ensure_ascii=False))
        i = close + 1
    return "".join(out)


def parse_initial_state(html):
    """从页面 HTML 提取并解析 __INITIAL_STATE__。失败返回 None。"""
    m = _INITIALIZER.search(html)
    if not m:
        return None
    try:
        return json.loads(strip_js_literals(m.group(1).replace("undefined", "null")))
    except Exception:
        return None


def unwrap_note_detail(state, note_id):
    """
    从解析后的 state 提取笔记详情，兼容新旧结构:
      新版: noteDetailMap[id] = {"note": {...}} (camelCase 字段 imageList)
      旧版: noteDetailMap[id] = {...}        (snake_case 字段 image_list)
    返回统一后的 note dict（无则 None）。
    """
    nd = (state or {}).get("note", {})
    if not isinstance(nd, dict):
        return None
    nd = nd.get("noteDetailMap") or {}
    entry = nd.get(note_id) or (next(iter(nd.values()), None) if nd else None)
    if not isinstance(entry, dict):
        return None
    note = entry.get("note") if isinstance(entry.get("note"), dict) else entry
    # 统一字段: imageList -> image_list 镜像
    if "image_list" not in note and "imageList" in note:
        note["image_list"] = note["imageList"]
    return note or None
