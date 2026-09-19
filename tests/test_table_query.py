"""表格查询测试。"""
from __future__ import annotations


def test_table_single_cell(table_engine):
    r = table_engine.answer("2024年一季度商业银行营业收入是多少亿元？")
    assert r["status"] == "answered"
    assert r["answer"] == "135.2亿元"
    assert r["sources"][0]["cell"] == "E4"


def test_table_org_indicator_period(table_engine):
    r = table_engine.answer("A机构2024年末营业收入是多少亿元？")
    assert r["answer"] == "300亿元"


def test_table_comparison(table_engine):
    r = table_engine.answer("B机构2024年末营业收入比A机构高多少亿元？")
    assert r["answer"] == "150亿元"
    assert len(r["sources"]) == 2


def test_table_no_evidence_year(table_engine):
    r = table_engine.answer("2020年一季度商业银行营业收入是多少亿元？")
    assert r["status"] == "no_evidence"
    assert r["answer"] == "未找到足够证据"
