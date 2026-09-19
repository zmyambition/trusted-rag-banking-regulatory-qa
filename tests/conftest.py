"""pytest 公共夹具：确保样例数据存在，并提供解析/索引对象。"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "data" / "documents"
TABLES = ROOT / "data" / "tables"


@pytest.fixture(scope="session")
def sample_data():
    """确保合成样例数据存在（缺失时生成）。"""
    has_docs = list(DOCS.glob("*.docx")) and list(DOCS.glob("*.pdf"))
    has_tables = list(TABLES.glob("*.xlsx"))
    if not (has_docs and has_tables):
        from scripts.generate_sample_data import main as gen_main
        gen_main()
    return ROOT


@pytest.fixture(scope="session")
def parsed_docs(sample_data):
    from src.parsers.docx_parser import parse_docx
    from src.parsers.pdf_parser import parse_pdf

    docs = {}
    for f in DOCS.glob("*.docx"):
        docs[f.name] = parse_docx(f)
    for f in DOCS.glob("*.pdf"):
        docs[f.name] = parse_pdf(f)
    return docs


@pytest.fixture(scope="session")
def chunks(parsed_docs):
    from src.knowledge.chunker import chunk_document

    all_chunks = []
    for parsed in parsed_docs.values():
        all_chunks += chunk_document(parsed)
    return all_chunks


@pytest.fixture(scope="session")
def table_records(sample_data):
    from src.parsers.excel_parser import parse_excel

    records = []
    for f in TABLES.glob("*.xlsx"):
        rs, _ = parse_excel(f)
        records += rs
    return records


@pytest.fixture(scope="session")
def retriever(chunks):
    from src.retrieval.bm25_retriever import BM25Retriever
    return BM25Retriever(chunks)


@pytest.fixture(scope="session")
def table_engine(table_records):
    from src.table_query.table_engine import TableEngine
    return TableEngine(table_records)


@pytest.fixture(scope="session")
def pipeline(retriever, table_engine):
    from src.qa.pipeline import Pipeline
    return Pipeline(retriever, table_engine)
