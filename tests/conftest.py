"""Fixture chung cho test backend báo đơn."""
from __future__ import annotations

import datetime as _dt

import pytest

from src.clock import Clock
from src.config import Settings
from src.db import Store
from src.scraper.interface import OrderToReport


class FakeClock(Clock):
    """Đồng hồ chỉnh tay được cho test timeline nhiều ngày."""

    def __init__(self, at: _dt.datetime):
        self.at = at

    def now(self) -> _dt.datetime:
        return self.at

    def set(self, *args) -> None:
        self.at = _dt.datetime(*args)

    def advance(self, **kwargs) -> None:
        self.at += _dt.timedelta(**kwargs)


def make_order(stt: str = "1502", sale: str = "Nguyễn Thu Hà",
               s_code: str | None = "S9663", group: str | None = "N15") -> OrderToReport:
    return OrderToReport(stt=stt, sale_name=sale, s_code=s_code, group_symbol=group)


def make_settings(**overrides) -> Settings:
    base = dict(
        seven_eleven_url="", seven_eleven_user="", seven_eleven_pass="",
        seven_eleven_storage_state=__import__("pathlib").Path(".auth/x.json"),
        headless=True,
        scan_interval_minutes=15,
        remind_times=(_dt.time(9, 0), _dt.time(14, 0)),
        remind_max_days=7,
        quiet_hours=(_dt.time(21, 0), _dt.time(7, 0)),
        notify_rate_per_min=10,
        db_path=__import__("pathlib").Path("data/test.db"),
    )
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def settings():
    return make_settings()


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.db", exception_text_log=tmp_path / "exc.txt")
    yield s
    try:
        s.commit_and_close()
    except Exception:
        pass


@pytest.fixture
def clock():
    return FakeClock(_dt.datetime(2026, 8, 7, 8, 0))
