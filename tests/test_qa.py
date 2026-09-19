"""问答流水线、证据与拒答测试。"""
from __future__ import annotations


def test_text_qa_evidence(pipeline):
    res = pipeline.answer("商业银行资本充足率不得低于多少？")
    assert res.status == "answered"
    assert "8%" in res.answer
    assert res.evidence, "应返回证据"
    assert res.sources, "应返回来源"
    assert res.sources[0]["article"] == "第五条"


def test_table_qa_pipeline(pipeline):
    res = pipeline.answer("2024年一季度商业银行营业收入是多少亿元？")
    assert res.status == "answered"
    assert res.answer == "135.2亿元"


def test_no_evidence_text(pipeline):
    res = pipeline.answer("某机构发生数据泄露后应当在多少日内报告金融监管总局？")
    assert res.status == "no_evidence"
    assert res.answer == "未找到足够证据"


def test_no_evidence_table(pipeline):
    res = pipeline.answer("2020年一季度商业银行营业收入是多少亿元？")
    assert res.status == "no_evidence"


def test_router_types(pipeline):
    from src.qa.router import route
    assert route("商业银行资本充足率不得低于多少？")[0] == "text"
    assert route("2024年一季度商业银行营业收入是多少亿元？")[0] == "table"
