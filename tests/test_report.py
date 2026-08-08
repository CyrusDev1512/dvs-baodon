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


def test_report_prints_vietnamese_on_non_utf8_stdout(tmp_path, monkeypatch):
    """Máy chưa bật UTF-8 (stdout cp1252, errors strict): lệnh vẫn phải chạy được
    thay vì chết vì UnicodeEncodeError — main() tự chuyển stdout sang utf-8."""
    import io
    import sys

    raw = io.BytesIO()
    monkeypatch.setattr(
        sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    )
    assert report.main(["--db", str(tmp_path / "khong-co.db")]) == 1
    sys.stdout.flush()
    assert "Chưa có DB" in raw.getvalue().decode("utf-8")


def test_report_stt_not_found_returns_nonzero(tmp_path, clock, settings, capsys):
    db = _seed_db(tmp_path, clock, settings)
    assert report.main(["--db", str(db), "--stt", "9999"]) == 1
    assert "Không có trong DB" in capsys.readouterr().out


def test_report_stt_is_normalized(tmp_path, clock, settings, capsys):
    """STT dán vào kèm khoảng trắng vẫn tra được (giá trị lưu đã qua norm_stt)."""
    db = _seed_db(tmp_path, clock, settings)
    assert report.main(["--db", str(db), "--stt", " 1502 "]) == 0
    assert "ĐƠN STT 1502" in capsys.readouterr().out


def test_report_readonly_does_not_lock(tmp_path, clock, settings):
    """Tra sổ khi một lượt quét đang chạy: không tranh khoá."""
    db = _seed_db(tmp_path, clock, settings)
    live = Store(db)                          # lượt quét đang giữ khoá ghi
    try:
        assert report.main(["--db", str(db), "--exceptions"]) == 0
    finally:
        live.commit_and_close()
