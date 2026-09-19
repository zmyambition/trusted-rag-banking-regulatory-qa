"""统一日志配置：控制台 + 文件，避免极端冗余。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from .config import Paths

_LOGGER_NAME = "trusted_rag"
_configured = False


def get_logger(name: str | None = None) -> logging.Logger:
    """返回命名 logger（默认挂载到 trusted_rag 根 logger）。"""
    root = logging.getLogger(_LOGGER_NAME)
    if not root.handlers:
        configure()
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return root


def configure(level: int = logging.INFO) -> None:
    """初始化全局日志。幂等，可重复调用。"""
    global _configured
    root = logging.getLogger(_LOGGER_NAME)
    if root.handlers:
        return
    root.setLevel(level)
    root.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # 控制台 handler：中文环境强制 UTF-8，避免 GBK 编码报错
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # 文件 handler
    log_file = Paths.OUTPUTS_DIR / "app.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    _configured = True
