# NOTES — kết quả khảo sát site thật (myship 7-11)

> Điền file này TRƯỚC khi hiện thực `src/scraper/seven_eleven.py`.
> Câu hỏi gốc: docs/711-scraper-context.md (O1–O6) và docs/DVS-context-01-bao-don.md (Q1–Q9).

## Làm gì trong 30 phút đầu khi có tài khoản

Làm đúng thứ tự dưới đây rồi điền các mục O1–O6; xong là code scraper được ngay.

1. **Đăng nhập bằng tay**, để ý có CAPTCHA/2FA không → ghi O1. Copy URL trang login.
2. Mở **bộ lọc `đơn cần báo`**, copy nguyên thanh địa chỉ → ghi vào mục "Filter" bên dưới.
   Đây cũng là câu trả lời cho câu 6 (myship hay forwarder riêng).
3. **Chụp toàn màn hình trang danh sách** (còn nguyên tên cột). Đối chiếu: có cột STT /
   Sale phụ trách / ký hiệu nhóm / mã S không → ghi O2, O4. Có mã dòng cố định
   (`CCxxxx`) không → câu 5.
4. Bấm vào **một đơn**, chụp trang chi tiết → xác nhận trường nào chỉ có ở đây (O2).
5. Nhấn **F12 → tab Network → lọc Fetch/XHR → F5 tải lại trang danh sách**. Có request
   trả JSON chứa các dòng đơn không?
   - Có → copy URL + method + params, lưu một response mẫu (xoá tên/SĐT/địa chỉ khách
     trước khi commit) vào `tests/fixtures/orders_sample.json` → ghi O5. **Đây là
     đường nhanh và bền hơn nhiều so với đọc HTML.**
   - Không → chuột phải trang → "Save as" HTML, xoá dữ liệu khách, lưu
     `tests/fixtures/dashboard_sample.html`.
6. Tìm nút **xuất file (匯出 / 下載 / Excel / CSV)** và kiểm tra hộp thư/LINE của tài
   khoản seller xem có thông báo tự động khi hàng tới cửa hàng không → ghi O6. Nếu có,
   có thể khỏi cần quét định kỳ.
7. Lướt xuống cuối danh sách xem **kiểu phân trang** (số trang / cuộn vô hạn / nút "xem
   thêm") và đếm xem một lượt có bao nhiêu đơn, bao nhiêu trang.

Sau đó điền các mục dưới, rồi chạy `python -m src.scraper.seven_eleven --dry-run`.

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
