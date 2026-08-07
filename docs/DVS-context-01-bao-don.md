# DVS — Context #01: Báo đơn

> **Trạng thái:** DRAFT v0.1 — chờ CEO / trưởng bộ phận xác nhận phần §8 và §9.
> **Phạm vi:** chỉ nghiệp vụ **Báo đơn**. Các nghiệp vụ khác (chốt đơn, đối soát tiền,
> hoàn hàng, kho) sẽ có file context riêng.

---

## 0. Cách dùng file này

File này là **nguồn sự thật chung** về nghiệp vụ Báo đơn: bất kỳ ai (người hoặc AI) nhận
task liên quan đến báo đơn đều đọc file này trước, và mọi tài liệu kỹ thuật (ví dụ
`711-scraper-context.md`) đều phải **không mâu thuẫn** với file này.

Quy tắc: file này mô tả **nghiệp vụ** (cái gì, tại sao, ai làm, khi nào). Nó **không**
mô tả cách code. Chi tiết kỹ thuật nằm ở các file context con.

---

## 1. Bối cảnh công ty

- **DVS** kinh doanh **đa mặt hàng**, bán cho khách hàng **ở nhiều quốc gia**.
- Kênh giao tiếp với khách: **Meta Business Suite (MBS)** và **Pancake** (CRM/chat
  hợp nhất inbox Facebook/Instagram). Sale trả lời khách trên 2 nền tảng này.
- Luồng hàng (thị trường đang xét trong file này): hàng được gửi qua hệ thống
  **7-Eleven Đài Loan — 賣貨便 / myship** (`myship.7-11.com.tw/seller/order`). Khách
  **không nhận tại nhà**, khách **ra cửa hàng 7-Eleven lấy hàng**.
- Vì khách phải tự ra cửa hàng lấy, nên **bắt buộc phải có người báo cho khách biết
  hàng đã tới cửa hàng**. Đó chính là nghiệp vụ **Báo đơn**.

---

## 2. Các vai trò

| Vai trò | Làm gì trong nghiệp vụ báo đơn |
|---|---|
| **Sale** | Chốt đơn, giữ quan hệ với khách, nhắn khách qua MBS/Pancake. Là người **cuối cùng** nói chuyện với khách. |
| **Nhân viên báo đơn** | Mở dashboard 7-11/forwarder, nhìn **thanh tiến độ** của từng đơn, phát hiện đơn đã tới cửa hàng, rồi **báo cho Sale phụ trách đơn đó**. |
| **Khách hàng** | Ra cửa hàng 7-Eleven lấy hàng trong thời hạn quy định. |
| **Bot Telegram** (đã có, do người khác làm) | Khi Sale đăng đơn, bot lưu lại ảnh chụp màn hình của khách, gắn theo **mã đơn**. |

**Điểm mấu chốt:** nhân viên báo đơn **không** liên hệ khách trực tiếp. Họ báo Sale,
Sale mới báo khách. Mọi thiết kế tự động hoá phải giữ đúng chuỗi này trừ khi CEO đổi ý.

---

## 3. Quy trình hiện tại (AS-IS — đang làm thủ công)

1. Sale chốt đơn với khách trên MBS/Pancake → đơn được tạo trên hệ thống vận chuyển.
2. Sale đăng đơn lên nhóm Telegram → bot lưu ảnh chụp màn hình + mã đơn.
3. Nhân viên báo đơn mở dashboard, lọc/duyệt danh sách đơn.
4. Với **từng đơn**, nhân viên nhìn **thanh tiến độ** (xem §4). Khi thanh chạy tới mốc
   "hàng đã tới nơi" → đơn này **cần báo**.
5. Nhân viên nhắn cho Sale phụ trách: "đơn STT/mã X của em tới rồi".
6. Sale nhắn khách qua MBS/Pancake: mời khách ra cửa hàng lấy hàng.
7. Khách ra lấy → thanh tiến độ nhảy sang mốc cuối → đơn **hết cần báo**.

### Vấn đề của cách làm hiện tại
- Phải **nhìn bằng mắt** từng thanh tiến độ, nhiều trang, dễ sót đơn.
- Phải làm lặp lại **nhiều lần trong ngày** (hàng về rải rác trong ngày).
- Không có bằng chứng "đơn này đã báo lúc mấy giờ" → dễ báo trùng hoặc bỏ quên.
- Hàng có **hạn lưu tại cửa hàng**; báo trễ = khách không kịp lấy = hàng bị trả về.

---

## 4. Tín hiệu "cần báo" — định nghĩa chính xác

Trên dashboard, mỗi đơn có một **thanh tiến độ 5 mốc** (nhãn hiển thị là bản dịch tự
động của trình duyệt, chữ gốc là tiếng Trung):

| # | Mốc (bản dịch trên màn hình) | Ý nghĩa | Ví dụ trong ảnh |
|---|---|---|---|
| 1 | Đơn hàng đã được đặt | Đơn được tạo | 25/07 17:00 |
| 2 | Tích trữ / chuẩn bị hàng | Người bán đang soạn hàng | 25/07 17:15 |
| 3 | Hàng đã được gửi | Đã bàn giao cho vận chuyển | 27/07 06:18 |
| 4 | **Đã giao hàng (tới cửa hàng)** | **Hàng đã tới cửa hàng 7-11, chờ khách lấy** | 27/07 06:18 |
| 5 | Giao hàng đã nhận / Đơn nhận | Khách **đã lấy** hàng (trong ảnh: chấm màu xám = chưa xảy ra) | — |

**Định nghĩa nghiệp vụ:**
- **CẦN BÁO** = đã đạt **mốc 4** và **chưa đạt mốc 5**.
- Đạt **mốc 5** = khách đã lấy hàng → **không báo nữa**, và nếu đã báo thì đóng lại.

> ⚠️ **Điểm cần CEO/nghiệp vụ xác nhận (Q1):** câu mô tả ban đầu là "thanh tiến độ chạy
> đến cuối là biết đơn được giao thành công". Nếu "đến cuối" nghĩa là **mốc 5**, thì lúc
> đó khách **đã cầm hàng rồi** → báo cho Sale không còn tác dụng nhắc khách đi lấy.
> Theo ảnh chụp, đơn đang nằm ở **mốc 4** (4 chấm cam, chấm 5 xám) — đây mới là lúc phải
> báo. File này đang tạm chốt theo **mốc 4**. Cần xác nhận trước khi code.

---

## 5. Dữ liệu tối thiểu của một "đơn cần báo"

Mỗi đơn khi đưa vào hệ thống báo đơn phải mang được các trường sau:

| Trường | Ý nghĩa | Bắt buộc | Nguồn |
|---|---|---|---|
| `stt` | Số thứ tự / khoá nối giữa dashboard và bot Telegram | ✅ | Dashboard |
| `sale_name` | Sale phụ trách — **người sẽ nhận thông báo** | ✅ | Dashboard |
| `ma_don` | Mã đơn vận chuyển (VD `CC240721S121117`) | ✅ | Dashboard |
| `s_code` | Mã `Sxxxx` / `Lxxxx` nội bộ (nếu có hiển thị) | ⬜ | Dashboard |
| `group_symbol` | Ký hiệu nhóm (nếu có hiển thị) | ⬜ | Dashboard |
| `thoi_diem_toi_cua_hang` | Timestamp mốc 4 → dùng để tính "đã tới bao lâu" | ⬜ | Dashboard |
| `han_lay_hang` | Hạn khách phải ra lấy (VD `2024-08-03` trên ảnh) | ⬜ | Dashboard |
| `kenh_chat` | MBS hay Pancake — để Sale biết mở đâu | ⬜ | CRM / Sale |
| `da_bao_luc` | Đã báo Sale lúc nào (chống báo trùng) | ✅ | Hệ thống tự sinh |

`stt` + `sale_name` là **hai trường không được thiếu** — thiếu là không biết báo cho ai,
báo đơn nào.

---

## 6. Mục tiêu tự động hoá (TO-BE)

Thay bước 3–5 của §3 bằng một vòng lặp tự động chạy **vài lần mỗi ngày**:

```
[Dashboard 7-11/forwarder]
        │  (đọc danh sách đơn ở trạng thái "đã tới cửa hàng, chưa lấy")
        ▼
   Bộ đọc dữ liệu  ──► danh sách OrderToReport
        ▼
   Reconcile loop  ──► so với DB: đơn nào MỚI cần báo? đơn nào đã báo rồi? đơn nào đã lấy?
        ▼
   Notifier  ──► nhắn Sale phụ trách (Telegram) kèm ảnh khách đã lưu theo mã đơn
        ▼
   Sale  ──► nhắn khách qua MBS/Pancake
```

**Nguyên tắc bất di bất dịch:**
1. **Chỉ đọc, không ghi** lên dashboard 7-11. Không bấm bất cứ nút nào tạo/sửa/xoá.
2. **Không tự nhắn khách.** Hệ thống chỉ nhắn **nội bộ** cho Sale. Việc nói chuyện với
   khách vẫn do người thật làm trên MBS/Pancake.
3. **Không báo trùng.** Một đơn chỉ báo một lần, trừ khi có quy tắc nhắc lại (Q4).
4. **Thà không báo còn hơn báo sai.** Nếu đọc không được hết danh sách → báo lỗi cho
   người, **không** gửi danh sách thiếu.

---

## 7. Không thuộc phạm vi task này

- Tự động nhắn khách hàng; tự động trả lời MBS/Pancake.
- Đối soát tiền, công nợ, hoàn hàng, xử lý đơn quá hạn bị trả về.
- Quản lý kho, nhập hàng, định giá.
- Thay đổi bất kỳ dữ liệu nào trên hệ thống 7-Eleven.

---

## 8. Giả định đang dùng (cần xác nhận, nếu sai thì thiết kế phải đổi)

| # | Giả định | Hệ quả nếu sai |
|---|---|---|
| A1 | Điểm cần báo là **mốc 4**, không phải mốc 5 | Toàn bộ tín hiệu báo đơn sai thời điểm |
| A2 | Dashboard dùng để đọc là **`myship.7-11.com.tw`** | Selector, đăng nhập, phân trang khác hoàn toàn |
| A3 | Trên dashboard **có** cột "Sale phụ trách" và "STT" | Không biết báo cho ai → phải lấy từ nguồn khác (Pancake/Sheet) |
| A4 | Mỗi Sale phụ trách đơn cố định, 1 đơn = 1 Sale | Phải thiết kế báo cho nhiều người |
| A5 | Có một bộ lọc lưu sẵn tên **`đơn cần báo`** trên dashboard | Phải tự lọc theo trạng thái thay vì dùng filter có sẵn |
| A6 | Chỉ có 1 tài khoản seller duy nhất cần theo dõi | Phải xử lý đa tài khoản/đa cửa hàng |

> ⚠️ **A2 + A3 đang mâu thuẫn với ảnh chụp màn hình.** Ảnh `myship.7-11.com.tw/seller/order`
> hiển thị các cột: Ngày đặt hàng, Tên cửa hàng, Số đơn hàng, Phương thức thanh toán,
> Phương thức giao hàng & hạn nhận hàng, Số lượng, Tổng giá trị, Bản ghi thu thập tên
> người nhận, Xử lý đơn hàng. **Không thấy cột "STT", "Sale phụ trách", "Ký hiệu nhóm",
> hay mã `Sxxxx`.** Đây là các khái niệm **nội bộ DVS**, hệ thống 7-Eleven Đài Loan
> không thể có. ⇒ Nhiều khả năng có **hai** màn hình khác nhau: màn hình 7-11 (trạng thái
> giao hàng) và một màn hình nội bộ/forwarder hoặc Google Sheet (STT + Sale). **Phải xác
> định rõ trước khi viết scraper**, nếu không sẽ code nhầm site.

---

## 9. Câu hỏi mở — cần trả lời trước khi build

- **Q1.** Báo ở mốc 4 (tới cửa hàng, chưa lấy) hay mốc 5 (đã lấy)? → xem §4.
- **Q2.** Màn hình nào là nguồn của **STT** và **Sale phụ trách**? Cùng site với thanh
  tiến độ hay site/Sheet khác? Nếu khác → khớp hai nguồn bằng trường nào?
- **Q3.** Có thật sự tồn tại bộ lọc lưu sẵn tên `đơn cần báo` không? Ai tạo? Ai được xem?
- **Q4.** Nếu Sale không xử lý, có nhắc lại không? Sau bao lâu? Nhắc mấy lần? Sắp tới
  **hạn lấy hàng** thì có leo thang lên quản lý không?
- **Q5.** Báo cho Sale bằng kênh nào — Telegram cá nhân, nhóm Telegram, hay Pancake?
- **Q6.** Một ngày chạy mấy lần, vào giờ nào? (Hàng về theo ca hay rải đều?) Lưu ý: tần suất
  khả thi phụ thuộc kết quả O5/O6 bên Track A. Nếu đọc được endpoint nội bộ thì chạy mỗi 15
  phút là bình thường; nếu phải mở trình duyệt thật mỗi lần thì thực tế chỉ chạy được 2–4
  lần/ngày. Chênh lệch này quyết định khách nhận được thông báo sớm hay muộn vài tiếng, nên
  đây là câu hỏi nghiệp vụ chứ không chỉ là câu hỏi kỹ thuật.
- **Q7.** Khối lượng thực tế: bao nhiêu đơn/ngày, bao nhiêu Sale, bao nhiêu trang danh sách?
- **Q8.** Ngoài Đài Loan còn thị trường/hệ thống vận chuyển nào cần báo đơn tương tự không?
  (Vì công ty bán đa quốc gia — nếu có, kiến trúc phải tách theo "nguồn").
- **Q9.** Đăng nhập dashboard: có CAPTCHA không, có 2FA không, tài khoản dùng chung hay riêng?

---

## 10. Định nghĩa hoàn thành (DoD) cho nghiệp vụ Báo đơn

Nghiệp vụ được coi là **tự động hoá xong** khi:

1. Hệ thống tự phát hiện **100%** đơn đạt mốc "cần báo" trong vòng ≤ 1 chu kỳ chạy.
2. Mỗi đơn được báo đúng **một lần**, tới đúng **Sale phụ trách**, kèm đủ mã đơn để Sale
   tra ra khách.
3. Đơn đã được khách lấy tự động đóng lại, không làm phiền Sale nữa.
4. Có log tra được: đơn nào, báo lúc nào, cho ai, kết quả gì.
5. Khi đọc dashboard thất bại, hệ thống **báo lỗi cho người**, không im lặng bỏ qua.
6. Nhân viên báo đơn chuyển từ "ngồi soi thanh tiến độ" sang "chỉ xử lý ngoại lệ".

---

## 11. Quan hệ với các file context khác

| File | Track | Nội dung |
|---|---|---|
| `DVS-context-01-bao-don.md` (file này) | Nghiệp vụ | Cái gì & tại sao |
| `711-scraper-context.md` | Track A — kỹ thuật | Cách đọc dashboard bằng Playwright, hợp đồng `OrderToReport` |
| *(chưa có)* | Track B — backend | Bot Telegram, DB, reconcile loop, notifier, scheduler |

Nếu §4 (Q1) hoặc §8 (A2/A3) thay đổi, **`711-scraper-context.md` phải được sửa theo**.

Chiều ngược lại thì không: quyết định transport (O5/O6) **không** làm thay đổi file này. Nếu
một quyết định kỹ thuật buộc phải sửa tài liệu nghiệp vụ, đó là dấu hiệu tài liệu nghiệp vụ
đã bị lẫn chi tiết kỹ thuật vào.

---

## 12. Thuật ngữ

| Từ | Nghĩa |
|---|---|
| **Báo đơn** | Việc thông báo "hàng đã tới cửa hàng" cho Sale để Sale nhắc khách đi lấy |
| **Đơn cần báo** | Đơn đã tới cửa hàng nhưng khách chưa lấy |
| **STT** | Số thứ tự nội bộ, dùng làm khoá nối giữa các hệ thống |
| **Sale phụ trách** | Nhân viên sale sở hữu đơn đó, người sẽ nhận thông báo |
| **MBS** | Meta Business Suite — inbox Facebook/Instagram |
| **Pancake** | Nền tảng CRM/chat hợp nhất nhiều kênh, dùng để nhắn khách |
| **myship / 賣貨便** | Dịch vụ bán & giao hàng qua cửa hàng 7-Eleven Đài Loan |
| **Mốc 4 / mốc 5** | Xem bảng ở §4 |
