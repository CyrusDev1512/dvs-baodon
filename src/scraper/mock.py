"""MockScraper — dữ liệu giả thật-giống để chạy backend khi Track A còn bị chặn.

Khi có tài khoản dashboard, swap trên một dòng trong run_once.py:
MockScraper() -> SevenElevenScraper().
"""
from __future__ import annotations

from src.scraper.interface import (
    BaseScraper,
    OrderToReport,
    ScraperError,
    norm_s_code,
    norm_sale_name,
    norm_stt,
)


def _o(stt: str, sale: str, s_code: str | None = None,
       group: str | None = None, ma_don: str = "") -> OrderToReport:
    """Dựng đơn qua đúng các hàm norm_* của contract (như scraper thật phải làm)."""
    return OrderToReport(
        stt=norm_stt(stt),
        sale_name=norm_sale_name(sale),
        s_code=norm_s_code(s_code),
        group_symbol=group,
        raw={"ma_don": ma_don} if ma_don else {},
    )


def default_orders() -> list[OrderToReport]:
    """~12 đơn mô phỏng một lượt quét thật (50-200 đơn thì cùng cấu trúc, chỉ nhiều
    hơn). Có tên Sale lặp (1 Sale nhiều đơn), STT đệm số 0 (chứng minh không ép
    int), mã đơn CCxxxx nằm trong raw — nơi mã vận đơn thật sẽ ở."""
    return [
        _o(" 1502 ", "Nguyễn  Thu Hà", "s9663", "N15", "CC260801S121101"),
        _o("1503", "Nguyễn Thu Hà", "S9664", "N15", "CC260801S121102"),
        _o("1504", "Trần Minh", "l0821", None, "CC260802S121103"),
        _o("1505", "Lê Thị Bích Ngọc", "S9665", "N7", "CC260802S121104"),
        _o("1506", "Trần Minh", None, "N3", "CC260803S121105"),
        _o("1507", "Phạm Quốc Bảo", "S9666", None, "CC260803S121106"),
        _o("1508", "Nguyễn Thu Hà", "S9667", "N15", "CC260804S121107"),
        _o("1509", "Đỗ Lan Anh", "S9668", "N9", "CC260804S121108"),
        _o("1510", "Lê Thị Bích Ngọc", "S9669", "N7", "CC260805S121109"),
        _o("1511", "Trần Minh", "L0822", None, "CC260805S121110"),
        _o("1512", "Phạm Quốc Bảo", None, "N3", "CC260806S121111"),
        _o("0042", "Đỗ Lan Anh", "S9670", "N9", "CC260806S121112"),
    ]


class MockScraper(BaseScraper):
    def __init__(self, orders: list[OrderToReport] | None = None,
                 error: ScraperError | None = None):
        self.orders = default_orders() if orders is None else orders
        self.error = error

    def fetch_orders_to_report(self) -> list[OrderToReport]:
        if self.error is not None:
            raise self.error
        return list(self.orders)


def build_scraper() -> MockScraper:
    return MockScraper()
