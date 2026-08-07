"""Contract giữa Track A (scraper) và Track B (backend).

KHÔNG SỬA FILE NÀY. Backend import BaseScraper/OrderToReport từ đây;
mọi thay đổi phải được cả hai bên thống nhất qua docs/711-scraper-context.md.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ScraperError(Exception):
    """Lỗi gốc của scraper."""


class LoginError(ScraperError):
    """Không đăng nhập được vào dashboard."""


class CaptchaError(ScraperError):
    """Gặp CAPTCHA cần người xử lý — dừng lại, không tự vượt."""


class ParseError(ScraperError):
    """Đọc/parse trang thất bại — không được trả danh sách thiếu."""


def norm_stt(value: str) -> str:
    """Giữ nguyên như hiển thị, chỉ trim. KHÔNG BAO GIỜ ép về int."""
    return value.strip()


def norm_sale_name(value: str) -> str:
    """Trim + gộp khoảng trắng bên trong, giữ nguyên hoa/thường."""
    return " ".join(value.split())


def norm_s_code(value: str | None) -> str | None:
    """Trim + uppercase; chuỗi rỗng coi như không có."""
    if value is None:
        return None
    v = value.strip().upper()
    return v or None


@dataclass(frozen=True)
class OrderToReport:
    stt: str                            # khoá nối BẮT BUỘC, đã qua norm_stt
    sale_name: str                      # "Sale phụ trách" BẮT BUỘC, đã qua norm_sale_name
    s_code: str | None = None           # "Sxxxx"/"Lxxxx" nếu có trên danh sách
    group_symbol: str | None = None     # "Ký hiệu nhóm" nếu có trên danh sách
    raw: dict = field(default_factory=dict, compare=False)  # cột thừa, chỉ để debug


class BaseScraper(ABC):
    @abstractmethod
    def fetch_orders_to_report(self) -> list[OrderToReport]:
        """Trả về TOÀN BỘ đơn trong filter `đơn cần báo`.

        - Read-only, idempotent.
        - Thất bại thì raise LoginError/CaptchaError/ParseError,
          không bao giờ trả danh sách thiếu một cách im lặng.
        """
