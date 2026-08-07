"""Test parser cấu hình — fail fast khi .env sai định dạng."""
from __future__ import annotations

from datetime import time

import pytest

from src.config import _parse_hhmm, _parse_range, _parse_times_csv


def test_parse_hhmm():
    assert _parse_hhmm("09:00") == time(9, 0)
    assert _parse_hhmm(" 21:30 ") == time(21, 30)
    with pytest.raises(ValueError):
        _parse_hhmm("9h00")


def test_parse_times_csv_sorted():
    assert _parse_times_csv("14:00,09:00") == (time(9, 0), time(14, 0))
    with pytest.raises(ValueError):
        _parse_times_csv("")


def test_parse_range_midnight_crossing_allowed():
    assert _parse_range("21:00-07:00") == (time(21, 0), time(7, 0))
    with pytest.raises(ValueError):
        _parse_range("21:00")
