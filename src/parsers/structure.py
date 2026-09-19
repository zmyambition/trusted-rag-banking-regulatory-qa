"""监管制度文档的结构识别：章 / 节 / 条 / 款 / 项。

Word 与 PDF 解析共享本模块，用于从文本中识别并标注：
- 章节（第一章 / 第一节）
- 条款（第十五条）
- 款/项（（一）/ 1. / 一、）

并提供统一入口 :func:`build_elements`，将"原始行"转换为带章节/条款
上下文标注的 :class:`~src.parsers.schemas.DocumentElement` 列表。
"""
from __future__ import annotations

import re
from typing import Optional

from .schemas import DocumentElement

# 中文数字 → 阿拉伯数字
_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "百": 100, "千": 1000, "万": 10000,
}

_PAT_CHAPTER = re.compile(r"^第\s*([零〇一二三四五六七八九十百千万两]+)\s*[章篇]\s*(.*)$")
_PAT_SECTION = re.compile(r"^第\s*([零〇一二三四五六七八九十百千万两]+)\s*节\s*(.*)$")
_PAT_ARTICLE = re.compile(r"^第\s*([零〇一二三四五六七八九十百千万两]+)\s*条\s*(.*)$")
_PAT_SUBITEM = re.compile(r"^[（(]\s*([零〇一二三四五六七八九十百千万两]+)\s*[）)]\s*(.*)$")
_PAT_CN_LIST = re.compile(r"^([零〇一二三四五六七八九十百千万两]+)\s*[、.．]\s*(.*)$")
_PAT_DIGIT_LIST = re.compile(r"^(\d+)\s*[、.．]\s*(.*)$")


def chinese_to_int(s: str) -> int:
    """中文数字转整数，如 "十五" -> 15、"一百二十三" -> 123。"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    total = 0
    section = 0
    number = 0
    for ch in s:
        if ch not in _CN_DIGITS:
            continue
        v = _CN_DIGITS[ch]
        if v >= 10:
            if v == 10000:
                total = (total + section) * 10000
                section = 0
            else:
                section = (number if number else 1) * v
                number = 0
                if v >= 100:
                    total += section
                    section = 0
        else:
            number = v
    return total + section + number


def detect_structure(text: str) -> Optional[tuple[str, str, str]]:
    """识别一行文本的结构类型。

    返回 ``(type, label, rest)``，type 为
    ``chapter/section/article/subitem/cn_list/digit_list`` 之一；
    未识别返回 None。
    """
    t = text.strip()
    m = _PAT_CHAPTER.match(t)
    if m:
        return ("chapter", f"第{m.group(1)}{'' if '章' in t else '篇'}", m.group(2))
    m = _PAT_SECTION.match(t)
    if m:
        return ("section", f"第{m.group(1)}节", m.group(2))
    m = _PAT_ARTICLE.match(t)
    if m:
        return ("article", f"第{m.group(1)}条", m.group(2))
    m = _PAT_SUBITEM.match(t)
    if m:
        return ("subitem", f"（{m.group(1)}）", m.group(2))
    m = _PAT_CN_LIST.match(t)
    if m:
        return ("cn_list", f"{m.group(1)}、", m.group(2))
    m = _PAT_DIGIT_LIST.match(t)
    if m:
        return ("digit_list", f"{m.group(1)}.", m.group(2))
    return None


def _heading_level_from_style(style_name: str) -> Optional[int]:
    """从 python-docx 样式名推断标题级别。"""
    if not style_name:
        return None
    s = style_name.lower()
    for i in range(1, 10):
        if f"heading {i}" in s or f"标题 {i}" in s or f"标题{i}" in s:
            return i
    return None


def build_elements(raw_lines: list[dict]) -> list[DocumentElement]:
    """将原始行列表转换为带结构标注的 DocumentElement 列表。

    ``raw_lines`` 每项需包含 ``text``，可包含 ``index`` / ``page`` /
    ``heading_level`` / ``style`` / ``metadata``。
    自动维护"当前章节"上下文，使条款与正文能继承其所属章节。
    """
    elements: list[DocumentElement] = []
    current_section: Optional[str] = None

    for i, raw in enumerate(raw_lines):
        text = (raw.get("text") or "").strip()
        if not text:
            continue

        page = raw.get("page")
        style = raw.get("style") or ""
        heading_level = raw.get("heading_level")
        if heading_level is None:
            heading_level = _heading_level_from_style(style)

        struct = detect_structure(text)
        kind = "paragraph"
        section = current_section
        article = None
        metadata = dict(raw.get("metadata") or {})

        if struct is not None:
            stype, label, _rest = struct
            if stype == "chapter":
                kind = "heading"
                heading_level = 1
                current_section = text
                section = text
                metadata["structure"] = "chapter"
            elif stype == "section":
                kind = "heading"
                heading_level = 2
                section = text
                metadata["structure"] = "section"
            elif stype == "article":
                kind = "heading"
                if heading_level is None:
                    heading_level = 3
                article = label
                metadata["structure"] = "article"
            elif stype in ("subitem", "cn_list", "digit_list"):
                kind = "paragraph"
                metadata["structure"] = stype
                metadata["structure_label"] = label

        elements.append(
            DocumentElement(
                kind=kind,
                text=text,
                index=i,
                heading_level=heading_level,
                section=section,
                article=article,
                page=page,
                metadata=metadata,
            )
        )
    return elements
