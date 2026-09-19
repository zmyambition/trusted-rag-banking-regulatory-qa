"""统一数据模型（Schema）。

本文件定义系统内所有核心数据结构的统一表示，供解析、检索、表格查询、
问答与评测各模块复用。字段约定：

- TextChunk：文本证据的最小单元，``source_file`` 与 ``text`` 必须存在；
- TableRecord：表格中单个数值单元格及其来源、行列表头、单位等；
- AnswerResult：一次问答的统一输出。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 解析中间结构：文档元素
# ---------------------------------------------------------------------------
@dataclass
class DocumentElement:
    """一个段落 / 标题 / 表格等文档单元。"""
    kind: str                     # "paragraph" | "heading" | "table"
    text: str
    index: int                    # 在文档中的顺序
    heading_level: Optional[int] = None   # 标题级别（1~n），无则 None
    section: Optional[str] = None         # 章节，如 "第一章"
    article: Optional[str] = None         # 条款，如 "第十五条"
    page: Optional[int] = None            # 页码（PDF 可用）
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParsedDocument:
    """一个文件解析后的结果。"""
    source_file: str
    file_type: str                # "docx" | "pdf" | "doc"
    elements: list = field(default_factory=list)
    tables: list = field(default_factory=list)   # Word 内嵌表格（如有）
    warnings: list = field(default_factory=list)  # 解析告警信息

    def to_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "file_type": self.file_type,
            "elements": [e.to_dict() for e in self.elements],
            "tables": self.tables,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 文本 Chunk
# ---------------------------------------------------------------------------
@dataclass
class TextChunk:
    chunk_id: str
    text: str
    source_file: str
    page: Optional[int] = None
    paragraph: Optional[int] = None
    section: Optional[str] = None
    article: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 表格记录（单个数值单元格）
# ---------------------------------------------------------------------------
@dataclass
class TableRecord:
    source_file: str
    sheet: str
    row: int
    column: int
    cell: str                     # Excel 坐标，如 "D12"
    value: Any                    # 数值或文本值
    row_header: str = ""          # 行标签合并结果，如 "A机构 / 营业收入"
    column_header: str = ""       # 列表头合并结果，如 "2025年 / 第一季度"
    row_labels: list = field(default_factory=list)
    column_labels: list = field(default_factory=list)
    headers: dict = field(default_factory=dict)   # 结构化表头映射
    unit: str = ""                # 检测到的单位，如 "亿元"、"%"、"万元"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def searchable_text(self) -> str:
        """用于指标/期间/机构匹配的拼接文本。"""
        parts = self.row_labels + self.column_labels + [self.sheet]
        return " ".join(str(p) for p in parts if p)


# ---------------------------------------------------------------------------
# 问答统一输出
# ---------------------------------------------------------------------------
@dataclass
class AnswerResult:
    question: str
    answer: str
    question_type: str            # "text" | "table" | "mixed"
    confidence: float = 0.0
    evidence: list = field(default_factory=list)   # 证据文本/记录（dict 列表）
    sources: list = field(default_factory=list)    # 来源摘要（dict 列表）
    status: str = "answered"      # "answered" | "no_evidence"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def cell_coordinate(row: int, column: int) -> str:
    """将 (行, 列) 转为 Excel 坐标，如 (12, 4) -> "D12"。

    ``column`` 为 1 起始列号。
    """
    col = column - 1
    letters = ""
    while col >= 0:
        letters = chr(ord("A") + col % 26) + letters
        col = col // 26 - 1
    return f"{letters}{row}"
