"""Test parser cấu hình — fail fast khi .env sai định dạng."""
from __future__ import annotations

from datetime import time

import pytest

from pathlib import Path

from src.config import PROJECT_ROOT, _anchor, _parse_hhmm, _parse_range, _parse_times_csv


def test_relative_paths_anchor_to_project_not_cwd():
    """Task Scheduler chạy với cwd lạ — đường dẫn tương đối phải neo vào gốc dự án,
    nếu không mỗi lượt sẽ ghi DB ở một chỗ khác nhau."""
    assert _anchor(Path("data/baodon.db")) == PROJECT_ROOT / "data/baodon.db"
    assert _anchor(Path("data/baodon.db")).is_absolute()


def test_absolute_path_left_alone():
    p = Path(PROJECT_ROOT / "elsewhere.db")
    assert _anchor(p) == p


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
