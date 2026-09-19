"""Reranker（增强功能）：默认实现一个轻量规则重排。

不依赖外部模型：基于关键词覆盖 + 数字/条款号命中，对候选证据做简单精排。
核心系统不依赖本模块，禁用时直接返回原序。
"""
from __future__ import annotations

import re
from typing import Any

_ARTICLE_PAT = re.compile(r"第[零〇一二三四五六七八九十百千万两]+条")
_NUM_PAT = re.compile(r"\d+(?:\.\d+)?%?")


def rule_rerank(
    query: str,
    results: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """规则重排：对已有结果按"关键词覆盖 + 条款号/数字命中"重算分数。"""
    if not results:
        return results
    q_tokens = set(re.findall(r"[一-鿿]+", query))
    q_articles = set(_ARTICLE_PAT.findall(query))
    q_nums = set(_NUM_PAT.findall(query))

    scored = []
    for r in results:
        text = r.get("text", "")
        bonus = 0.0
        for tok in q_tokens:
            if len(tok) >= 2 and tok in text:
                bonus += 0.5
        for a in q_articles:
            if a in text:
                bonus += 2.0
        for n in q_nums:
            if n in text:
                bonus += 1.0
        scored.append((bonus, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored][:top_k]
