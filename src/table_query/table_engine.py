"""表格查询引擎：把自然语言问题转换为对 Excel 结构化数据的取数。

流程：

    问题 → 解析意图(指标/期间/机构) → 候选匹配 → 定位 Cell → 返回数值 + 证据

支持单点取数与简单的"比较/差值"计算题（扩展）。
"""
from __future__ import annotations

import re
from typing import Any, Optional

from ..parsers.schemas import TableRecord
from ..knowledge.metadata import table_source_summary
from ..utils.logging import get_logger
from . import table_matcher as tm
from .table_index import TableIndex, ScoredRecord, filter_candidates

log = get_logger("table_engine")

_COMPARE_PAT = re.compile(r"比|较|高多少|多多少|低多少|少多少|增长|下降")


def format_value(value: Any, unit: str = "") -> str:
    """把数值格式化为可读字符串，附加单位。"""
    if isinstance(value, float) and value.is_integer():
        v = str(int(value))
    else:
        v = str(value)
    return v + (unit if unit else "")


def _numeric(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


class TableEngine:
    def __init__(self, records: list[TableRecord]):
        self.records = records
        self.index = TableIndex(records)

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def answer(self, question: str) -> dict[str, Any]:
        """回答一个表格问题，返回结构化结果（不含 question 字段，由调用方补充）。"""
        candidates = self.index.search(question, top_k=20)
        candidates = filter_candidates(candidates)

        # 指定了期间时，要求期间完全命中，否则视为数据中无该期间 → 拒答
        period = tm.extract_period(question)
        if period:
            candidates = [c for c in candidates if c.period_score >= 100.0]

        if not candidates:
            return self._no_evidence(question)

        if self._is_comparison(question):
            result = self._comparison_answer(question)
            if result is not None:
                return result
            # 比较解析失败则退回单点取数

        best = candidates[0]
        return self._single_cell_answer(question, best)

    # ------------------------------------------------------------------
    # 单点取数
    # ------------------------------------------------------------------
    def _single_cell_answer(self, question: str, scored: ScoredRecord) -> dict[str, Any]:
        rec = scored.record
        value = format_value(rec.value, rec.unit)
        confidence = self._confidence(scored)
        evidence = [{
            "indicator": " / ".join(rec.row_labels),
            "period": " / ".join(rec.column_labels),
            "value": rec.value,
            "unit": rec.unit,
        }]
        sources = [table_source_summary(rec)]
        return {
            "answer": value,
            "question_type": "table",
            "confidence": confidence,
            "evidence": evidence,
            "sources": sources,
            "status": "answered",
        }

    # ------------------------------------------------------------------
    # 比较 / 差值计算（扩展）
    # ------------------------------------------------------------------
    def _is_comparison(self, question: str) -> bool:
        return bool(_COMPARE_PAT.search(question))

    def _comparison_answer(self, question: str) -> Optional[dict[str, Any]]:
        """解析 "X比Y高/低多少" 类问题，返回差值答案。失败返回 None。"""
        indicator_label = self._extract_indicator_label(question)
        period = tm.extract_period(question)
        orgs = re.findall(r"[A-Za-z]{1,3}\s*机构|[一-鿿]{2,12}(?:银行|机构|公司)", question)
        orgs = [o.replace(" ", "") for o in orgs]
        if len(orgs) < 2:
            return None
        subj, ref = orgs[0], orgs[1]
        rec_a = self._lookup_cell(indicator_label, subj, period)
        rec_b = self._lookup_cell(indicator_label, ref, period)
        if rec_a is None or rec_b is None:
            return None
        va, vb = _numeric(rec_a.value), _numeric(rec_b.value)
        if va is None or vb is None:
            return None
        # 判断方向："低/少/下降" 取反向
        reverse = bool(re.search(r"低|少|下降", question))
        diff = (vb - va) if reverse else (va - vb)
        unit = rec_a.unit or rec_b.unit
        answer = format_value(abs(diff), unit)
        evidence = [
            {"indicator": " / ".join(rec_a.row_labels), "org": subj,
             "period": " / ".join(rec_a.column_labels), "value": rec_a.value, "unit": rec_a.unit},
            {"indicator": " / ".join(rec_b.row_labels), "org": ref,
             "period": " / ".join(rec_b.column_labels), "value": rec_b.value, "unit": rec_b.unit},
        ]
        sources = [table_source_summary(rec_a), table_source_summary(rec_b)]
        return {
            "answer": answer,
            "question_type": "table",
            "confidence": 0.9,
            "evidence": evidence,
            "sources": sources,
            "status": "answered",
        }

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    def _extract_indicator_label(self, question: str) -> str:
        """从问题中找出最可能对应的指标名（取自行标签，便于精确 lookup）。

        跳过机构类标签；同分时优先更长（更具体）的指标名。
        """
        candidates: list[tuple[float, int, str]] = []
        seen: set[str] = set()
        for rec in self.records:
            for lab in rec.row_labels:
                if lab in seen:
                    continue
                seen.add(lab)
                if tm.is_org_label(lab):
                    continue
                s = tm.indicator_match_score(question, lab)
                candidates.append((s, len(lab), lab))
        if not candidates:
            return ""
        return max(candidates, key=lambda x: (x[0], x[1]))[2]

    def _lookup_cell(self, indicator_label: str, org: str, period: dict[str, Any]) -> Optional[TableRecord]:
        """精确查找 (指标, 机构, 期间) 对应的单元格记录。"""
        for rec in self.records:
            row_text = tm.normalize(" ".join(rec.row_labels))
            ind_ok = tm.normalize(indicator_label) in row_text
            org_ok = (not org) or tm.normalize(org) in row_text
            period_ok = TableIndex._period_score(rec, period) >= 100.0
            if ind_ok and org_ok and period_ok:
                return rec
        return None

    @staticmethod
    def _confidence(scored: ScoredRecord) -> float:
        return round(
            scored.indicator_score / 100 * 0.5
            + scored.period_score / 100 * 0.35
            + scored.org_score / 100 * 0.15,
            3,
        )

    @staticmethod
    def _no_evidence(question: str) -> dict[str, Any]:
        return {
            "answer": "未找到足够证据",
            "question_type": "table",
            "confidence": 0.0,
            "evidence": [],
            "sources": [],
            "status": "no_evidence",
        }
