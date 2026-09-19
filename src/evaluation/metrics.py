"""答案归一化与正确性判定。

不做简单字符串完全相等：
- 文本：归一化后检查 gold 答案的每个部分（按 和/、/；/， 拆分）是否出现在预测中；
- 数字：抽取数值并按单位（亿/万/%）归一后，用相对容差比较。
"""
from __future__ import annotations

import re


def _full_to_half(s: str) -> str:
    out = []
    for ch in s:
        code = ord(ch)
        if code == 0x3000:
            out.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def normalize_text(s: str) -> str:
    """文本归一化：去空白、全半角、统一标点/百分号、小写。"""
    s = _full_to_half(str(s))
    s = re.sub(r"\s+", "", s)
    s = s.replace("％", "%").replace("（", "(").replace("）", ")")
    s = s.replace("，", ",").replace("。", ".").replace("；", ";")
    s = s.replace("：", ":").replace("“", '"').replace("”", '"')
    return s.lower().strip()


_NO_ANSWER = "未找到足够证据"


def _extract_number(s: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", normalize_text(s))
    return float(m.group()) if m else None


def _unit_factor(s: str) -> float:
    """单位换算因子（相对"元"）。"""
    if "万亿" in s:
        return 1e12
    if "亿" in s:
        return 1e8
    if "万" in s:
        return 1e4
    return 1.0


def _is_no_answer(s: str) -> bool:
    return _NO_ANSWER in normalize_text(s) or "未找到" in s or "没有找到" in s


def text_correct(gold: str, predicted: str) -> bool:
    """文本题正确性：gold 各部分均出现在 predicted（归一化后）。"""
    g = normalize_text(gold)
    p = normalize_text(predicted)
    if not g or not p:
        return False
    # 拒答题：两侧都表示"无答案"即正确
    if _is_no_answer(g):
        return _is_no_answer(p)
    # 拆分多值答案（"6%和5%" → ["6%", "5%"]）
    parts = [x for x in re.split(r"[和、,;；/及与]", g) if x]
    if not parts:
        parts = [g]
    return all(part in p for part in parts)


def table_correct(gold: str, predicted: str) -> bool:
    """表格题正确性：数字 + 单位归一后比较。"""
    g, p = normalize_text(gold), normalize_text(predicted)
    if _is_no_answer(g):
        return _is_no_answer(p)
    if _is_no_answer(p):
        return False
    gn, pn = _extract_number(g), _extract_number(p)
    if gn is None or pn is None:
        return text_correct(gold, predicted)
    gv = gn * _unit_factor(g)
    pv = pn * _unit_factor(p)
    return abs(gv - pv) <= 1e-6 * max(1.0, abs(gv))


def is_correct(gold: str, predicted: str, question_type: str = "text") -> bool:
    """按题型选择判定逻辑。"""
    if question_type == "table":
        return table_correct(gold, predicted)
    return text_correct(gold, predicted)
