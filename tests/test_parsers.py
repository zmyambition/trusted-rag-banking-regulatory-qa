"""解析器测试：Word / PDF / Excel。"""
from __future__ import annotations


def test_docx_parser_elements(parsed_docs):
    d = parsed_docs["商业银行资本管理办法.docx"]
    assert len(d.elements) > 0
    texts = [e.text for e in d.elements]
    assert any("资本充足率" in t for t in texts)


def test_docx_article_detection(parsed_docs):
    d = parsed_docs["商业银行资本管理办法.docx"]
    articles = [e.article for e in d.elements if e.article]
    assert "第三条" in articles
    assert "第五条" in articles


def test_docx_section_tracking(parsed_docs):
    d = parsed_docs["商业银行资本管理办法.docx"]
    # 第三条应继承"第二章 资本充足率要求"
    e3 = next(e for e in d.elements if e.article == "第三条")
    assert e3.section == "第二章 资本充足率要求"


def test_pdf_parser_page(parsed_docs):
    d = parsed_docs["个人贷款管理办法.pdf"]
    assert len(d.elements) > 0
    pages = [e.page for e in d.elements if e.page is not None]
    assert pages and all(p >= 1 for p in pages)
    texts = [e.text for e in d.elements]
    assert any("贷款" in t for t in texts)


def test_excel_multilevel_header(table_records):
    # 找到 2024 年一季度营业收入记录
    rec = next(r for r in table_records
               if "营业收入" in r.row_labels and "2024年" in r.column_labels and "一季度" in r.column_labels)
    assert rec.value == 135.2
    assert rec.unit == "亿元"
    assert rec.cell == "E4"


def test_excel_unit_detection(table_records):
    rate = next(r for r in table_records if "不良贷款率" in r.row_labels)
    assert rate.unit == "%"


def test_excel_cell_metadata(table_records):
    rec = next(r for r in table_records if r.cell == "D2")
    assert rec.source_file == "银行业金融机构资产负债统计表.xlsx"
    assert rec.sheet == "机构数据"
    assert "A机构" in rec.row_labels
