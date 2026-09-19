"""错误分析：对评测错题分类并生成分析报告。

错误类别（启发式）：
- Retrieval Error     正确证据未进入 Top-K（文本）
- Table Matching Error 指标/期间/Sheet 定位错误（表格）
- Generation Error    已找到正确证据但生成答案错误
- Refusal Error       应拒答却给出答案（幻觉风险）
- Insufficient Evidence 数据本身缺少依据
- Routing Error       文本/表格路由错误
- Evaluation Error    答案实际正确但评分规则误判
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ..utils.config import Paths
from .metrics import normalize_text, _is_no_answer


def _gold_parts(gold: str) -> list[str]:
    g = normalize_text(gold)
    parts = [x for x in re.split(r"[和、,;；/及与]", g) if x]
    return parts or [g]


def classify(detail: dict[str, Any]) -> str:
    """对一道错题分类，返回错误类型字符串（正确题返回空串）。"""
    if detail.get("correct"):
        return ""

    gold = detail["gold_answer"]
    pred = detail["predicted_answer"]
    qtype = detail.get("question_type", "text")

    gold_no = _is_no_answer(gold)
    pred_no = detail.get("status") == "no_evidence" or _is_no_answer(pred)

    # 应拒答却回答
    if gold_no and not pred_no:
        return "Refusal Error"

    # 检查 gold 是否出现在证据中
    ev_text = normalize_text(" ".join(str(e.get("text", "")) for e in detail.get("evidence", [])))
    gold_in_evidence = any(p in ev_text for p in _gold_parts(gold))

    if pred_no and not gold_no:
        # 该答却拒答：数据缺失 or 检索/匹配失败
        if qtype == "table":
            return "Table Matching Error"
        return "Retrieval Error"

    if gold_in_evidence:
        return "Generation Error"

    if qtype == "table":
        return "Table Matching Error"
    return "Retrieval Error"


def analyze(summary: dict[str, Any]) -> dict[str, Any]:
    """基于评测汇总进行错误分析。"""
    details = summary.get("details", [])
    wrong = [d for d in details if not d["correct"]]
    counts = Counter()
    for d in wrong:
        etype = classify(d)
        counts[etype] += 1

    top = counts.most_common(2)
    report = {
        "total_wrong": len(wrong),
        "error_counts": dict(counts),
        "top_errors": [
            {"type": t, "count": c, "examples": _examples(wrong, t)}
            for t, c in top
        ],
    }
    return report


def _examples(wrong: list[dict[str, Any]], etype: str, limit: int = 3) -> list[dict[str, str]]:
    out = []
    for d in wrong:
        if classify(d) == etype:
            out.append({
                "question": d["question"],
                "gold": d["gold_answer"],
                "predicted": d["predicted_answer"],
            })
        if len(out) >= limit:
            break
    return out


def write_report(summary: dict[str, Any], analysis: dict[str, Any]) -> Path:
    """生成 reports/error_analysis.md 并返回路径。"""
    Paths.ensure_dirs()
    lines: list[str] = []
    lines.append("# 错误分析报告\n")
    lines.append(f"- 总题数：{summary.get('total', 0)}")
    lines.append(f"- 正确：{summary.get('correct', 0)}")
    lines.append(f"- 错误：{summary.get('incorrect', 0)}")
    lines.append(f"- 总体正确率：{summary.get('accuracy', 0):.2%}\n")

    lines.append("## 错误类型分布\n")
    for etype, cnt in sorted(analysis.get("error_counts", {}).items(), key=lambda x: -x[1]):
        lines.append(f"- {etype}: {cnt}")

    lines.append("\n## 主要错误类型分析\n")
    for item in analysis.get("top_errors", []):
        lines.append(f"\n### {item['type']}（{item['count']} 例）\n")
        for ex in item["examples"]:
            lines.append(f"- 问题：{ex['question']}")
            lines.append(f"  - 标准答案：{ex['gold']}")
            lines.append(f"  - 系统答案：{ex['predicted']}")

    lines.append("\n## 下一步优化方向\n")
    top_types = [item["type"] for item in analysis.get("top_errors", [])]
    if "Retrieval Error" in top_types:
        lines.append("- 优化 Chunk 策略、BM25 参数与条款号/数字增强，提升正确证据进入 Top-K 的概率。")
    if "Table Matching Error" in top_types:
        lines.append("- 优化表头归一化、指标名匹配与期间/机构识别规则。")
    if "Generation Error" in top_types:
        lines.append("- 优化抽取式回答的选择逻辑，或引入 LLM 进行受证据约束的答案生成。")
    if "Refusal Error" in top_types:
        lines.append("- 收紧拒答阈值，降低无证据时的误答风险。")
    if "Insufficient Evidence" in top_types:
        lines.append("- 检查数据源是否缺失相应制度/报表内容。")

    path = Paths.REPORTS_DIR / "error_analysis.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
