# NOTES — kết quả khảo sát site thật (myship 7-11)

> Điền file này TRƯỚC khi hiện thực `src/scraper/seven_eleven.py`.
> Câu hỏi gốc: docs/711-scraper-context.md (O1–O4) và docs/DVS-context-01-bao-don.md (Q1–Q9).

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

## Filter `đơn cần báo`
- Có tồn tại filter lưu sẵn không? Ai tạo, URL trực tiếp là gì? _(chưa xác nhận — Q3)_

## Selector đã chốt
| Mục | Selector | Ghi chú |
|---|---|---|
| Row đơn hàng | _(chưa)_ | neo theo header/aria, không dùng class tự sinh |
| Cột STT | _(chưa)_ | |
| Cột Sale | _(chưa)_ | |
| Pagination | _(chưa)_ | kiểu phân trang: ? |
