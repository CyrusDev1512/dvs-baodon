"""Chạy MỘT lượt báo đơn trọn vẹn rồi thoát (lên lịch bằng Windows Task Scheduler).

Ví dụ:
    python -m src.run_once --mock                          # dry-run với dữ liệu giả
    python -m src.run_once --mock --now "2026-08-07 09:05" # demo mốc nhắc 09:00
    python -m src.run_once --mock --mock-file kich_ban.json

Exit code: 0 = lượt chạy sạch, 1 = lượt bị hủy (scan thất bại / DB đang bị khoá).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time as _time
from pathlib import Path

from src.clock import FixedClock, SystemClock
from src.config import get_settings
from src.db import Store, StoreLockedError
from src.notify import DryRunImageStore, DryRunNotifier
from src.reconcile import run_cycle
from src.scraper.interface import OrderToReport, norm_s_code, norm_sale_name, norm_stt
from src.scraper.mock import MockScraper


def _load_mock_file(path: Path) -> list[OrderToReport]:
    """File JSON: [{"stt": "...", "sale_name": "...", "s_code": ..., ...}, ...]"""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        OrderToReport(
            stt=norm_stt(d["stt"]),
            sale_name=norm_sale_name(d["sale_name"]),
            s_code=norm_s_code(d.get("s_code")),
            group_symbol=d.get("group_symbol"),
            raw=d.get("raw", {}),
        )
        for d in data
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chạy một lượt báo đơn (dry-run)")
    parser.add_argument("--mock", action="store_true",
                        help="Dùng MockScraper thay vì scraper thật (Track A đang chặn)")
    parser.add_argument("--mock-file", type=Path,
                        help="File JSON danh sách đơn giả cho kịch bản tuỳ biến")
    parser.add_argument("--db", type=Path, help="Đường dẫn SQLite (mặc định theo .env)")
    parser.add_argument("--now", help='Giả lập thời điểm chạy, "YYYY-MM-DD HH:MM"')
    parser.add_argument("--real-pace", action="store_true",
                        help="Giãn nhịp gửi thật theo NOTIFY_RATE_PER_MIN")
    args = parser.parse_args(argv)

    settings = get_settings()

    if args.mock or args.mock_file:
        orders = _load_mock_file(args.mock_file) if args.mock_file else None
        scraper = MockScraper(orders=orders)
    else:
        # Điểm swap một dòng khi Track A sẵn sàng:
        from src.scraper.seven_eleven import SevenElevenScraper
        scraper = SevenElevenScraper()

    clock = (FixedClock(_dt.datetime.strptime(args.now, "%Y-%m-%d %H:%M"))
             if args.now else SystemClock())
    db_path = args.db if args.db else settings.db_path

    try:
        store = Store(db_path, exception_text_log=Path("logs/exception_log.txt"))
    except StoreLockedError as e:
        print(f"BỎ QUA LƯỢT: {e}")
        return 1

    notifier = DryRunNotifier()
    image_store = DryRunImageStore()
    try:
        s = run_cycle(scraper, store, notifier, image_store, clock, settings,
                      sleep_fn=_time.sleep if args.real_pace else None)
        store.commit_and_close()
    except Exception:
        store.rollback_and_close()
        raise

    mode = "mock" if (args.mock or args.mock_file) else "site thật"
    print(f"\n=== BÁO ĐƠN — lượt quét {s.at:%Y-%m-%d %H:%M} (DRY-RUN, {mode}) ===")
    if s.aborted:
        print(f"LƯỢT BỊ HỦY: {s.abort_reason} — không xử lý danh sách thiếu.")
        return 1
    print(f"Quét được: {s.scanned} đơn | MỚI: {s.new} | mở lại: {s.reopened}"
          f" | nhắc lại: {s.reminded} | chưa tới mốc: {s.not_due}"
          f" | đóng: {s.closed} | quá hạn: {s.expired}")
    print(f"Hoãn vì QUIET_HOURS: {s.deferred_quiet}"
          f" | thiếu ảnh: {s.skipped_no_image} | lỗi gửi: {s.send_errors}"
          f" | STT trùng: {s.duplicates}")
    if s.skipped_no_image or s.send_errors or s.duplicates:
        print("→ Có ngoại lệ mới, xem logs/exception_log.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
