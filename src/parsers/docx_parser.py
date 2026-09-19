"""Word (.docx) 解析器。

- 使用 python-docx 读取正文段落与内嵌表格，并保留其在文档中的顺序；
- 保留段落索引、标题级别、章节/条款结构；
- 若 Word 含表格，至少保留其文本内容与位置信息（表格 → text 证据）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from .schemas import ParsedDocument
from .structure import build_elements


def iter_block_items(parent) -> Iterator[object]:
    """按文档顺序迭代段落与表格（python-docx 默认只给段落）。"""
    for child in parent.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def _table_text(table: Table) -> str:
    """把 Word 表格展平为可检索文本（保留行列分隔）。"""
    rows: list[str] = []
    for row in table.rows:
        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def parse_docx(path: str | Path) -> ParsedDocument:
    """解析单个 .docx 文件。

    Raises:
        Exception: 文件不存在或无法解析时向上抛出，由调用方记录。
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    doc = Document(str(path))

    raw_lines: list[dict] = []
    tables: list[dict] = []
    warnings: list[str] = []
    idx = 0

    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            raw_lines.append({
                "text": block.text,
                "index": idx,
                "style": block.style.name if block.style is not None else "",
            })
            idx += 1
        elif isinstance(block, Table):
            text = _table_text(block)
            if text.strip():
                # 表格内容作为普通段落参与后续检索，同时单独记录表格位置
                raw_lines.append({
                    "text": text,
                    "index": idx,
                    "style": "",
                    "metadata": {"is_table": True},
                })
                tables.append({"index": idx, "text": text})
                idx += 1

    elements = build_elements(raw_lines)

    if not any(e.text.strip() for e in elements):
        warnings.append("文档未提取到任何可读文本内容")

    return ParsedDocument(
        source_file=str(path),
        file_type="docx",
        elements=elements,
        tables=tables,
        warnings=warnings,
    )
