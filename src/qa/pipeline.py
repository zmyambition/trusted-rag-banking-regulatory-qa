"""问答流水线：串联路由 → 检索/取数 → 生成 → 证据 → 输出。

统一输出为 :class:`~src.parsers.schemas.AnswerResult`。
"""
from __future__ import annotations

from typing import Any

from ..parsers.schemas import AnswerResult
from ..utils.config import RetrievalConfig
from ..utils.logging import get_logger
from .answer_generator import LLMProvider, get_provider
from .confidence import text_confidence
from .router import route

log = get_logger("pipeline")


class Pipeline:
    def __init__(
        self,
        retriever: Any,
        table_engine: Any,
        provider: LLMProvider | None = None,
    ):
        self.retriever = retriever
        self.table_engine = table_engine
        self.provider = provider or get_provider()

    def answer(self, question: str) -> AnswerResult:
        qtype, info = route(question)
        log.info("query=%s | route=%s | info=%s", question, qtype, info)

        if qtype == "table":
            return self._table_answer(question)
        if qtype == "text":
            return self._text_answer(question)
        if qtype == "mixed":
            table_res = self.table_engine.answer(question)
            if table_res.get("status") == "answered":
                return self._wrap(table_res, question, "mixed")
            return self._text_answer(question)
        # unknown：两条路径都跑，取更可信的
        table_res = self.table_engine.answer(question)
        text_res = self._text_answer(question)
        if table_res.get("status") == "answered":
            return self._wrap(table_res, question, "unknown")
        return text_res

    # ------------------------------------------------------------------
    def _text_answer(self, question: str) -> AnswerResult:
        evidence = self.retriever.retrieve(question, top_k=RetrievalConfig.TOP_K)
        confidence, status = text_confidence(question, evidence)
        if status == "no_evidence":
            return AnswerResult(
                question=question,
                answer="未找到足够证据",
                question_type="text",
                confidence=confidence,
                evidence=self._evidence_dicts(evidence),
                sources=self._sources(evidence),
                status="no_evidence",
                metadata={"candidates": len(evidence)},
            )
        answer = self.provider.generate(question, evidence, "text") or self._fallback(evidence)
        return AnswerResult(
            question=question,
            answer=answer,
            question_type="text",
            confidence=confidence,
            evidence=self._evidence_dicts(evidence),
            sources=self._sources(evidence),
            status="answered",
            metadata={"provider": self.provider.name, "candidates": len(evidence)},
        )

    def _table_answer(self, question: str) -> AnswerResult:
        r = self.table_engine.answer(question)
        return self._wrap(r, question, "table")

    @staticmethod
    def _wrap(r: dict[str, Any], question: str, qtype: str) -> AnswerResult:
        return AnswerResult(
            question=question,
            answer=r.get("answer", "未找到足够证据"),
            question_type=qtype,
            confidence=r.get("confidence", 0.0),
            evidence=r.get("evidence", []),
            sources=r.get("sources", []),
            status=r.get("status", "no_evidence"),
        )

    @staticmethod
    def _evidence_dicts(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"text": e.get("text", ""), "source": e.get("source", {})} for e in evidence]

    @staticmethod
    def _sources(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [e.get("source", {}) for e in evidence]

    @staticmethod
    def _fallback(evidence: list[dict[str, Any]]) -> str:
        return evidence[0]["text"][:200] if evidence else "未找到足够证据"
