"""Test MockScraper tuân đúng contract như một scraper thật."""
from __future__ import annotations

import pytest

from src.scraper.interface import BaseScraper, ParseError
from src.scraper.mock import MockScraper, build_scraper, default_orders


def test_conforms_to_contract():
    scraper = build_scraper()
    assert isinstance(scraper, BaseScraper)
    orders = scraper.fetch_orders_to_report()
    assert len(orders) == 12
    for o in orders:
        assert o.stt == o.stt.strip()                 # đã norm
        assert "  " not in o.sale_name                # whitespace đã gộp
        assert o.s_code is None or o.s_code == o.s_code.upper()


def test_zero_padded_stt_not_int_cast():
    stts = [o.stt for o in default_orders()]
    assert "0042" in stts  # giữ nguyên chuỗi, không thành "42"


def test_error_injection():
    scraper = MockScraper(error=ParseError("giả lập đọc thiếu trang"))
    with pytest.raises(ParseError):
        scraper.fetch_orders_to_report()
