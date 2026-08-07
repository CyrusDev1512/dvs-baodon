"""Nguồn cấu hình duy nhất cho cả hai track — đọc từ biến môi trường / file .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv là tiện ích, không bắt buộc khi env đã được set sẵn
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    seven_eleven_url: str
    seven_eleven_user: str
    seven_eleven_pass: str
    seven_eleven_storage_state: Path
    headless: bool


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
    )
