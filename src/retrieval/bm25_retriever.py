"""BM25 文本检索器（最低要求实现）。

- 使用 jieba 中文分词 + rank-bm25；
- 额外把"条款号"（第X条）与"数字/百分号"作为独立 token，提升精确关键词检索；
- 对条款号、数字做规则增强（见 :meth:`_rule_boost`）。

统一检索接口：

    retrieve(query, top_k=5) -> [{"text", "score", "source"}]
"""
from __future__ import annotations

import re
from typing import Any

import jieba
from rank_bm25 import BM25Okapi

from ..parsers.schemas import TextChunk
from ..knowledge.metadata import text_source_summary
from ..utils.config import RetrievalConfig

# 条款号 / 数字模式
_ARTICLE_PAT = re.compile(r"第[零〇一二三四五六七八九十百千万两]+条")
_NUM_PAT = re.compile(r"\d+(?:\.\d+)?%?")

_jieba_initialized = False


def tokenize(text: str) -> list[str]:
    """中文分词 + 条款号/数字 token 增强。"""
    global _jieba_initialized
    if not _jieba_initialized:
        jieba.initialize()
        _jieba_initialized = True
    tokens = [t.strip() for t in jieba.lcut(text) if t.strip()]
    # 保留条款号与数字作为整 token，便于精确匹配
    tokens += _ARTICLE_PAT.findall(text)
    tokens += _NUM_PAT.findall(text)
    return tokens


class BM25Retriever:
    def __init__(self, chunks: list[TextChunk]):
        self.chunks = chunks
        self._corpus = [c.text for c in chunks]
        self._tokenized = [tokenize(t) for t in self._corpus] if chunks else []
        self._bm25 = BM25Okapi(
            self._tokenized,
            k1=RetrievalConfig.BM25_K1,
            b=RetrievalConfig.BM25_B,
        ) if self._tokenized else None

    def __len__(self) -> int:
        return len(self.chunks)

    def _rule_boost(self, query: str, scores: list[float]) -> list[float]:
        """数字/条款号规则增强，避免只依赖语义相似度。"""
        boosted = list(scores)
        query_articles = set(_ARTICLE_PAT.findall(query))
        query_nums = set(_NUM_PAT.findall(query))
        if not query_articles and not query_nums:
            return boosted
        for i, chunk in enumerate(self.chunks):
            bonus = 0.0
            if query_articles:
                if chunk.article and chunk.article in query_articles:
                    bonus += 3.0
                if any(a in chunk.text for a in query_articles):
                    bonus += 2.0
            if query_nums:
                if any(n in chunk.text for n in query_nums):
                    bonus += 1.5
            if bonus:
                boosted[i] += bonus
        return boosted

    def retrieve(self, query: str, top_k: int = RetrievalConfig.TOP_K) -> list[dict[str, Any]]:
        """返回 Top-K 相关文本块及来源。"""
        if not self._bm25 or not self._tokenized:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        scores = self._rule_boost(query, list(scores))
        # 取 top_k
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        results = []
        for i in order:
            if scores[i] <= 0:
                continue
            chunk = self.chunks[i]
            results.append({
                "text": chunk.text,
                "score": float(scores[i]),
                "source": text_source_summary(chunk),
                "chunk": chunk,
            })
        return results
