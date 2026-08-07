"""Test tầng lưu trữ: schema idempotent, chuyển trạng thái, sổ ngoại lệ, khoá."""
from __future__ import annotations

import datetime as _dt

import pytest

from src.db import Store, StoreLockedError, parse_ts
from tests.conftest import make_order

NOW = _dt.datetime(2026, 8, 7, 8, 0)
LATER = _dt.datetime(2026, 8, 7, 9, 0)


def test_schema_idempotent(tmp_path):
    p = tmp_path / "x.db"
    s1 = Store(p)
    s1.commit_and_close()
    s2 = Store(p)  # mở lại trên file đã có schema — không lỗi
    s2.commit_and_close()


def test_insert_touch_close_reopen(store):
    o = make_order()
    store.insert_order("1502", o, NOW)
    row = store.get_all()["1502"]
    assert row["status"] == "active" and row["first_notified_at"] is None

    store.touch_seen("1502", LATER)
    assert parse_ts(store.get_all()["1502"]["last_seen_at"]) == LATER

    store.close_order("1502", LATER)
    assert store.get_all()["1502"]["status"] == "closed"

    store.reopen_order("1502", LATER)
    row = store.get_all()["1502"]
    assert row["status"] == "active"
    assert row["reopen_count"] == 1
    assert row["closed_at"] is None
    assert row["first_notified_at"] is None          # được báo lại ngay
    assert parse_ts(row["first_seen_at"]) == LATER   # reset đồng hồ REMIND_MAX_DAYS


def test_mark_notified_sets_first_only_once(store):
    store.insert_order("1502", make_order(), NOW)
    store.mark_notified("1502", "first", "Nguyễn Thu Hà", NOW, "dry-run")
    store.mark_notified("1502", "remind", "Nguyễn Thu Hà", LATER, "dry-run")
    row = store.get_all()["1502"]
    assert parse_ts(row["first_notified_at"]) == NOW      # không bị ghi đè
    assert parse_ts(row["last_notified_at"]) == LATER
    kinds = [r["kind"] for r in store.notifications_for("1502")]
    assert kinds == ["first", "remind"]


def test_exception_log_db_and_text_mirror(store, tmp_path):
    store.log_exception(NOW, "1502", "không có ảnh báo đơn", "chi tiết")
    assert store.exception_count() == 1
    text = (tmp_path / "exc.txt").read_text(encoding="utf-8")
    assert "STT 1502" in text and "không có ảnh báo đơn" in text


def test_second_instance_locked(tmp_path):
    p = tmp_path / "x.db"
    s1 = Store(p)
    with pytest.raises(StoreLockedError):
        Store(p)  # lượt thứ hai chạy chồng → từ chối ngay
    s1.commit_and_close()
