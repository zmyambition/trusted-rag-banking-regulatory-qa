"""评测器：批量运行测试集，统计正确率并输出评测结果。

支持 JSON / CSV / Excel 测试集；字段名集中映射，不在代码多处散落。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..utils.config import Paths
from ..utils.logging import get_logger
from .metrics import is_correct, normalize_text, _is_no_answer

log = get_logger("evaluator")

# 字段名集中映射：外部列名 → 内部规范名
_FIELD_MAP = {
    "question": ["question", "问题", "query", "题目", "question_text"],
    "answer": ["answer", "gold_answer", "答案", "标准答案", "ground_truth", "gold"],
    "type": ["type", "question_type", "qa_type", "题型", "category", "label"],
}


def _pick(row: dict[str, Any], canonical: str) -> Any:
    for name in _FIELD_MAP[canonical]:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


class TestDatasetLoader:
    """测试集加载器：支持 JSON / CSV / Excel，字段名自动识别。"""

    def load(self, path: str | Path) -> list[dict[str, Any]]:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"测试集不存在: {path}")
        suffix = path.suffix.lower()
        if suffix == ".json":
            rows = self._load_json(path)
        elif suffix == ".csv":
            rows = self._load_csv(path)
        elif suffix in (".xlsx", ".xls"):
            rows = self._load_excel(path)
        else:
            raise ValueError(f"不支持的测试集格式: {suffix}")

        dataset = []
        for row in rows:
            q = _pick(row, "question")
            a = _pick(row, "answer")
            if q is None or a is None:
                continue
            t = _pick(row, "type") or self._guess_type(str(q))
            dataset.append({
                "question": str(q),
                "gold_answer": str(a),
                "question_type": str(t).lower() if str(t).lower() in ("text", "table", "mixed") else "text",
                "raw": row,
            })
        return dataset

    @staticmethod
    def _guess_type(question: str) -> str:
        from ..qa.router import route
        t, _ = route(question)
        return t if t in ("text", "table") else "text"

    @staticmethod
    def _load_json(path: Path) -> list[dict[str, Any]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for key in ("questions", "data", "items", "dataset"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                data = [data]
        if not isinstance(data, list):
            data = [data]
        return [r for r in data if isinstance(r, dict)]

    @staticmethod
    def _load_csv(path: Path) -> list[dict[str, Any]]:
        import pandas as pd

        df = pd.read_csv(path)
        return df.to_dict(orient="records")

    @staticmethod
    def _load_excel(path: Path) -> list[dict[str, Any]]:
        import pandas as pd

        df = pd.read_excel(path)
        return df.to_dict(orient="records")


class Evaluator:
    def __init__(self, pipeline: Any):
        self.pipeline = pipeline
        self.loader = TestDatasetLoader()

    def evaluate(self, dataset: list[dict[str, Any]]) -> dict[str, Any]:
        """运行评测，返回汇总结果（含逐题明细）。"""
        details: list[dict[str, Any]] = []
        for item in dataset:
            q = item["question"]
            gold = item["gold_answer"]
            gold_type = item.get("question_type", "text")
            try:
                res = self.pipeline.answer(q)
                pred = res.answer
                qtype = res.question_type or gold_type
                correct = is_correct(gold, pred, qtype)
                details.append({
                    "question": q,
                    "gold_answer": gold,
                    "predicted_answer": pred,
                    "correct": correct,
                    "question_type": qtype,
                    "gold_type": gold_type,
                    "confidence": res.confidence,
                    "status": res.status,
                    "evidence": res.evidence,
                    "source": res.sources,
                })
            except Exception as e:  # noqa: BLE001
                log.warning("评测单题异常 %s: %s", q, e)
                details.append({
                    "question": q,
                    "gold_answer": gold,
                    "predicted_answer": f"[ERROR] {e}",
                    "correct": False,
                    "question_type": gold_type,
                    "gold_type": gold_type,
                    "confidence": 0.0,
                    "status": "error",
                    "evidence": [],
                    "source": [],
                })

        summary = self._summarize(details)
        summary["details"] = details
        return summary

    @staticmethod
    def _summarize(details: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(details)
        correct = sum(1 for d in details if d["correct"])
        incorrect = total - correct
        by_type: dict[str, dict[str, int]] = {}
        for d in details:
            t = d["question_type"]
            by_type.setdefault(t, {"total": 0, "correct": 0})
            by_type[t]["total"] += 1
            by_type[t]["correct"] += 1 if d["correct"] else 0

        summary: dict[str, Any] = {
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": round(correct / total, 4) if total else 0.0,
        }
        for t, v in by_type.items():
            summary[f"{t}_accuracy"] = round(v["correct"] / v["total"], 4) if v["total"] else 0.0
            summary[f"{t}_total"] = v["total"]
        return summary

    # ------------------------------------------------------------------
    def run(self, dataset_path: str | Path) -> dict[str, Any]:
        """加载测试集 → 评测 → 保存输出，返回 summary。"""
        dataset = self.loader.load(dataset_path)
        if not dataset:
            log.warning("测试集为空")
            return {"total": 0, "correct": 0, "incorrect": 0, "accuracy": 0.0, "details": []}

        summary = self.evaluate(dataset)
        self._save_outputs(summary)
        return summary

    @staticmethod
    def _save_outputs(summary: dict[str, Any]) -> None:
        Paths.ensure_dirs()
        details = summary.get("details", [])
        # JSON
        (Paths.OUTPUTS_DIR / "evaluation.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # CSV（逐题明细）
        csv_path = Paths.OUTPUTS_DIR / "evaluation.csv"
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "question", "gold_answer", "predicted_answer", "correct",
                "question_type", "confidence", "status",
            ])
            for d in details:
                writer.writerow([
                    d["question"], d["gold_answer"], d["predicted_answer"],
                    d["correct"], d["question_type"], d["confidence"], d["status"],
                ])
