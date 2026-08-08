"""Tầng lưu trữ SQLite — trạng thái đơn, audit gửi tin, sổ ngoại lệ.

Toàn bộ timestamp là ISO-8601 naive local (giờ máy = giờ nghiệp vụ, xem .env.example).
Đổi khoá order_key sau này: sửa rules.order_key() + script UPDATE gác bằng
PRAGMA user_version=2.
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
  order_key         TEXT PRIMARY KEY,
  stt               TEXT NOT NULL,
  sale_name         TEXT NOT NULL,
  s_code            TEXT,
  group_symbol      TEXT,
  status            TEXT NOT NULL DEFAULT 'active',
  created_at        TEXT NOT NULL,
  first_seen_at     TEXT NOT NULL,
  last_seen_at      TEXT NOT NULL,
  first_notified_at TEXT,
  last_notified_at  TEXT,
  closed_at         TEXT,
  reopen_count      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notifications (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  order_key TEXT NOT NULL,
  kind      TEXT NOT NULL,
  sent_at   TEXT NOT NULL,
  sale_name TEXT NOT NULL,
  result    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exception_log (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  at     TEXT NOT NULL,
  stt    TEXT,
  reason TEXT NOT NULL,
  detail TEXT
);
"""


def _iso(t: _dt.datetime) -> str:
    return t.isoformat(sep=" ", timespec="seconds")


def parse_ts(value: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(value)


class StoreLockedError(Exception):
    """Một lượt khác đang chạy trên cùng DB — thoát êm, không chạy chồng."""


class Store:
    """CRUD trạng thái đơn.

    Mở ở chế độ ghi = chiếm khoá (BEGIN IMMEDIATE) cho cả lượt, chống hai lượt
    chạy chồng. Mở `readonly=True` (dùng cho lệnh tra sổ) thì không chiếm khoá và
    không tạo file mới — nhờ WAL nên đọc được ngay cả khi một lượt đang ghi.
    """

    def __init__(self, db_path: Path, exception_text_log: Path | None = None,
                 readonly: bool = False):
        self.readonly = readonly
        if readonly:
            uri = db_path.resolve().as_uri() + "?mode=ro"
            self._conn = sqlite3.connect(uri, uri=True)
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._exc_text = exception_text_log
        if readonly:
            return
        self._conn.execute("PRAGMA journal_mode = WAL")  # đọc không chặn ghi
        self._init_schema()
        try:
            self._conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as e:
            raise StoreLockedError("Một lượt khác đang chạy trên cùng DB") from e

    def _init_schema(self) -> None:
        version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            self._conn.executescript(_SCHEMA)
            self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def commit_and_close(self) -> None:
        self._conn.execute("COMMIT")
        self._conn.close()

    def rollback_and_close(self) -> None:
        self._conn.execute("ROLLBACK")
        self._conn.close()

    def close(self) -> None:
        self._conn.close()

    # --- orders ---

    def get_all(self) -> dict[str, sqlite3.Row]:
        rows = self._conn.execute("SELECT * FROM orders").fetchall()
        return {r["order_key"]: r for r in rows}

    def insert_order(self, key: str, order, now: _dt.datetime) -> None:
        self._conn.execute(
            "INSERT INTO orders (order_key, stt, sale_name, s_code, group_symbol,"
            " status, created_at, first_seen_at, last_seen_at)"
            " VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)",
            (key, order.stt, order.sale_name, order.s_code, order.group_symbol,
             _iso(now), _iso(now), _iso(now)),
        )

    def touch_seen(self, key: str, now: _dt.datetime) -> None:
        self._conn.execute(
            "UPDATE orders SET last_seen_at = ? WHERE order_key = ?", (_iso(now), key)
        )

    def close_order(self, key: str, now: _dt.datetime) -> None:
        self._conn.execute(
            "UPDATE orders SET status = 'closed', closed_at = ? WHERE order_key = ?",
            (_iso(now), key),
        )

    def expire_order(self, key: str) -> None:
        self._conn.execute(
            "UPDATE orders SET status = 'expired' WHERE order_key = ?", (key,)
        )

    def reopen_order(self, key: str, now: _dt.datetime) -> None:
        """Đơn đã đóng quay lại bộ lọc: mở lại, reset đồng hồ REMIND_MAX_DAYS,
        xoá dấu đã-báo để được báo lại ngay (quyết định nghiệp vụ 07/08/2026)."""
        self._conn.execute(
            "UPDATE orders SET status = 'active', reopen_count = reopen_count + 1,"
            " first_seen_at = ?, last_seen_at = ?, closed_at = NULL,"
            " first_notified_at = NULL, last_notified_at = NULL"
            " WHERE order_key = ?",
            (_iso(now), _iso(now), key),
        )

    def mark_notified(self, key: str, kind: str, sale_name: str,
                      now: _dt.datetime, result: str) -> None:
        self._conn.execute(
            "UPDATE orders SET last_notified_at = ?,"
            " first_notified_at = COALESCE(first_notified_at, ?)"
            " WHERE order_key = ?",
            (_iso(now), _iso(now), key),
        )
        self._conn.execute(
            "INSERT INTO notifications (order_key, kind, sent_at, sale_name, result)"
            " VALUES (?, ?, ?, ?, ?)",
            (key, kind, _iso(now), sale_name, result),
        )

    # --- sổ ngoại lệ ---

    def log_exception(self, now: _dt.datetime, stt: str | None,
                      reason: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO exception_log (at, stt, reason, detail) VALUES (?, ?, ?, ?)",
            (_iso(now), stt, reason, detail),
        )
        if self._exc_text is not None:
            self._exc_text.parent.mkdir(parents=True, exist_ok=True)
            with self._exc_text.open("a", encoding="utf-8") as f:
                f.write(f"{_iso(now)} | STT {stt or '-'} | {reason}"
                        f"{' | ' + detail if detail else ''}\n")

    def exception_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM exception_log").fetchone()[0]

    def notifications_for(self, key: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM notifications WHERE order_key = ? ORDER BY id", (key,)
        ).fetchall()

    # --- truy vấn cho lệnh tra sổ (src/report.py) ---
    # Để SQL nằm hết ở đây: khi đổi khoá order_key (user_version 2) chỉ sửa một file.

    def status_counts(self) -> dict[str, int]:
        return dict(
            self._conn.execute(
                "SELECT status, COUNT(*) FROM orders GROUP BY status"
            ).fetchall()
        )

    def notification_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]

    def recent_exceptions(self, limit: int) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM exception_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    def recent_notifications(self, limit: int) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    def orders_by_stt(self, stt: str) -> list[sqlite3.Row]:
        """Trả về TẤT CẢ đơn khớp STT — không dùng fetchone, vì STT chưa chắc
        unique (cờ đỏ O3) và sau khi đổi khoá thì một STT có thể ra nhiều dòng."""
        return self._conn.execute(
            "SELECT * FROM orders WHERE stt = ? ORDER BY order_key", (stt,)
        ).fetchall()

    def exceptions_for_stt(self, stt: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM exception_log WHERE stt = ? ORDER BY id", (stt,)
        ).fetchall()
