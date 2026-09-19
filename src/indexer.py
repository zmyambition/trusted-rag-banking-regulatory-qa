"""索引构建器：扫描数据 → 解析 → 切分 → 建立检索与表格查询索引。

- 支持增量缓存：根据源文件 mtime/size 判断是否需要重建；
- .doc（旧格式）无法用 python-docx 解析时，明确记录告警而非静默跳过。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .parsers.docx_parser import parse_docx
from .parsers.pdf_parser import parse_pdf
from .parsers.excel_parser import parse_excel
from .parsers.schemas import TextChunk, TableRecord
from .knowledge.chunker import chunk_document
from .retrieval.hybrid_retriever import HybridRetriever
from .table_query.table_engine import TableEngine
from .utils.config import Paths
from .utils.logging import get_logger

log = get_logger("indexer")

_DOC_EXTS = {".docx", ".pdf", ".doc"}
_TABLE_EXTS = {".xlsx", ".xlsm", ".xls"}


@dataclass
class IndexStats:
    documents: int = 0
    chunks: int = 0
    tables: int = 0
    table_records: int = 0
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "documents": self.documents,
            "chunks": self.chunks,
            "tables": self.tables,
            "table_records": self.table_records,
            "warnings": self.warnings,
        }


class Indexer:
    def __init__(
        self,
        docs_dir: Path = Paths.DOCUMENTS_DIR,
        tables_dir: Path = Paths.TABLES_DIR,
        indexes_dir: Path = Paths.INDEXES_DIR,
    ):
        self.docs_dir = Path(docs_dir)
        self.tables_dir = Path(tables_dir)
        self.indexes_dir = Path(indexes_dir)
        self.indexes_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def list_documents(self) -> list[Path]:
        files: list[Path] = []
        if self.docs_dir.exists():
            files += sorted(p for p in self.docs_dir.iterdir() if p.suffix.lower() in _DOC_EXTS)
        return files

    def list_tables(self) -> list[Path]:
        files: list[Path] = []
        if self.tables_dir.exists():
            files += sorted(p for p in self.tables_dir.iterdir() if p.suffix.lower() in _TABLE_EXTS)
        return files

    # ------------------------------------------------------------------
    def build(self, force: bool = False) -> tuple[HybridRetriever, TableEngine, IndexStats]:
        """构建索引，返回 (retriever, table_engine, stats)。"""
        Paths.ensure_dirs()
        if not force and self._cache_valid():
            loaded = self._load_cache()
            if loaded is not None:
                chunks, records, stats = loaded
                log.info("从缓存加载索引：%d chunks, %d records", len(chunks), len(records))
                return HybridRetriever(chunks), TableEngine(records), stats

        stats = IndexStats()
        chunks: list[TextChunk] = []
        records: list[TableRecord] = []

        for doc_path in self.list_documents():
            try:
                if doc_path.suffix.lower() == ".docx":
                    parsed = parse_docx(doc_path)
                elif doc_path.suffix.lower() == ".pdf":
                    parsed = parse_pdf(doc_path)
                elif doc_path.suffix.lower() == ".doc":
                    stats.warnings.append(f"{doc_path.name}: 旧版 .doc 格式无法直接解析，请转换为 .docx")
                    log.warning("跳过旧版 .doc：%s", doc_path.name)
                    continue
                else:
                    continue
                stats.warnings += [f"{doc_path.name}: {w}" for w in parsed.warnings]
                chunks += chunk_document(parsed)
                stats.documents += 1
            except Exception as e:  # noqa: BLE001
                stats.warnings.append(f"{doc_path.name}: 解析失败 - {e}")
                log.warning("解析失败 %s: %s", doc_path.name, e)

        for table_path in self.list_tables():
            try:
                if table_path.suffix.lower() == ".xls":
                    stats.warnings.append(f"{table_path.name}: 旧版 .xls 格式，请转换为 .xlsx")
                    log.warning("跳过旧版 .xls：%s", table_path.name)
                    continue
                recs, warns = parse_excel(table_path)
                stats.warnings += [f"{table_path.name}: {w}" for w in warns]
                records += recs
                stats.tables += 1
            except Exception as e:  # noqa: BLE001
                stats.warnings.append(f"{table_path.name}: 解析失败 - {e}")
                log.warning("解析失败 %s: %s", table_path.name, e)

        stats.chunks = len(chunks)
        stats.table_records = len(records)

        self._save_cache(chunks, records, stats)

        log.info(
            "索引构建完成：documents=%d chunks=%d tables=%d records=%d",
            stats.documents, stats.chunks, stats.tables, stats.table_records,
        )
        return HybridRetriever(chunks), TableEngine(records), stats

    # ------------------------------------------------------------------
    # 缓存
    # ------------------------------------------------------------------
    def _source_signature(self) -> str:
        files = self.list_documents() + self.list_tables()
        sig = []
        for f in files:
            st = f.stat()
            sig.append(f"{f.name}|{st.st_mtime_ns}|{st.st_size}")
        return hashlib.sha1(";".join(sig).encode("utf-8")).hexdigest()

    def _cache_valid(self) -> bool:
        manifest = self.indexes_dir / "manifest.json"
        if not manifest.exists():
            return False
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            return data.get("signature") == self._source_signature()
        except Exception:  # noqa: BLE001
            return False

    def _save_cache(self, chunks: list[TextChunk], records: list[TableRecord], stats: IndexStats) -> None:
        (self.indexes_dir / "chunks.json").write_text(
            json.dumps([c.to_dict() for c in chunks], ensure_ascii=False), encoding="utf-8"
        )
        (self.indexes_dir / "tables.json").write_text(
            json.dumps([r.to_dict() for r in records], ensure_ascii=False), encoding="utf-8"
        )
        (self.indexes_dir / "manifest.json").write_text(
            json.dumps({"signature": self._source_signature(), "stats": stats.to_dict()}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_cache(self) -> tuple[list[TextChunk], list[TableRecord], IndexStats] | None:
        try:
            chunks_raw = json.loads((self.indexes_dir / "chunks.json").read_text(encoding="utf-8"))
            records_raw = json.loads((self.indexes_dir / "tables.json").read_text(encoding="utf-8"))
            manifest = json.loads((self.indexes_dir / "manifest.json").read_text(encoding="utf-8"))
            chunks = [TextChunk(**c) for c in chunks_raw]
            records = [TableRecord(**r) for r in records_raw]
            stats = IndexStats(**manifest.get("stats", {}))
            return chunks, records, stats
        except Exception:  # noqa: BLE001
            return None
