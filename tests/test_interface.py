"""Test hợp đồng normalization — chạy được ngay, không cần site thật."""
from src.scraper.interface import norm_s_code, norm_sale_name, norm_stt


def test_norm_stt_keeps_string_as_displayed():
    assert norm_stt("  007 ") == "007"


def test_norm_sale_name_collapses_whitespace_keeps_case():
    assert norm_sale_name("  Nguyễn   Văn\tA ") == "Nguyễn Văn A"


def test_norm_s_code_uppercases_and_empty_is_none():
    assert norm_s_code(" s1234 ") == "S1234"
    assert norm_s_code("   ") is None
    assert norm_s_code(None) is None
