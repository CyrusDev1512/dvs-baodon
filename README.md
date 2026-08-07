# DVS — Báo đơn (Track A: 711 Dashboard Scraper)

Scraper Playwright đọc filter **`đơn cần báo`** trên dashboard 7-Eleven Đài Loan (myship),
trả về danh sách `OrderToReport` cho backend (bot Telegram / reconcile loop — Track B, repo khác).

## Đọc gì trước

1. `docs/DVS-context-01-bao-don.md` — nghiệp vụ Báo đơn (nguồn sự thật, cái gì & tại sao)
2. `docs/711-scraper-context.md` — spec kỹ thuật Track A, hợp đồng `OrderToReport`
3. `NOTES.md` — kết quả khảo sát site thật (O1–O4). **Chưa điền xong thì chưa code scraper.**

## Cấu trúc

```
src/
  config.py               # get_settings() — nguồn cấu hình duy nhất (.env)
  scraper/
    interface.py          # HỢP ĐỒNG với backend — không sửa
    seven_eleven.py       # SevenElevenScraper (skeleton, chờ O1-O4)
tests/
  test_interface.py       # test normalization, chạy được ngay
  test_seven_eleven_offline.py  # test parse fixture (skip khi chưa có fixture)
  fixtures/               # dashboard_sample.html (sanitized) sẽ lưu ở đây
docs/                     # 2 file context + ảnh chụp dashboard
debug/                    # HTML/screenshot khi ParseError (không commit)
.auth/                    # Playwright storage_state (không commit)
```

## Setup

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
python -m playwright install chromium            # idempotent
cp .env.example .env                             # rồi điền credential
```

## Chạy

```bash
python -m src.scraper.seven_eleven --dry-run     # in danh sách đơn ra JSON
pytest                                           # test offline
```

Lần chạy đầu: đặt `HEADLESS=false`, login tay (nếu có CAPTCHA), session được lưu vào
`.auth/711_state.json` để các lần sau chạy headless.

## Nguyên tắc bất di bất dịch

- **Chỉ đọc, không ghi** lên dashboard 7-11 — không bấm nút tạo/sửa/xoá.
- **Không tự nhắn khách** — hệ thống chỉ báo nội bộ cho Sale.
- **Thà không báo còn hơn báo sai** — đọc không hết danh sách thì raise, không trả thiếu.
- Gặp CAPTCHA ở mỗi lần tra cứu (không chỉ login) → **dừng và báo cáo**, không tự vượt.
