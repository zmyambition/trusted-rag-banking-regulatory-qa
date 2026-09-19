"""评测归一化与正确性判定测试。"""
from __future__ import annotations

from src.evaluation.metrics import (
    text_correct, table_correct, is_correct, normalize_text,
)


def test_normalize_text():
    assert normalize_text(" 8% ") == "8%"
    assert normalize_text("１００％") == "100%"


def test_text_correct_substring():
    assert text_correct("8%", "第五条 商业银行资本充足率不得低于8%。")


def test_text_correct_multi_fact():
    assert text_correct("6%和5%", "第四条 不得低于6%。；第三条 不得低于5%。")


def test_table_correct_value():
    assert table_correct("135.2亿元", "135.2亿元")
    assert not table_correct("135.2亿元", "140.6亿元")


def test_table_correct_unit_conversion():
    # 数值相同但单位不同应判定不一致（避免错误地认为 10% == 0.1）
    assert table_correct("1.79%", "1.79%")
    assert not table_correct("1.79亿元", "1.79%")


def test_no_answer_consistency():
    assert text_correct("未找到足够证据", "未找到足够证据")
    assert not text_correct("未找到足够证据", "第五条 不得低于8%")


def test_is_correct_dispatch():
    assert is_correct("8%", "第五条 不得低于8%。", "text")
    assert is_correct("135.2亿元", "135.2亿元", "table")
