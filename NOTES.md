# NOTES — kết quả khảo sát site thật (myship 7-11)

> Điền file này TRƯỚC khi hiện thực `src/scraper/seven_eleven.py`.
> Câu hỏi gốc: docs/711-scraper-context.md (O1–O6) và docs/DVS-context-01-bao-don.md (Q1–Q9).

## Làm gì trong 30 phút đầu khi có tài khoản

Đã có sẵn 2 công cụ để đỡ phải làm tay — chạy theo thứ tự này:

**Bước 1 — đăng nhập và lưu phiên** (làm một lần, các lần sau tự dùng lại):

```bash
python -m src.scraper.session --login
```

Điền `SEVEN_ELEVEN_URL` trong `.env` trước. Lệnh này mở cửa sổ trình duyệt thật để
bạn đăng nhập bằng tay (kể cả CAPTCHA), rồi lưu phiên vào `.auth/`. Trong lúc làm,
để ý có CAPTCHA/2FA không, CAPTCHA chỉ hiện lúc login hay mỗi lần tra cứu → **ghi O1**.
Kiểm tra phiên còn sống: `python -m src.scraper.session --check`.

**Bước 2 — tự bắt endpoint, trả lời O5** (thay cho việc ngồi đọc DevTools):

```bash
python -m src.scraper.survey
```

Mở bộ lọc `đơn cần báo`, **tải lại trang**, bấm sang trang 2 nếu có, rồi bấm Enter.
Công cụ in ra bảng xếp hạng request nào giống "danh sách đơn" nhất, kèm **tên các
trường** trong đó. Nhìn bảng này là trả lời được luôn:
- Có endpoint JSON không, URL và tham số là gì → **O5**
- Trong danh sách trường có `stt` / tên Sale / mã S không → **O2, O4**
- Có mã định danh cố định cho mỗi dòng không (`CCxxxx`) → **câu 5**
- Nếu công cụ báo "KHÔNG thấy request JSON nào" → bảng nằm trong HTML, phải đọc bằng
  trình duyệt; ghi kết luận đó vào O5.

Bảng in ra chỉ có tên trường, không có giá trị, nên chụp màn hình gửi cho nhau được.
File đầy đủ nằm trong `debug/` và **chứa dữ liệu khách thật** — phải xoá sạch tên,
SĐT, địa chỉ trước khi dùng làm fixture test.

**Bước 3 — những thứ vẫn phải nhìn bằng mắt:**

1. Copy nguyên thanh địa chỉ khi đang ở bộ lọc → mục "Filter" bên dưới (cũng là câu 6:
   myship hay forwarder riêng).
2. Chụp toàn màn hình trang danh sách còn nguyên tên cột; bấm vào một đơn, chụp trang
   chi tiết → xác nhận trường nào chỉ có ở trang chi tiết (**O2**).
3. Tìm nút **xuất file (匯出 / 下載 / Excel / CSV)**, và kiểm tra hộp thư/LINE của tài
   khoản seller xem có thông báo tự động khi hàng tới cửa hàng không → **O6**. Nếu có,
   có thể khỏi cần quét định kỳ.
4. Lướt cuối danh sách xem **kiểu phân trang** (số trang / cuộn vô hạn / nút "xem
   thêm"), đếm một lượt bao nhiêu đơn, bao nhiêu trang.

Sau đó điền các mục dưới, chốt transport, rồi mới code `seven_eleven.py`.

## O1 — Login
- URL login: _(chưa xác nhận)_
- Flow login (username/pass? 2FA?): _(chưa xác nhận)_
- CAPTCHA: chỉ khi login hay mỗi lần tra cứu? _(chưa xác nhận — nếu mỗi lần tra cứu: DỪNG, báo cáo lại, không tự vượt)_

## O2 — Các trường nằm ở đâu
- `STT`, `Sale phụ trách`, `S code` có trên danh sách không, hay phải mở trang chi tiết? _(chưa xác nhận)_
- ⚠️ Theo docs/DVS-context-01-bao-don.md §8: ảnh chụp màn hình myship KHÔNG có các cột nội bộ
  DVS (STT / Sale / ký hiệu nhóm) → nhiều khả năng có 2 nguồn (7-11 + màn hình nội bộ/Sheet).
  Phải chốt trước khi code, không sẽ scrape nhầm site.

## O3 — STT unique?
- STT là duy nhất toàn cục hay lặp lại theo từng Sale? _(chưa xác nhận — báo backend để flip flag)_

## O4 — S code
- Mã `Sxxxx`/`Lxxxx` có hiển thị trên dashboard không? _(chưa xác nhận)_

## O5 — Có endpoint JSON nội bộ không? (F12 → Network → Fetch/XHR)
- URL + method: _(chưa xác nhận)_
- Params (đặc biệt tham số trang và tham số trạng thái): _(chưa)_
- Trường chứa trạng thái giao hàng + giá trị ứng với "đã tới cửa hàng": _(chưa)_
- File mẫu đã lưu (đã xoá dữ liệu khách): _(chưa)_
- Nếu KHÔNG có JSON: bảng nằm sẵn trong HTML đầu tiên hay do JS dựng sau? _(chưa)_

## O6 — Có sẵn đường tắt không?
- Nút xuất file (匯出 / 下載 / Excel / CSV): _(chưa xác nhận)_
- Tài khoản seller có nhận email/LINE khi hàng tới cửa hàng không? _(chưa)_

## Transport đã chọn
- [ ] Đọc endpoint JSON nội bộ (httpx) — nhanh, bền, quét được mỗi 15 phút
- [ ] Điều khiển trình duyệt (Playwright) — chậm, thực tế chỉ 2–4 lượt/ngày
- Lý do chọn: _(điền sau khi có O5/O6)_

## Filter `đơn cần báo`
- Có tồn tại filter lưu sẵn không? Ai tạo, URL trực tiếp là gì? _(chưa xác nhận — Q3)_

## Selector đã chốt
| Mục | Selector | Ghi chú |
|---|---|---|
| Row đơn hàng | _(chưa)_ | neo theo header/aria, không dùng class tự sinh |
| Cột STT | _(chưa)_ | |
| Cột Sale | _(chưa)_ | |
| Pagination | _(chưa)_ | kiểu phân trang: ? |
