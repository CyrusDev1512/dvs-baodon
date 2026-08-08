"""SevenElevenScraper — đọc filter `đơn cần báo` trên dashboard myship 7-11.

Skeleton dựng theo docs/711-scraper-context.md. Các chỗ đánh dấu TODO(O1)..TODO(O4)
chỉ điền được sau khi khảo sát site thật và ghi kết quả vào NOTES.md.

Chạy thử:  python -m src.scraper.seven_eleven --dry-run
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import json
import sys

from src.config import get_settings
from src.scraper.interface import (
    BaseScraper,
    CaptchaError,
    LoginError,
    OrderToReport,
    ParseError,
    norm_s_code,
    norm_sale_name,
    norm_stt,
)

# TODO(O1): URL login + URL của filter `đơn cần báo` — xác nhận trên site thật.
FILTER_URL = ""  # ví dụ: https://myship.7-11.com.tw/seller/order?... — chưa xác nhận

# TODO(O2): selector hàng/cột — neo theo header cột / aria-role / text,
# KHÔNG neo theo class CSS tự sinh. Ghi selector đã chốt vào NOTES.md.
ROW_SELECTOR = ""


class SevenElevenScraper(BaseScraper):
    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch_orders_to_report(self) -> list[OrderToReport]:
        """Đăng nhập (ưu tiên storage_state đã lưu), mở filter, đọc HẾT các trang."""
        # TODO: hiện thực bằng Playwright sync API theo trình tự:
        #   1. Mở browser (headless theo settings), load storage_state nếu có.
        #   2. Vào FILTER_URL; nếu bị đá về trang login -> login lại;
        #      gặp CAPTCHA -> raise CaptchaError (không tự vượt).
        #   3. Đọc từng trang (theo pagination), parse từng row -> OrderToReport
        #      dùng norm_stt / norm_sale_name / norm_s_code.
        #   4. Parse lỗi -> lưu HTML + screenshot vào debug/ rồi raise ParseError.
        #   5. Trả về đủ toàn bộ danh sách; thiếu là raise, không trả thiếu.
        raise NotImplementedError(
            "Chưa khảo sát site thật — điền O1-O6 và chốt transport trong NOTES.md"
            " trước (O5: có endpoint JSON nội bộ không, quyết định tần suất quét)."
        )

    def _save_debug(self, html: str, screenshot: bytes) -> None:
        from pathlib import Path

        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        debug_dir = Path("debug")
        debug_dir.mkdir(exist_ok=True)
        (debug_dir / f"{stamp}.html").write_text(html, encoding="utf-8")
        (debug_dir / f"{stamp}.png").write_bytes(screenshot)


def build_scraper() -> SevenElevenScraper:
    """Factory để backend swap MockScraper() -> SevenElevenScraper() trên một dòng."""
    return SevenElevenScraper()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="711 dashboard scraper")
    parser.add_argument("--dry-run", action="store_true", help="In danh sách đơn ra JSON")
    args = parser.parse_args(argv)

    if not args.dry_run:
        parser.print_help()
        return 0

    orders = build_scraper().fetch_orders_to_report()
    print(json.dumps([dataclasses.asdict(o) for o in orders], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
