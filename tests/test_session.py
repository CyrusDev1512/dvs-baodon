"""Test phần quản lý phiên không cần trình duyệt."""
from __future__ import annotations

import datetime as _dt

from src.scraper.session import is_login_page, storage_state_age_days


def test_detects_login_page_by_url():
    assert is_login_page("https://myship.7-11.com.tw/Login") is True
    assert is_login_page("https://x.com/auth/signin") is True
    assert is_login_page("https://myship.7-11.com.tw/seller/order") is False


def test_storage_state_age(tmp_path):
    assert storage_state_age_days(tmp_path / "chua-co.json") is None

    state = tmp_path / "state.json"
    state.write_text("{}", encoding="utf-8")
    age = storage_state_age_days(state)
    assert age is not None and age < 0.01          # vừa tạo xong

    later = _dt.datetime.now() + _dt.timedelta(days=3)
    assert round(storage_state_age_days(state, now=later)) == 3
