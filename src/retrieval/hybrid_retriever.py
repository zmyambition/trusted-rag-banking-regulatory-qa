"""混合检索：BM25 + 向量，使用 Reciprocal Rank Fusion (RRF) 融合。

当向量检索不可用时，自动退化为纯 BM25，保证系统始终可用。
"""
from __future__ import annotations

from typing import Any

from ..parsers.schemas import TextChunk
from ..utils.config import RetrievalConfig
from .bm25_retriever import BM25Retriever
from .vector_retriever import VectorRetriever, is_available


def _rrf_fuse(
    bm25_results: list[dict[str, Any]],
    vec_results: list[dict[str, Any]],
    k: int = RetrievalConfig.RRF_K,
) -> dict[int, float]:
    """按 chunk 索引做 RRF 融合，返回 {chunk_index: rrf_score}。"""
    fused: dict[int, float] = {}
    for rank, r in enumerate(bm25_results):
        idx = id(r["chunk"])
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    for rank, r in enumerate(vec_results):
        idx = id(r["chunk"])
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return fused


class HybridRetriever:
    def __init__(self, chunks: list[TextChunk], use_vector: bool | None = None):
        self.chunks = chunks
        self._index_by_id = {id(c): c for c in chunks}
        self.bm25 = BM25Retriever(chunks)
        self.use_vector = is_available() if use_vector is None else use_vector
        self.vector = VectorRetriever(chunks) if self.use_vector else None
        if self.use_vector and (self.vector is None or not self.vector.enabled()):
            self.use_vector = False

    def retrieve(self, query: str, top_k: int = RetrievalConfig.TOP_K) -> list[dict[str, Any]]:
        bm25_results = self.bm25.retrieve(query, top_k=RetrievalConfig.CANDIDATE_K)
        if not self.use_vector:
            return bm25_results[:top_k]

        vec_results = self.vector.retrieve(query, top_k=RetrievalConfig.CANDIDATE_K)
        if not vec_results:
            return bm25_results[:top_k]

        fused = _rrf_fuse(bm25_results, vec_results)
        # 融合分数对应的 chunk，附带 BM25 分数作为 score
        order = sorted(fused, key=lambda i: fused[i], reverse=True)[:top_k]
        results = []
        for idx in order:
            chunk = self._index_by_id[idx]
            # score 取融合分数（用于排序），另存 bm25_score 便于置信度
            results.append({
                "text": chunk.text,
                "score": fused[idx],
                "source": self._source_of(chunk),
                "chunk": chunk,
            })
        return results

    @staticmethod
    def _source_of(chunk: TextChunk) -> dict[str, Any]:
        from ..knowledge.metadata import text_source_summary
        return text_source_summary(chunk)
