"""Tra sổ ngoại lệ và lịch sử báo đơn — DoD "có log tra được: đơn nào, báo lúc nào,
cho ai, kết quả gì" (DVS-context-01-bao-don.md §10).

Chỉ ĐỌC, mở connection riêng ở chế độ read-only nên chạy song song với một lượt quét
cũng không tranh khoá.

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


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _print_overview(conn: sqlite3.Connection) -> None:
    counts = dict(
        conn.execute("SELECT status, COUNT(*) FROM orders GROUP BY status").fetchall()
    )
    total_notif = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    total_exc = conn.execute("SELECT COUNT(*) FROM exception_log").fetchone()[0]
    print("--- TỔNG QUAN ---")
    print(f"Đơn đang theo dõi: {counts.get('active', 0)}"
          f" | đã đóng: {counts.get('closed', 0)}"
          f" | quá hạn: {counts.get('expired', 0)}")
    print(f"Tin đã gửi: {total_notif} | Ngoại lệ: {total_exc}")


def _print_exceptions(conn: sqlite3.Connection, limit: int) -> None:
    rows = conn.execute(
        "SELECT * FROM exception_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    print(f"\n--- SỔ NGOẠI LỆ ({len(rows)} dòng gần nhất) ---")
    if not rows:
        print("(trống)")
    for r in rows:
        detail = f" — {r['detail']}" if r["detail"] else ""
        print(f"{r['at']} | STT {r['stt'] or '-'} | {r['reason']}{detail}")


def _print_notifications(conn: sqlite3.Connection, limit: int) -> None:
    rows = conn.execute(
        "SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    print(f"\n--- LỊCH SỬ BÁO ĐƠN ({len(rows)} dòng gần nhất) ---")
    if not rows:
        print("(trống)")
    for r in rows:
        print(f"{r['sent_at']} | đơn {r['order_key']} | {r['sale_name']}"
              f" | {r['kind']} | {r['result']}")


def _print_one_order(conn: sqlite3.Connection, stt: str) -> None:
    row = conn.execute("SELECT * FROM orders WHERE stt = ?", (stt,)).fetchone()
    print(f"\n--- ĐƠN STT {stt} ---")
    if row is None:
        print("Không có trong DB.")
        return
    print(f"Sale: {row['sale_name']} | mã S: {row['s_code'] or '-'}"
          f" | trạng thái: {row['status']}")
    print(f"Thấy lần đầu: {row['first_seen_at']} | thấy gần nhất: {row['last_seen_at']}"
          f" | mở lại: {row['reopen_count']} lần")
    print(f"Báo lần đầu: {row['first_notified_at'] or 'chưa'}"
          f" | báo gần nhất: {row['last_notified_at'] or 'chưa'}")
    for r in conn.execute(
        "SELECT * FROM notifications WHERE order_key = ? ORDER BY id",
        (row["order_key"],)
    ):
        print(f"  đã báo {r['sent_at']} | {r['kind']} | {r['result']}")
    for r in conn.execute(
        "SELECT * FROM exception_log WHERE stt = ? ORDER BY id", (stt,)
    ):
        print(f"  ngoại lệ {r['at']} | {r['reason']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tra sổ ngoại lệ & lịch sử báo đơn")
    parser.add_argument("--db", type=Path, help="Đường dẫn SQLite (mặc định theo .env)")
    parser.add_argument("--limit", type=int, default=20, help="Số dòng mỗi bảng")
    parser.add_argument("--exceptions", action="store_true", help="Chỉ sổ ngoại lệ")
    parser.add_argument("--stt", help="Lần theo một đơn cụ thể")
    args = parser.parse_args(argv)

    db_path = args.db if args.db else get_settings().db_path
    if not db_path.exists():
        print(f"Chưa có DB tại {db_path} — chạy `python -m src.run_once --mock` trước.")
        return 1

    conn = _connect(db_path)
    try:
        if args.stt:
            _print_one_order(conn, args.stt)
        elif args.exceptions:
            _print_exceptions(conn, args.limit)
        else:
            _print_overview(conn)
            _print_exceptions(conn, args.limit)
            _print_notifications(conn, args.limit)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
