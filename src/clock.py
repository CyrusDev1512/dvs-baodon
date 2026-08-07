"""Đồng hồ inject được — để logic phụ thuộc giờ (mốc nhắc, quiet hours) test được."""
from __future__ import annotations

import datetime as _dt
from abc import ABC, abstractmethod


class Clock(ABC):
    @abstractmethod
    def now(self) -> _dt.datetime:
        """Giờ hiện tại, naive local (giờ máy = giờ nghiệp vụ, xem .env.example)."""


class SystemClock(Clock):
    def now(self) -> _dt.datetime:
        return _dt.datetime.now()


class FixedClock(Clock):
    """Đứng yên tại một thời điểm — cho demo (--now) và test."""

    def __init__(self, at: _dt.datetime):
        self.at = at

    def now(self) -> _dt.datetime:
        return self.at
