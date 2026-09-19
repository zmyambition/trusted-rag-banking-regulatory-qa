"""问题路由（Query Router）：把问题划分为 text / table / mixed / unknown。

优先使用轻量规则：
- 出现年份/季度/报表指标等 → 提高 TABLE 概率；
- 出现"规定/条款/应当/不得/期限/日内"等 → 提高 TEXT 概率。

不使用绝对规则；不确定时返回 mixed / unknown，由上层同时运行两条路径。
"""
from __future__ import annotations

import re

# 强烈暗示"表格取数"的词汇（具体指标名 / 统计口径，不含裸单位，避免与阈值题混淆）
_TABLE_STRONG = [
    "营业收入", "净利润", "总资产", "总负债", "不良贷款率", "贷款余额",
    "同比", "环比", "报表", "余额", "总额", "占比", "增长率",
    "指标", "数据", "月末", "季末", "季度",
]

# 强烈暗示"制度文本"的词汇
_TEXT_STRONG = [
    "规定", "条款", "办法", "制度", "应当", "不得", "必须", "可以",
    "期限", "条件", "报告", "备案", "批准", "风险权重", "杠杆率",
    "最低", "最高", "不得低于", "不得高于", "不得超过", "不得少于",
    "日内", "年内", "月内", "多少日", "多长时间", "依据", "根据",
    "充足率", "第", "条",
]

_YEAR = re.compile(r"(19|20)\d{2}\s*年")
_QUARTER = re.compile(r"第?[一二三四1-4]\s*季度")


def _has_period(q: str) -> bool:
    return bool(_YEAR.search(q) or _QUARTER.search(q) or "年末" in q or "月末" in q)


def route(question: str) -> tuple[str, dict]:
    """返回 (类型, 得分说明)。类型为 text/table/mixed/unknown 之一。"""
    table_score = 0.0
    text_score = 0.0
    reasons: list[str] = []

    if _has_period(question):
        table_score += 3.0
        reasons.append("含期间(年/季度)")

    for t in _TABLE_STRONG:
        if t in question:
            table_score += 1.5
    for t in _TEXT_STRONG:
        if t in question:
            text_score += 1.5

    if table_score >= 2 and text_score >= 2:
        qtype = "mixed"
    elif table_score - text_score >= 2:
        qtype = "table"
    elif text_score - table_score >= 2:
        qtype = "text"
    elif table_score > 0:
        qtype = "table"
    elif text_score > 0:
        qtype = "text"
    else:
        qtype = "unknown"

    return qtype, {
        "table_score": round(table_score, 1),
        "text_score": round(text_score, 1),
        "reasons": reasons,
    }
