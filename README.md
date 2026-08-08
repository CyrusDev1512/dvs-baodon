# DVS — Báo đơn

Tự động hoá nghiệp vụ **Báo đơn**: phát hiện đơn đã tới cửa hàng 7-Eleven (khách chưa
lấy) và nhắc Sale phụ trách. Gồm 2 track trong cùng repo:
- **Track A** — bộ đọc dữ liệu dashboard vận đơn (`src/scraper/`) — **đang chặn: chưa có tài khoản**
- **Track B** — backend reconcile + gửi tin (`src/reconcile.py` & đồng bọn) — **đã chạy được với mock**

## Đọc gì trước

1. `docs/DVS-context-01-bao-don.md` — nghiệp vụ Báo đơn (nguồn sự thật, cái gì & tại sao)
2. `docs/711-scraper-context.md` — spec kỹ thuật Track A, hợp đồng `OrderToReport`
3. `NOTES.md` — kết quả khảo sát site thật (O1–O6, gồm cả việc chốt transport).
   **Chưa điền xong thì chưa code scraper.**

## Cấu trúc

```
src/
  config.py               # get_settings() — nguồn cấu hình duy nhất (.env)
  clock.py                # Clock inject được (SystemClock / FixedClock)
  rules.py                # quy tắc thuần: order_key, quiet hours, mốc nhắc, quá hạn
  db.py                   # SQLite: trạng thái đơn + audit gửi + sổ ngoại lệ
  notify.py               # Notifier/ImageStore ABC + bản DryRun + RateLimiter
  message.py              # soạn nội dung tin gửi Sale
  sale_directory.py       # tra tên Sale → link Messenger (danh bạ CSV)
  report.py               # CLI tra sổ ngoại lệ & lịch sử báo đơn
  reconcile.py            # run_cycle() — 4 quy tắc gửi, trái tim Track B
  run_once.py             # CLI: chạy 1 lượt rồi thoát (lên lịch bằng Task Scheduler)
  scraper/
    interface.py          # HỢP ĐỒNG giữa 2 track — không sửa
    seven_eleven.py       # SevenElevenScraper (skeleton, chờ tài khoản + O1-O6)
    mock.py               # MockScraper — dữ liệu giả để chạy Track B ngay
tests/                    # 40+ test: rules/db/notify/reconcile/e2e timeline
docs/                     # context nghiệp vụ + flow + dashboard kế hoạch
data/, logs/              # SQLite + sổ ngoại lệ dạng text (không commit)
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

## Chạy Track B ngay (không cần tài khoản dashboard)

```bash
python -m src.run_once --mock                          # 1 lượt trọn vẹn, dry-run
python -m src.run_once --mock --now "2026-08-07 09:05" # demo mốc nhắc 09:00
python -m src.run_once --mock --sales sales.example.csv # kèm danh bạ Sale
pytest                                                 # toàn bộ test
```

Chạy lần 1 → 12 đơn MỚI được "gửi" (in `[DRY-RUN] GỬI ...`). Chạy lại cùng giờ →
"chưa tới mốc" (chống báo trùng). `--now` lùi về 21:30 → "hoãn vì QUIET_HOURS".
Khi có tài khoản, swap `MockScraper()` → `SevenElevenScraper()` trong `run_once.py`.

Chưa có gì gửi thật: `DryRunNotifier`/`DryRunImageStore` chỉ in ra — kênh Messenger
an toàn và khoá tra ảnh bot Telegram là 2 quyết định còn chờ.

### Danh bạ Sale (gửi cho ai)

Dashboard chỉ cho biết *tên* Sale; gửi vào đâu thì tra trong danh bạ — xuất Google
Sheet ra CSV với các cột `sale_name`, `messenger_link`, tuỳ chọn `aliases` (các cách
viết khác, phân cách `;`) và `note`. Xem mẫu `sales.example.csv`; trỏ đường dẫn thật
qua `SALE_DIRECTORY_PATH` trong `.env` (file thật chứa link cá nhân nên không commit).

Khớp tên chịu được lệch hoa/thường, thừa khoảng trắng, và **thiếu dấu tiếng Việt** —
nhưng chỉ khi ra đúng một người. Nếu Sale chưa có trong danh bạ, hoặc tên khớp với
nhiều người (kể cả do bỏ dấu mà «Hà» lẫn với «Hạ»), hệ thống **không đoán**: bỏ qua
đơn đó và ghi sổ ngoại lệ. Đơn vẫn giữ trạng thái chưa báo nên sẽ tự gửi ở lượt sau
khi danh bạ được bổ sung.

### Tra sổ ngoại lệ & lịch sử báo đơn

```bash
python -m src.report                # tổng quan + ngoại lệ + tin đã gửi gần nhất
python -m src.report --exceptions   # chỉ sổ ngoại lệ
python -m src.report --stt 1502     # lần theo một đơn: thấy lúc nào, báo mấy lần
```

Chỉ đọc (read-only), chạy được cả khi một lượt quét đang diễn ra.

## Lên lịch chạy (khi Track A xong)

Cố ý KHÔNG viết daemon: mỗi lượt là một tiến trình chạy rồi thoát, trạng thái nằm hết
trong SQLite nên lượt bị lỡ tự bù ở lượt sau, và khoá DB chặn hai lượt chạy chồng.
Lên lịch bằng Windows Task Scheduler:

```powershell
schtasks /create /tn "DVS-baodon" /sc minute /mo 15 ^
  /tr "D:\DVS-baodon\.venv\Scripts\python.exe -m src.run_once" /st 07:00
```

Tiến trình trả exit code 1 khi lượt bị hủy (đọc dashboard lỗi / DB đang khoá) để Task
Scheduler đánh dấu thất bại. Ngoài `QUIET_HOURS` hệ thống tự im lặng nên không cần
lịch riêng cho ban đêm.

## Chạy Track A (khi có tài khoản)

```bash
python -m src.scraper.session --login       # đăng nhập tay 1 lần, lưu phiên
python -m src.scraper.session --check       # phiên còn dùng được không
python -m src.scraper.survey                # tự bắt endpoint JSON → trả lời O5
python -m src.scraper.seven_eleven --dry-run  # (sau khi code xong) in đơn ra JSON
```

`session --login` mở trình duyệt thật để đăng nhập bằng tay (kể cả CAPTCHA) rồi lưu
`.auth/711_state.json`; các lần sau chạy headless bằng phiên đó.

`survey` ghi lại mọi request nền trong lúc bạn duyệt dashboard, rồi chỉ ra request nào
giống "danh sách đơn" nhất kèm tên các trường — thay cho việc đọc DevTools bằng mắt.
Bảng in ra chỉ có tên trường (an toàn để chụp gửi); file đầy đủ trong `debug/` **chứa
dữ liệu khách thật**, phải xoá sạch trước khi dùng làm fixture. Chi tiết: `NOTES.md`.

## Nguyên tắc bất di bất dịch

- **Chỉ đọc, không ghi** lên dashboard 7-11 — không bấm nút tạo/sửa/xoá.
- **Không tự nhắn khách** — hệ thống chỉ báo nội bộ cho Sale.
- **Thà không báo còn hơn báo sai** — đọc không hết danh sách thì raise, không trả thiếu.
- Gặp CAPTCHA ở mỗi lần tra cứu (không chỉ login) → **dừng và báo cáo**, không tự vượt.
