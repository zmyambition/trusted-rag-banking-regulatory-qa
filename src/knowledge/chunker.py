"""文本切分（Chunking）。

监管制度文档不能机械地每 N 字符切一次。切分优先级：

    条款 > 段落 > 标题结构 > 长度切分

策略：
1. 先按"标题元素"（章/节/条）把文档切成块，保证"第十五条"及其内容在同一块；
2. 块过长（超过 target_max）时，再按段落/长度进一步切分，允许 overlap；
3. 每个 Chunk 继承 source_file / page / paragraph / section / article 来源信息。
"""
from __future__ import annotations

from ..parsers.schemas import ParsedDocument, TextChunk, DocumentElement
from ..utils.config import ChunkConfig
from ..utils.logging import get_logger

log = get_logger("chunker")


def _split_long(elements: list[DocumentElement], max_len: int, overlap: int) -> list[list[DocumentElement]]:
    """把过长的元素列表按长度二次切分，保留 overlap（按段落粒度尽量不切开）。"""
    groups: list[list[DocumentElement]] = []
    cur: list[DocumentElement] = []
    cur_len = 0
    for elem in elements:
        cur.append(elem)
        cur_len += len(elem.text)
        if cur_len >= max_len:
            groups.append(cur)
            # overlap：把最后一个元素保留到下一组
            if overlap > 0 and len(cur) > 1:
                cur = [cur[-1]]
                cur_len = len(cur[-1].text)
            else:
                cur = []
                cur_len = 0
    if cur:
        groups.append(cur)
    return groups


def chunk_document(
    parsed: ParsedDocument,
    target_max: int = ChunkConfig.TARGET_MAX,
    overlap: int = ChunkConfig.OVERLAP,
) -> list[TextChunk]:
    """把单个 ParsedDocument 切分为 TextChunk 列表。"""
    elements = parsed.elements
    if not elements:
        return []

    # 1. 按标题元素分块
    blocks: list[list[DocumentElement]] = []
    cur: list[DocumentElement] = []
    for elem in elements:
        if elem.kind == "heading" and cur:
            blocks.append(cur)
            cur = [elem]
        else:
            cur.append(elem)
    if cur:
        blocks.append(cur)

    # 2. 二次切分过长的块
    chunks: list[TextChunk] = []
    seq = 0
    for block in blocks:
        if sum(len(e.text) for e in block) > target_max:
            groups = _split_long(block, target_max, overlap)
        else:
            groups = [block]

        for group in groups:
            text = "\n".join(e.text for e in group if e.text.strip())
            if not text.strip():
                continue
            head = group[0]
            # 找到块内标题元素（若有）作为 article/section 元数据
            article = head.article
            section = head.section
            for e in group:
                if e.article:
                    article = e.article
                if e.section:
                    section = e.section
            page = head.page
            chunks.append(
                TextChunk(
                    chunk_id=f"{parsed.source_file}#{seq}",
                    text=text,
                    source_file=parsed.source_file,
                    page=page,
                    paragraph=head.index,
                    section=section,
                    article=article,
                    metadata={"file_type": parsed.file_type},
                )
            )
            seq += 1

    return chunks
