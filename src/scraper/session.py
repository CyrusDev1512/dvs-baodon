"""Quản lý phiên đăng nhập dashboard — phần KHÔNG phụ thuộc selector.

Vì sao viết được ngay khi chưa có tài khoản: dù cuối cùng chọn transport nào (điều
khiển trình duyệt hay gọi thẳng endpoint nội bộ — xem O5 trong NOTES.md), bước đăng
nhập vẫn phải làm bằng trình duyệt thật vì có CAPTCHA. Cookie thu được dùng lại cho
cả hai hướng.

Cách dùng lần đầu (có CAPTCHA thì tự đăng nhập bằng tay trong cửa sổ hiện ra):

    python -m src.scraper.session --login

Sau đó phiên nằm ở SEVEN_ELEVEN_STORAGE_STATE và các lần chạy sau tự dùng lại.
Kiểm tra phiên còn sống không:

    python -m src.scraper.session --check
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from contextlib import contextmanager
from pathlib import Path

from src.config import Settings, get_settings
from src.scraper.interface import LoginError

# Dấu hiệu "đang ở trang đăng nhập" — neo theo đường dẫn URL, không theo class CSS.
# Điền thêm sau khi biết URL thật (O1); mặc định bắt các từ khoá phổ biến.
LOGIN_URL_HINTS = ("login", "signin", "sign-in", "auth")


def is_login_page(url: str) -> bool:
    """URL hiện tại có phải trang đăng nhập không (tức là phiên đã hết hạn)."""
    low = url.lower()
    return any(h in low for h in LOGIN_URL_HINTS)


def storage_state_age_days(path: Path, now: _dt.datetime | None = None) -> float | None:
    """Phiên đã lưu bao nhiêu ngày rồi; None nếu chưa có file."""
    if not path.exists():
        return None
    now = now or _dt.datetime.now()
    saved = _dt.datetime.fromtimestamp(path.stat().st_mtime)
    return (now - saved).total_seconds() / 86400


@contextmanager
def browser_context(settings: Settings | None = None, headless: bool | None = None):
    """Mở trình duyệt, nạp sẵn phiên đã lưu nếu có. Tự dọn khi thoát.

    Import playwright ở trong hàm để phần backend (Track B) chạy được mà không cần
    cài playwright.
    """
    from playwright.sync_api import sync_playwright

    s = settings or get_settings()
    state = s.seven_eleven_storage_state
    use_headless = s.headless if headless is None else headless

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=use_headless)
        try:
            context = browser.new_context(
                storage_state=str(state) if state.exists() else None
            )
            try:
                yield context
            finally:
                context.close()
        finally:
            browser.close()


def save_state(context, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(path))


def dump_debug(page, reason: str, debug_dir: Path = Path("debug")) -> Path:
    """Lưu HTML + ảnh màn hình để sửa selector nhanh khi parse hỏng."""
    debug_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = debug_dir / f"{stamp}-{reason}"
    base.with_suffix(".html").write_text(page.content(), encoding="utf-8")
    page.screenshot(path=str(base.with_suffix(".png")), full_page=True)
    return base


def login_interactively(settings: Settings | None = None) -> Path:
    """Mở cửa sổ trình duyệt để người tự đăng nhập (kể cả CAPTCHA), rồi lưu phiên."""
    s = settings or get_settings()
    if not s.seven_eleven_url:
        raise LoginError("Chưa đặt SEVEN_ELEVEN_URL trong .env")

    with browser_context(s, headless=False) as context:
        page = context.new_page()
        page.goto(s.seven_eleven_url)
        print("Cửa sổ trình duyệt đã mở.")
        print("→ Đăng nhập bằng tay (kể cả CAPTCHA), mở tới bộ lọc «đơn cần báo».")
        print("→ Xong thì quay lại đây và bấm Enter để lưu phiên.")
        input()
        save_state(context, s.seven_eleven_storage_state)
        print(f"Đã lưu phiên vào {s.seven_eleven_storage_state}")
        print(f"URL cuối cùng (chép vào NOTES.md): {page.url}")
    return s.seven_eleven_storage_state


def check_session(settings: Settings | None = None) -> bool:
    """Phiên đã lưu còn dùng được không (mở trang mà không bị đá về login)."""
    s = settings or get_settings()
    age = storage_state_age_days(s.seven_eleven_storage_state)
    if age is None:
        print("Chưa có phiên nào được lưu — chạy `--login` trước.")
        return False
    print(f"Phiên đã lưu {age:.1f} ngày trước. Đang thử mở dashboard...")

    with browser_context(s) as context:
        page = context.new_page()
        page.goto(s.seven_eleven_url)
        page.wait_for_load_state("networkidle")
        if is_login_page(page.url):
            print(f"Phiên đã hết hạn (bị chuyển về {page.url}) — chạy lại `--login`.")
            return False
        print(f"Phiên còn dùng được. Đang ở: {page.url}")
        return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Quản lý phiên đăng nhập dashboard")
    parser.add_argument("--login", action="store_true",
                        help="Mở trình duyệt để đăng nhập tay rồi lưu phiên")
    parser.add_argument("--check", action="store_true",
                        help="Kiểm tra phiên đã lưu còn dùng được không")
    args = parser.parse_args(argv)

    if args.login:
        login_interactively()
        return 0
    if args.check:
        return 0 if check_session() else 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
