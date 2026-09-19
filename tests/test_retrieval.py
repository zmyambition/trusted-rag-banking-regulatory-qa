"""BM25 检索测试。"""
from __future__ import annotations


def test_bm25_retrieves_relevant_chunk(retriever):
    results = retriever.retrieve("商业银行资本充足率不得低于多少", top_k=3)
    assert results, "应返回检索结果"
    assert "8%" in results[0]["text"]


def test_bm25_article_number_boost(retriever):
    results = retriever.retrieve("杠杆率不得低于多少", top_k=3)
    assert any("杠杆率" in r["text"] for r in results)


def test_bm25_returns_source(retriever):
    results = retriever.retrieve("重大事项后多少日内报告", top_k=3)
    assert results
    assert results[0]["source"]["source_file"]
    assert results[0]["source"]["article"]
