"""Test lõi quy tắc thuần — ma trận biên của giờ giấc."""
from __future__ import annotations

import datetime as _dt
from datetime import time

from src import rules
from tests.conftest import make_order

QUIET = (time(21, 0), time(7, 0))
MARKS = (time(9, 0), time(14, 0))


def dt(h, m=0, day=7):
    return _dt.datetime(2026, 8, day, h, m)


def test_order_key_is_stt_verbatim():
    assert rules.order_key(make_order(stt="0042")) == "0042"


class TestQuietHours:
    def test_midnight_crossing_boundaries(self):
        assert rules.in_quiet_hours(dt(21, 0), QUIET) is True   # bắt đầu
        assert rules.in_quiet_hours(dt(22, 0), QUIET) is True
        assert rules.in_quiet_hours(dt(6, 59), QUIET) is True
        assert rules.in_quiet_hours(dt(7, 0), QUIET) is False   # hết giờ im lặng
        assert rules.in_quiet_hours(dt(20, 59), QUIET) is False
        assert rules.in_quiet_hours(dt(12, 0), QUIET) is False

    def test_non_crossing_window(self):
        q = (time(12, 0), time(13, 0))
        assert rules.in_quiet_hours(dt(12, 30), q) is True
        assert rules.in_quiet_hours(dt(13, 0), q) is False
        assert rules.in_quiet_hours(dt(11, 59), q) is False


class TestDueRemindMark:
    def test_before_first_mark_none(self):
        assert rules.due_remind_mark(dt(8, 30), dt(7, 0), MARKS) is None

    def test_fires_after_mark(self):
        assert rules.due_remind_mark(dt(9, 7), dt(7, 0), MARKS) == dt(9, 0)

    def test_no_double_fire_same_day(self):
        # đã gửi lúc 09:07 → lượt 09:22 không bắn lại
        assert rules.due_remind_mark(dt(9, 22), dt(9, 7), MARKS) is None

    def test_missed_mark_catches_up(self):
        # máy tắt lúc 09:00, chạy lại 10:30 → vẫn bắn bù mốc 09:00
        assert rules.due_remind_mark(dt(10, 30), dt(7, 0), MARKS) == dt(9, 0)

    def test_second_mark_same_day(self):
        assert rules.due_remind_mark(dt(14, 3), dt(9, 7), MARKS) == dt(14, 0)

    def test_next_day_refires(self):
        assert rules.due_remind_mark(dt(9, 5, day=8), dt(14, 3, day=7), MARKS) == dt(9, 0, day=8)

    def test_yesterday_mark_counts_after_long_gap(self):
        # nghỉ từ 08:00 hôm trước tới 00:30 hôm nay → nợ mốc 14:00 hôm qua
        assert rules.due_remind_mark(dt(0, 30, day=8), dt(8, 0, day=7), MARKS) == dt(14, 0, day=7)


class TestIsExpired:
    def test_boundary_exact_days(self):
        first = dt(8, 0, day=1)
        assert rules.is_expired(dt(8, 0, day=8), first, 7) is True     # đúng 7 ngày
        assert rules.is_expired(dt(7, 59, day=8), first, 7) is False   # thiếu 1 phút
