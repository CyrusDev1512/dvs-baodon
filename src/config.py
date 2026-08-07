"""Nguồn cấu hình duy nhất cho cả hai track — đọc từ biến môi trường / file .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv là tiện ích, không bắt buộc khi env đã được set sẵn
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _parse_hhmm(value: str) -> time:
    """'09:00' -> time(9, 0). Sai định dạng thì ValueError ngay lúc khởi động."""
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Giờ không hợp lệ (cần HH:MM): {value!r}")
    return time(int(parts[0]), int(parts[1]))


def _parse_times_csv(value: str) -> tuple[time, ...]:
    """'09:00,14:00' -> (time(9,0), time(14,0)), đã sort."""
    items = [p for p in value.split(",") if p.strip()]
    if not items:
        raise ValueError("REMIND_TIMES rỗng — cần ít nhất một mốc HH:MM")
    return tuple(sorted(_parse_hhmm(p) for p in items))


def _parse_range(value: str) -> tuple[time, time]:
    """'21:00-07:00' -> (time(21,0), time(7,0)). Cho phép qua nửa đêm."""
    parts = value.split("-")
    if len(parts) != 2:
        raise ValueError(f"QUIET_HOURS không hợp lệ (cần HH:MM-HH:MM): {value!r}")
    return _parse_hhmm(parts[0]), _parse_hhmm(parts[1])


@dataclass(frozen=True)
class Settings:
    seven_eleven_url: str
    seven_eleven_user: str
    seven_eleven_pass: str
    seven_eleven_storage_state: Path
    headless: bool
    # Backend báo đơn (bao-don-flow.md §3) — áp dụng chung toàn hệ thống
    scan_interval_minutes: int
    remind_times: tuple[time, ...]
    remind_max_days: int
    quiet_hours: tuple[time, time]
    notify_rate_per_min: int
    db_path: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        seven_eleven_url=os.environ.get("SEVEN_ELEVEN_URL", ""),
        seven_eleven_user=os.environ.get("SEVEN_ELEVEN_USER", ""),
        seven_eleven_pass=os.environ.get("SEVEN_ELEVEN_PASS", ""),
        seven_eleven_storage_state=Path(
            os.environ.get("SEVEN_ELEVEN_STORAGE_STATE", ".auth/711_state.json")
        ),
        headless=os.environ.get("HEADLESS", "true").strip().lower() != "false",
        scan_interval_minutes=int(os.environ.get("SCAN_INTERVAL_MINUTES", "15")),
        remind_times=_parse_times_csv(os.environ.get("REMIND_TIMES", "09:00,14:00")),
        remind_max_days=int(os.environ.get("REMIND_MAX_DAYS", "7")),
        quiet_hours=_parse_range(os.environ.get("QUIET_HOURS", "21:00-07:00")),
        notify_rate_per_min=int(os.environ.get("NOTIFY_RATE_PER_MIN", "10")),
        db_path=Path(os.environ.get("BAODON_DB_PATH", "data/baodon.db")),
    )
