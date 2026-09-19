"""置信度计算与拒答（No Evidence）判定。

文本：结合关键词覆盖率（问题内容词在证据中的命中比例）与候选一致性；
表格：结合指标/期间/机构匹配分数（在 table_engine 中已计算）。
"""
from __future__ import annotations

from typing import Any

from ..utils.config import ConfidenceConfig
from .answer_generator import _content_words


def text_confidence(question: str, evidence: list[dict[str, Any]]) -> tuple[float, str]:
    """基于文本证据计算置信度，返回 (confidence, status)。

    status 为 "answered" 或 "no_evidence"。
    """
    if not evidence:
        return 0.0, "no_evidence"

    top_text = evidence[0].get("text", "")
    q_words = _content_words(question)
    if not q_words:
        return 0.5, "answered"

    covered = [w for w in q_words if w in top_text]
    coverage = len(covered) / len(q_words)

    # 候选一致性：Top1 与 Top2 是否指向同一来源/条款
    consistency = 1.0
    if len(evidence) >= 2:
        s1 = evidence[0].get("source", {})
        s2 = evidence[1].get("source", {})
        if s1.get("article") and s1.get("article") == s2.get("article"):
            consistency = 1.0
        else:
            consistency = 0.5

    confidence = round(coverage * 0.7 + consistency * 0.3, 3)

    if coverage < ConfidenceConfig.TEXT_KEYWORD_COVERAGE:
        return confidence, "no_evidence"
    return confidence, "answered"
