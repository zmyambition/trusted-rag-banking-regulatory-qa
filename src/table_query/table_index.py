"""表格索引：基于 TableRecord 的结构化查询。

对每个候选记录计算"指标 / 期间 / 机构"三类匹配分数，
并支持过滤 + 排序，返回 Top-K 候选（用于取数与拒答判定）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..parsers.schemas import TableRecord
from ..utils.config import TableConfig
from . import table_matcher as tm


@dataclass
class ScoredRecord:
    record: TableRecord
    indicator_score: float
    period_score: float
    org_score: float
    total: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "indicator_score": self.indicator_score,
            "period_score": self.period_score,
            "org_score": self.org_score,
            "total": self.total,
        }


class TableIndex:
    def __init__(self, records: list[TableRecord]):
        self.records = records

    def __len__(self) -> int:
        return len(self.records)

    def search(self, query: str, top_k: int = 5) -> list[ScoredRecord]:
        """检索：返回 Top-K 候选记录。"""
        intent_period = tm.extract_period(query)
        intent_org = self._validate_org(tm.extract_org(query))

        scored: list[ScoredRecord] = []
        for rec in self.records:
            ind_score, _ = tm.best_row_label_match(query, rec.row_labels)
            period_score = self._period_score(rec, intent_period)
            org_score = self._org_score(rec, intent_org)

            # 总分为加权和：指标 0.5 + 期间 0.35 + 机构 0.15
            total = ind_score * 0.5 + period_score * 0.35 + org_score * 0.15
            scored.append(ScoredRecord(rec, ind_score, period_score, org_score, total))

        scored.sort(key=lambda s: s.total, reverse=True)
        return scored[:top_k]

    def _validate_org(self, org: str | None) -> str | None:
        """数据验证：抽取到的机构若未出现在任何记录的标签中，视为通用词并丢弃。

        例如"商业银行"是类别而非具体机构，不应作为机构过滤条件。
        """
        if not org:
            return None
        org_n = tm.normalize(org)
        for rec in self.records:
            row_text = tm.normalize(" ".join(rec.row_labels))
            if org_n in row_text:
                return org
        return None

    @staticmethod
    def _period_score(rec: TableRecord, period: dict[str, Any]) -> float:
        """期间匹配：0~100。未指定期间时给中性分 100。"""
        if not period:
            return 100.0
        col_text = tm.normalize(" ".join(rec.column_labels))
        components = []
        if period.get("year"):
            components.append(period["year"])
        if period.get("quarter"):
            components.append(period["quarter"])
        if period.get("month"):
            components.append(period["month"])
        if period.get("end"):
            components.append("年末")
        if not components:
            return 100.0
        hit = sum(1 for c in components if c in col_text)
        # 未命中任何期间组件时，额外惩罚：仍给少量分，便于排序而非直接剔除
        return hit / len(components) * 100.0

    @staticmethod
    def _org_score(rec: TableRecord, org: str | None) -> float:
        """机构匹配：命中 100，未指定 100，指定但未命中 0。"""
        if not org:
            return 100.0
        row_text = tm.normalize(" ".join(rec.row_labels))
        return 100.0 if tm.normalize(org) in row_text else 0.0


def filter_candidates(
    scored: list[ScoredRecord],
    min_indicator: float = TableConfig.MATCH_SCORE_MIN,
) -> list[ScoredRecord]:
    """过滤：指标分数过低或期间/机构完全未命中的候选剔除。"""
    out = []
    for s in scored:
        if s.indicator_score < min_indicator:
            continue
        if s.period_score < 100.0 and s.period_score <= 0.0:
            # 指定了期间但完全没命中
            continue
        if s.org_score <= 0.0:
            # 指定了机构但没命中
            continue
        out.append(s)
    return out
