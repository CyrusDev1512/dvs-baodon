"""Test CLI tra sổ — đọc được DB do một lượt quét thật sinh ra."""
from __future__ import annotations

from src import report
from src.db import Store
from src.notify import DryRunImageStore, DryRunNotifier
from src.reconcile import run_cycle
from src.scraper.mock import MockScraper
from tests.conftest import make_order


def _seed_db(tmp_path, clock, settings):
    db = tmp_path / "r.db"
    store = Store(db, exception_text_log=tmp_path / "exc.txt")
    run_cycle(MockScraper(orders=[make_order()]), store, DryRunNotifier(echo=False),
              DryRunImageStore(), clock, settings)
    store.commit_and_close()
    return db


def test_report_overview_and_detail(tmp_path, clock, settings, capsys):
    db = _seed_db(tmp_path, clock, settings)

    assert report.main(["--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "TỔNG QUAN" in out and "Đơn đang theo dõi: 1" in out
    assert "Nguyễn Thu Hà" in out            # lịch sử báo đơn có tên Sale

    assert report.main(["--db", str(db), "--stt", "1502"]) == 0
    out = capsys.readouterr().out
    assert "ĐƠN STT 1502" in out and "đã báo" in out


def test_report_missing_db_is_friendly(tmp_path, capsys):
    assert report.main(["--db", str(tmp_path / "khong-co.db")]) == 1
    assert "Chưa có DB" in capsys.readouterr().out


def test_report_readonly_does_not_lock(tmp_path, clock, settings):
    """Tra sổ khi một lượt quét đang chạy: không tranh khoá."""
    db = _seed_db(tmp_path, clock, settings)
    live = Store(db)                          # lượt quét đang giữ khoá ghi
    try:
        assert report.main(["--db", str(db), "--exceptions"]) == 0
    finally:
        live.commit_and_close()
