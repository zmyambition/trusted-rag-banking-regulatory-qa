"""统一配置：路径、检索参数、置信度阈值等。

所有路径均以项目根目录为基准动态计算，不写死绝对路径，
保证在 Windows / macOS / Linux 及任意安装位置均可运行。
"""
from __future__ import annotations

import os
from pathlib import Path

# 项目根目录 = src/utils/config.py 向上两级
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
class Paths:
    ROOT: Path = PROJECT_ROOT
    DATA_DIR: Path = PROJECT_ROOT / "data"
    DOCUMENTS_DIR: Path = DATA_DIR / "documents"      # Word / PDF 制度文档
    TABLES_DIR: Path = DATA_DIR / "tables"            # Excel 统计报表
    QUESTIONS_DIR: Path = DATA_DIR / "questions"       # 测试问题集
    SAMPLE_DIR: Path = DATA_DIR / "sample"            # 合成样例数据源
    INDEXES_DIR: Path = PROJECT_ROOT / "indexes"      # 索引缓存
    OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"      # 评测输出
    REPORTS_DIR: Path = PROJECT_ROOT / "reports"      # 报告

    @classmethod
    def all_dirs(cls) -> list[Path]:
        return [
            cls.ROOT, cls.DATA_DIR, cls.DOCUMENTS_DIR, cls.TABLES_DIR,
            cls.QUESTIONS_DIR, cls.SAMPLE_DIR, cls.INDEXES_DIR,
            cls.OUTPUTS_DIR, cls.REPORTS_DIR,
        ]

    @classmethod
    def ensure_dirs(cls) -> None:
        for d in cls.all_dirs():
            d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 文档解析
# ---------------------------------------------------------------------------
class ParseConfig:
    # Word/PDF 中会被忽略的空白/无意义文本
    STRIP_CHARS: str = " \t\r\n　\xa0"
    # PDF 单页提取为空或字符过少时视为"疑似扫描/空页"
    PDF_MIN_PAGE_CHARS: int = 5


# ---------------------------------------------------------------------------
# Chunk 切分
# ---------------------------------------------------------------------------
class ChunkConfig:
    TARGET_MIN: int = 300      # 目标最小长度（中文字符）
    TARGET_MAX: int = 800      # 目标最大长度
    OVERLAP: int = 50          # 超长条款切分时的重叠长度


# ---------------------------------------------------------------------------
# 检索
# ---------------------------------------------------------------------------
class RetrievalConfig:
    TOP_K: int = 5             # 最终返回给答案生成的证据数
    CANDIDATE_K: int = 20      # 检索候选数
    BM25_K1: float = 1.5
    BM25_B: float = 0.75
    # 混合检索 RRF 参数
    RRF_K: int = 60


# ---------------------------------------------------------------------------
# 表格查询
# ---------------------------------------------------------------------------
class TableConfig:
    # 表头识别：一行中文本占比超过该值即视为表头/标签行
    HEADER_TEXT_RATIO: float = 0.6
    # 数值单元格才会进入 TableRecord（跳过纯文本标签）
    # 指标匹配分数阈值（0~1）
    MATCH_SCORE_MIN: float = 60.0


# ---------------------------------------------------------------------------
# 置信度 / 拒答
# ---------------------------------------------------------------------------
class ConfidenceConfig:
    TEXT_MIN_SCORE: float = 0.0      # BM25 归一化分数下限
    TEXT_KEYWORD_COVERAGE: float = 0.6   # 问题内容词在证据中的覆盖率下限，低于则拒答
    TABLE_MIN_MATCH: float = 60.0    # rapidfuzz 分数下限


# ---------------------------------------------------------------------------
# 环境变量读取（用于可选 LLM / Embedding）
# ---------------------------------------------------------------------------
def get_env(name: str, default: str = "") -> str:
    """读取环境变量，若为空返回 default。"""
    return os.environ.get(name, default).strip()


Paths.ensure_dirs()
