"""表格查询的文本匹配与意图解析。

提供：
- :func:`normalize` 文本归一化（去空格、全半角、括号、百分号等）
- :func:`extract_period` / :func:`extract_org` 从问题中抽取期间与机构
- :func:`indicator_match_score` 指标名模糊匹配（rapidfuzz）

不引入复杂 NLP，优先保证真实测试题准确率。
"""
from __future__ import annotations

import re
from typing import Any, Optional

from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# 文本归一化
# ---------------------------------------------------------------------------
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


def normalize(s: Any) -> str:
    """归一化文本：去空白、全角转半角、统一括号/百分号、小写。"""
    s = str(s)
    s = _full_to_half(s)
    s = s.replace(" ", "").replace("　", "").replace("\xa0", "").replace("\n", "")
    s = s.replace("％", "%").replace("（", "(").replace("）", ")")
    s = s.replace("【", "[").replace("】", "]").replace("．", ".").replace("。", ".")
    s = s.replace("年末", "年末").replace("年底", "年末")
    return s.lower().strip()


# ---------------------------------------------------------------------------
# 期间 / 机构抽取
# ---------------------------------------------------------------------------
_YEAR_MONTH = re.compile(r"(19|20)\d{2}\s*年\s*(\d{1,2})\s*月")
_YEAR = re.compile(r"(19|20)\d{2}\s*年")
_MONTH = re.compile(r"(\d{1,2})\s*月")
_QUARTER = re.compile(r"第?([一二三四1-4])\s*季度")
_END = re.compile(r"年末|年底|年\s*末|季末|期末")
_CN_Q = {"一": "一季度", "二": "二季度", "三": "三季度", "四": "四季度",
         "1": "一季度", "2": "二季度", "3": "三季度", "4": "四季度"}

_ORG = re.compile(r"[A-Za-z]{1,3}\s*机构|[一-鿿]{2,12}(?:银行|机构|公司|分行|支行|信用社)")


def extract_period(query: str) -> dict[str, Any]:
    """从问题中抽取期间信息。返回可能为空的 dict。"""
    p: dict[str, Any] = {}
    m = _YEAR_MONTH.search(query)          # 形如 "2025年6月"
    if m:
        p["year"] = m.group(0)[:4]
        p["month"] = f"{int(m.group(2))}月"
    else:
        m = _YEAR.search(query)            # 形如 "2024年"
        if m:
            p["year"] = m.group(0)[:4]
        m2 = _MONTH.search(query)          # 独立 "6月"
        if m2:
            p["month"] = f"{int(m2.group(1))}月"
    m = _QUARTER.search(query)             # 形如 "一季度"
    if m:
        p["quarter"] = _CN_Q[m.group(1)]
    if _END.search(query):                 # "年末 / 年底 / 期末"
        p["end"] = True
    return p


def extract_org(query: str) -> Optional[str]:
    m = _ORG.search(query)
    if m:
        return m.group(0).replace(" ", "")
    return None


def is_org_label(label: str) -> bool:
    """判断一个行标签是否是"机构名"而非"指标名"（如 A机构 / 某银行）。"""
    m = _ORG.search(label)
    if not m:
        return False
    return normalize(m.group(0)) == normalize(label)


# ---------------------------------------------------------------------------
# 指标匹配
# ---------------------------------------------------------------------------
def indicator_match_score(query: str, label: str) -> float:
    """问题与某个行标签的指标匹配分数（0~100）。

    综合 partial_ratio / token_sort_ratio / WRatio，取最高，兼顾
    "营业收入" vs "营业总收入" 这类不完全一致的情况。
    """
    q = normalize(query)
    l = normalize(label)
    if not l:
        return 0.0
    scores = [
        fuzz.partial_ratio(q, l),
        fuzz.token_sort_ratio(q, l),
        fuzz.WRatio(q, l),
    ]
    return float(max(scores))


def best_row_label_match(query: str, row_labels: list[str]) -> tuple[float, str]:
    """返回查询与行标签的最佳匹配分数及对应标签。

    跳过"机构类"标签（如 A机构），避免机构名污染指标匹配。
    """
    best_score, best_label = 0.0, ""
    for lab in row_labels:
        if is_org_label(lab):
            continue
        s = indicator_match_score(query, lab)
        if s > best_score:
            best_score, best_label = s, lab
    return best_score, best_label
