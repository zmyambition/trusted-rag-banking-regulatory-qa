"""来源元数据工具：生成 chunk_id、证据来源摘要等。"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..parsers.schemas import TextChunk, TableRecord


def stable_id(text: str, length: int = 12) -> str:
    """基于文本内容生成稳定短 id（用于索引缓存校验等）。"""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def text_source_summary(chunk: TextChunk) -> dict:
    """文本 Chunk 的来源摘要，用于 Evidence / Source 展示。"""
    s: dict = {
        "source_file": Path(chunk.source_file).name,
        "page": chunk.page,
        "paragraph": chunk.paragraph,
        "section": chunk.section,
        "article": chunk.article,
    }
    # 去除 None，保持输出干净
    return {k: v for k, v in s.items() if v is not None}


def table_source_summary(rec: TableRecord) -> dict:
    """表格记录来源摘要。"""
    return {
        "source_file": rec.source_file,
        "sheet": rec.sheet,
        "cell": rec.cell,
        "row": rec.row,
        "column": rec.column,
        "unit": rec.unit or None,
    }
