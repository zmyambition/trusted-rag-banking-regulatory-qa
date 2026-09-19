"""Chunk 切分与元数据测试。"""
from __future__ import annotations


def test_chunk_has_required_fields(chunks):
    for c in chunks:
        assert c.source_file
        assert c.text


def test_chunk_article_metadata(chunks):
    # 存在携带条款号的 chunk
    articles = [c.article for c in chunks if c.article]
    assert "第三条" in articles
    assert any(a is not None for a in articles)


def test_chunk_keeps_article_content_together(chunks):
    # "第三条 ... 不得低于5%" 应在一个 chunk 内
    c = next(c for c in chunks if "核心一级资本充足率不得低于5%" in c.text)
    assert "第三条" in c.text


def test_chunk_source_file(chunks):
    names = {c.source_file for c in chunks}
    assert any("资本管理办法" in n for n in names)
