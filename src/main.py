"""可信 RAG 问答系统 — CLI 入口。

用法：
    python -m src.main index                     # 建立索引
    python -m src.main index --force             # 强制重建索引
    python -m src.main ask "问题"                # 回答问题
    python -m src.main evaluate                  # 运行测试集
    python -m src.main demo                      # 运行端到端示例
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .indexer import Indexer
from .qa.pipeline import Pipeline
from .parsers.schemas import AnswerResult
from .utils.config import Paths
from .utils.logging import configure, get_logger

log = get_logger("main")


def build_pipeline(force: bool = False) -> tuple[Pipeline, Indexer.IndexStats]:
    """构建索引并返回问答流水线。"""
    indexer = Indexer()
    retriever, table_engine, stats = indexer.build(force=force)
    pipeline = Pipeline(retriever, table_engine)
    return pipeline, stats


def format_result(res: AnswerResult) -> str:
    """按证据可追溯格式打印答案。"""
    lines = [f"Answer: {res.answer}", f"Type: {res.question_type} | Confidence: {res.confidence:.3f} | Status: {res.status}"]
    for i, ev in enumerate(res.evidence, start=1):
        lines.append(f"\nEvidence {i}:")
        if isinstance(ev, dict):
            if "indicator" in ev:  # 表格证据
                lines.append(f"  指标：{ev.get('indicator','')}")
                lines.append(f"  期间：{ev.get('period','')}")
                lines.append(f"  值：{ev.get('value','')}")
                lines.append(f"  单位：{ev.get('unit','')}")
            else:
                lines.append(f"  {ev.get('text','')}")
    for i, src in enumerate(res.sources, start=1):
        if not src:
            continue
        lines.append(f"\nSource {i}:")
        if "cell" in src:  # 表格来源
            lines.append(f"  {src.get('source_file','')} | Sheet: {src.get('sheet','')} | Cell: {src.get('cell','')}")
        else:
            parts = [f"  {src.get('source_file','')}"]
            if src.get("page") is not None:
                parts.append(f"Page: {src.get('page')}")
            if src.get("article"):
                parts.append(f"Article: {src.get('article')}")
            if src.get("section"):
                parts.append(f"Section: {src.get('section')}")
            lines.append(" | ".join(parts))
    return "\n".join(lines)


def cmd_index(args: argparse.Namespace) -> int:
    indexer = Indexer()
    retriever, table_engine, stats = indexer.build(force=args.force)
    print(f"索引构建完成：")
    print(f"  文档：{stats.documents} 个")
    print(f"  文本 Chunk：{stats.chunks} 个")
    print(f"  表格：{stats.tables} 个")
    print(f"  表格记录：{stats.table_records} 条")
    if stats.warnings:
        print(f"  告警 {len(stats.warnings)} 条：")
        for w in stats.warnings:
            print(f"    - {w}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    pipeline, _ = build_pipeline()
    res = pipeline.answer(args.question)
    print(format_result(res))
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    from .evaluation.evaluator import Evaluator
    from .evaluation.error_analysis import analyze, write_report

    pipeline, _ = build_pipeline()
    evaluator = Evaluator(pipeline)

    dataset_path = args.dataset
    if dataset_path is None:
        # 自动寻找测试集
        candidates = list(Paths.QUESTIONS_DIR.glob("*.json")) + list(Paths.QUESTIONS_DIR.glob("*.csv")) + list(Paths.QUESTIONS_DIR.glob("*.xlsx"))
        if not candidates:
            print("未找到测试集。请用 --dataset 指定，或将测试集放入 data/questions/。")
            return 1
        dataset_path = candidates[0]

    summary = evaluator.run(dataset_path)
    print(f"评测完成（{dataset_path}）：")
    print(f"  total={summary.get('total')} correct={summary.get('correct')} incorrect={summary.get('incorrect')}")
    print(f"  accuracy={summary.get('accuracy', 0):.2%}")
    for key in sorted(summary.keys()):
        if key.endswith("_accuracy"):
            print(f"  {key}={summary[key]:.2%}")

    if not args.no_analysis and summary.get("total"):
        analysis = analyze(summary)
        path = write_report(summary, analysis)
        print(f"\n错误分析已生成：{path}")

    # 打印错题（简洁）
    wrong = [d for d in summary.get("details", []) if not d["correct"]]
    if wrong:
        print(f"\n错题（{len(wrong)}）：")
        for d in wrong:
            print(f"  Q: {d['question']}")
            print(f"    gold={d['gold_answer']}  pred={d['predicted_answer']}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    pipeline, _ = build_pipeline()
    demo_questions = [
        ("text", "商业银行资本充足率不得低于多少？"),
        ("text", "银行业金融机构发生重大事项后，应当在多少日内报告？"),
        ("table", "2024年一季度商业银行营业收入是多少亿元？"),
        ("table", "B机构2024年末营业收入比A机构高多少亿元？"),
        ("no_evidence", "某机构发生数据泄露后应当在多少日内报告金融监管总局？"),
    ]
    lines = ["# 端到端演示案例\n"]
    for label, q in demo_questions:
        res = pipeline.answer(q)
        lines.append(f"## {label}：{q}\n")
        lines.append("```")
        lines.append(format_result(res))
        lines.append("```\n")
    path = Paths.REPORTS_DIR / "demo_cases.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"演示案例已保存：{path}")
    for label, q in demo_questions:
        res = pipeline.answer(q)
        print(f"\n[{label}] {q}\n{format_result(res)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="src.main", description="可信 RAG 问答系统")
    sub = p.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="建立索引")
    p_index.add_argument("--force", action="store_true", help="强制重建")
    p_index.set_defaults(func=cmd_index)

    p_ask = sub.add_parser("ask", help="回答问题")
    p_ask.add_argument("question", help="问题文本")
    p_ask.set_defaults(func=cmd_ask)

    p_eval = sub.add_parser("evaluate", help="运行测试集")
    p_eval.add_argument("--dataset", default=None, help="测试集路径")
    p_eval.add_argument("--no-analysis", action="store_true", help="跳过错误分析")
    p_eval.set_defaults(func=cmd_evaluate)

    p_demo = sub.add_parser("demo", help="运行端到端示例")
    p_demo.set_defaults(func=cmd_demo)

    return p


def main(argv: list[str] | None = None) -> int:
    configure()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # noqa: BLE001
        log.exception("命令执行失败")
        print(f"错误：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
