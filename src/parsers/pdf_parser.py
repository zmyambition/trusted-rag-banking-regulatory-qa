"""PDF 解析器（PyMuPDF / fitz）。

- 逐页解析，保留页码；
- 检查每页提取文字是否为空，过滤明显无意义字符；
- 记录疑似扫描件（大量页面为空）的告警信息；
- 不假设"程序无异常 = 解析成功"。
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF

from .schemas import ParsedDocument
from .structure import build_elements
from ..utils.config import ParseConfig

# 明显无意义的乱码/占位字符（常见于 PDF 文本提取噪声）
_NOISE_PAT = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _clean_text(text: str) -> str:
    text = _NOISE_PAT.sub("", text)
    text = text.replace("　", " ").replace("\xa0", " ")
    return text


def parse_pdf(path: str | Path) -> ParsedDocument:
    """解析单个 PDF 文件，返回 ParsedDocument。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    raw_lines: list[dict] = []
    warnings: list[str] = []
    empty_pages: list[int] = []
    idx = 0
    total_pages = 0

    with fitz.open(str(path)) as doc:
        total_pages = len(doc)
        for page_no in range(total_pages):
            page = doc[page_no]
            page_text = _clean_text(page.get_text("text"))
            if len(page_text.strip()) < ParseConfig.PDF_MIN_PAGE_CHARS:
                empty_pages.append(page_no + 1)
            # 按行拆分，保留页码；每行作为一个待结构识别的"行"
            for line in page_text.splitlines():
                line = line.strip()
                if not line:
                    continue
                raw_lines.append({
                    "text": line,
                    "index": idx,
                    "page": page_no + 1,
                })
                idx += 1

    if len(raw_lines) == 0:
        warnings.append("PDF 全文未提取到任何可读文本（可能为扫描件或加密文档）")
    if total_pages > 0 and len(empty_pages) / total_pages > 0.5:
        warnings.append(
            f"疑似扫描 PDF：{len(empty_pages)}/{total_pages} 页提取为空，"
            "若为扫描件需 OCR 支持。"
        )

    elements = build_elements(raw_lines)
    return ParsedDocument(
        source_file=str(path),
        file_type="pdf",
        elements=elements,
        tables=[],
        warnings=warnings,
    )
