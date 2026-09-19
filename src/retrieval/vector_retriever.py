"""向量检索器（可选扩展，Embedding 检索）。

默认不安装 sentence-transformers；本模块在依赖缺失时优雅降级，
通过 :func:`is_available` 报告状态，Hybrid 检索会自动回退到纯 BM25。

不将 Embedding 作为整个系统无法启动的单点故障。
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ..parsers.schemas import TextChunk
from ..knowledge.metadata import text_source_summary
from ..utils.config import RetrievalConfig, get_env
from ..utils.logging import get_logger

log = get_logger("vector_retriever")

_available = False
_sentence_transformers = None
try:
    import sentence_transformers  # type: ignore
    _sentence_transformers = sentence_transformers
    _available = True
except Exception:  # noqa: BLE001
    _available = False


def is_available() -> bool:
    """sentence-transformers 是否可用。"""
    return _available


class VectorRetriever:
    def __init__(self, chunks: list[TextChunk], model_name: str | None = None):
        self.chunks = chunks
        self.model_name = model_name or get_env("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
        self._model = None
        self._embeddings = None
        if _available:
            try:
                self._model = _sentence_transformers.SentenceTransformer(self.model_name)
                self._embeddings = self._model.encode(
                    [c.text for c in chunks], normalize_embeddings=True
                )
            except Exception as e:  # noqa: BLE001
                log.warning("向量模型加载失败，回退 BM25：%s", e)
                self._model = None
                self._embeddings = None

    def enabled(self) -> bool:
        return self._model is not None and self._embeddings is not None

    def retrieve(self, query: str, top_k: int = RetrievalConfig.TOP_K) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        q_emb = self._model.encode([query], normalize_embeddings=True)
        sims = (self._embeddings @ q_emb.T).flatten()
        order = np.argsort(-sims)[:top_k]
        results = []
        for i in order:
            chunk = self.chunks[int(i)]
            results.append({
                "text": chunk.text,
                "score": float(sims[int(i)]),
                "source": text_source_summary(chunk),
                "chunk": chunk,
            })
        return results
