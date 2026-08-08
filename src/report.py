"""Tra sổ ngoại lệ và lịch sử báo đơn — DoD "có log tra được: đơn nào, báo lúc nào,
cho ai, kết quả gì" (DVS-context-01-bao-don.md §10).

Chỉ ĐỌC: mở Store ở chế độ read-only nên không chiếm khoá, chạy song song với một
lượt quét vẫn được. Mọi câu SQL nằm ở src/db.py để khi đổi khoá order_key chỉ phải
sửa một chỗ.

    python -m src.report                  # tổng quan + 20 dòng gần nhất mỗi bảng
    python -m src.report --exceptions     # chỉ sổ ngoại lệ
    python -m src.report --stt 1502       # lần theo một đơn cụ thể
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from src.config import get_settings
from src.db import Store
from src.scraper.interface import norm_stt


def _print_overview(store: Store) -> None:
    counts = store.status_counts()
    print("--- TỔNG QUAN ---")
    print(f"Đơn đang theo dõi: {counts.get('active', 0)}"
          f" | đã đóng: {counts.get('closed', 0)}"
          f" | quá hạn: {counts.get('expired', 0)}")
    print(f"Tin đã gửi: {store.notification_count()}"
          f" | Ngoại lệ: {store.exception_count()}")


def _print_exceptions(store: Store, limit: int) -> None:
    rows = store.recent_exceptions(limit)
    print(f"\n--- SỔ NGOẠI LỆ ({len(rows)} dòng gần nhất) ---")
    if not rows:
        print("(trống)")
    for r in rows:
        detail = f" — {r['detail']}" if r["detail"] else ""
        print(f"{r['at']} | STT {r['stt'] or '-'} | {r['reason']}{detail}")


def _print_notifications(store: Store, limit: int) -> None:
    rows = store.recent_notifications(limit)
    print(f"\n--- LỊCH SỬ BÁO ĐƠN ({len(rows)} dòng gần nhất) ---")
    if not rows:
        print("(trống)")
    for r in rows:
        print(f"{r['sent_at']} | đơn {r['order_key']} | {r['sale_name']}"
              f" | {r['kind']} | {r['result']}")


def _print_one_order(store: Store, stt: str) -> bool:
    """In mọi đơn khớp STT. Trả về False nếu không tìm thấy đơn nào."""
    rows = store.orders_by_stt(stt)
    print(f"\n--- ĐƠN STT {stt} ---")
    if not rows:
        print("Không có trong DB.")
        return False
    if len(rows) > 1:
        print(f"⚠ {len(rows)} đơn cùng STT này (cờ đỏ O3 — STT không unique).")
    for row in rows:
        print(f"\n[khoá {row['order_key']}] Sale: {row['sale_name']}"
              f" | mã S: {row['s_code'] or '-'} | trạng thái: {row['status']}")
        print(f"Thấy lần đầu: {row['first_seen_at']}"
              f" | thấy gần nhất: {row['last_seen_at']}"
              f" | mở lại: {row['reopen_count']} lần")
        print(f"Báo lần đầu: {row['first_notified_at'] or 'chưa'}"
              f" | báo gần nhất: {row['last_notified_at'] or 'chưa'}")
        for r in store.notifications_for(row["order_key"]):
            print(f"  đã báo {r['sent_at']} | {r['kind']} | {r['result']}")
    for r in store.exceptions_for_stt(stt):
        print(f"  ngoại lệ {r['at']} | {r['reason']}")
    return True


def main(argv: list[str] | None = None) -> int:
    # Tiếng Việt phải ra được cả khi stdout bị chuyển hướng vào file/Task Scheduler.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description="Tra sổ ngoại lệ & lịch sử báo đơn")
    parser.add_argument("--db", type=Path, help="Đường dẫn SQLite (mặc định theo .env)")
    parser.add_argument("--limit", type=int, default=20, help="Số dòng mỗi bảng")
    parser.add_argument("--exceptions", action="store_true", help="Chỉ sổ ngoại lệ")
    parser.add_argument("--stt", help="Lần theo một đơn cụ thể")
    args = parser.parse_args(argv)

    limit = max(1, args.limit)
    db_path = args.db if args.db else get_settings().db_path
    if not db_path.exists():
        print(f"Chưa có DB tại {db_path} — chạy `python -m src.run_once --mock` trước.")
        return 1

    try:
        store = Store(db_path, readonly=True)
    except sqlite3.Error as e:
        print(f"Không đọc được DB tại {db_path}: {e}")
        return 1

    try:
        if args.stt:
            found = _print_one_order(store, norm_stt(args.stt))
            return 0 if found else 1
        if args.exceptions:
            _print_exceptions(store, limit)
        else:
            _print_overview(store)
            _print_exceptions(store, limit)
            _print_notifications(store, limit)
    except sqlite3.Error as e:
        print(f"Lỗi đọc DB ({db_path}): {e}")
        return 1
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
