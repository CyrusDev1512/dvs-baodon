# Quy trình báo đơn — sơ đồ luồng

> **Phiên bản:** v1.0 · cập nhật 07/08/2026
> **Phạm vi:** nghiệp vụ Báo đơn. Xem `DVS-context-01-bao-don.md` cho bối cảnh nghiệp vụ,
> `711-scraper-context.md` cho spec kỹ thuật của bộ đọc dữ liệu.
> **Cảnh báo:** phần TO-BE dựa trên giả định về cấu trúc dashboard. Tại thời điểm viết,
> **team chưa có quyền truy cập dashboard**, nên chưa giả định nào được kiểm chứng.

---

## Chú giải màu

| Màu | Nghĩa |
|---|---|
| ⬜ Trắng | Hành động thông thường |
| 🟩 Xanh lá | Quy tắc nghiệp vụ — không được tự ý đổi khi code |
| 🟦 Xanh dương | Dữ liệu thu được |
| 🟧 Cam | **Chưa xác nhận** — cần người trả lời |
| 🟥 Đỏ | Nhánh ngoại lệ |

---

## 1. AS-IS — quy trình thủ công hiện tại

Đây là những gì nhân viên báo đơn đang làm bằng tay.

```mermaid
flowchart TD
    Start(["TRIGGER: 4 lượt/ngày<br/>(?) giờ chạy cụ thể<br/>50-200 đơn mỗi lượt"]) --> A1

    subgraph S0["GIAI ĐOẠN 0 - Lấy danh sách đơn cần báo"]
        direction TB
        A1["Đăng nhập web app vận đơn"]
        A0{"Đăng nhập được?"}
        A2["Mở BỘ LỌC 'đơn cần báo'<br/>Mọi đơn trong bộ lọc = phải báo<br/>KHÔNG chống trùng - báo lại mỗi lượt"]
        A3["Lấy TOÀN BỘ đơn trong bộ lọc<br/>kể cả các trang sau"]
        A4{"Đọc được hết mọi trang?"}
        A9["DỪNG CẢ LƯỢT - báo người<br/>Không xử lý danh sách thiếu"]
        A1 --> A0
        A0 -- "Không / CAPTCHA" --> A9
        A0 -- "Có" --> A2 --> A3 --> A4
        A4 -- "Không" --> A9
    end

    A4 -- "Có" --> LOOP
    LOOP["LẶP: xử lý từng đơn"] --> B1

    subgraph S1["GIAI ĐOẠN 1 - Đọc thông tin đơn"]
        direction TB
        B1["Mở CHI TIẾT đơn hàng"]
        B2["Trích xuất:<br/>Mã STT<br/>Tên Sale phụ trách<br/>Ký hiệu nhóm"]
        B9["Ngoại lệ: mở lỗi / thiếu field"]
        B1 --> B2
        B1 -. "lỗi" .-> B9
        B2 -. "thiếu field" .-> B9
    end

    B2 --> C1

    subgraph S2["GIAI ĐOẠN 2 - Tìm nhóm trên Messenger"]
        direction TB
        C1["Tìm nhóm theo KÝ HIỆU NHÓM + mã STT<br/>(?) cách 2 giá trị ghép thành tên nhóm"]
        C2{"Khớp được nhóm?"}
        C3["Mở nhóm đơn hàng"]
        C9["Ngoại lệ: không có nhóm /<br/>trùng nhiều nhóm"]
        C1 --> C2
        C2 -- "Có" --> C3
        C2 -- "Không" --> C9
    end

    C3 --> D1

    subgraph S3["GIAI ĐOẠN 3 - Định vị ảnh báo đơn"]
        direction TB
        D1["Tìm TIN NHẮN NEO chứa mã S + STT"]
        D2{"Có tin neo VÀ<br/>có ảnh ngay trên nó?"}
        D3["Thu về: Mã S + Ảnh báo đơn"]
        D9["Ngoại lệ: không thấy tin neo /<br/>không có ảnh / nhiều ảnh"]
        D1 --> D2
        D2 -- "Có" --> D3
        D2 -- "Không" --> D9
    end

    D3 --> E1

    subgraph S4["GIAI ĐOẠN 4 - Nhắn riêng cho Sale"]
        direction TB
        E1["Tra tên Sale trong GOOGLE SHEET<br/>danh sách Sale + link Messenger"]
        E2{"Có trong sheet?"}
        E3["MỘT ĐƠN = MỘT TIN RIÊNG<br/>Nội dung: Mã S + Ảnh báo đơn"]
        E4["Gửi inbox 1-1 cho Sale"]
        E9["Ngoại lệ: Sale chưa có trong sheet /<br/>trùng tên"]
        E1 --> E2
        E2 -- "Có" --> E3 --> E4
        E2 -- "Không" --> E9
    end

    E4 --> NEXT{"Còn đơn?"}
    B9 --> LOG
    C9 --> LOG
    D9 --> LOG
    E9 --> LOG
    LOG["SỔ NGOẠI LỆ<br/>ghi: STT + lý do + thời điểm"] --> NEXT
    NEXT -- "Còn" --> LOOP
    NEXT -- "Hết" --> REVIEW
    REVIEW["NGƯỜI XỬ LÝ SỔ NGOẠI LỆ<br/>(?) ai làm, trong bao lâu"] --> DONE(["Kết thúc lượt"])

    NOTE["QUY TẮC - ĐƠN RỜI BỘ LỌC KHI:<br/>Khách đã lấy hàng, hoặc<br/>Sau 7 ngày đơn hoàn về<br/>Còn trong filter = còn báo lại"]

    classDef unknown fill:#FFF4E5,stroke:#E8A33D,stroke-width:2px,color:#7A4E00
    classDef data fill:#E8F1FC,stroke:#3B7DD8,stroke-width:2px,color:#123A6B
    classDef rule fill:#EAF7EC,stroke:#3E9B54,stroke-width:2px,color:#14532D
    classDef action fill:#FFFFFF,stroke:#8A8A8A,stroke-width:1.5px,color:#222222
    classDef problem fill:#FCEAEA,stroke:#C0392B,stroke-width:2px,color:#7B1F1F

    class C1,REVIEW,Start unknown
    class B2,D3 data
    class A2,D1,NOTE,E3,E1 rule
    class A1,B1,C3,E4,LOOP,LOG action
    class A9,B9,C9,D9,E9 problem
```

---

## 2. TO-BE — hệ thống tự động

Khác biệt cốt lõi so với AS-IS: **tách tần suất quét khỏi tần suất nhắn**, và **chỉ mở
trang chi tiết cho đơn mới** thay vì mở lại toàn bộ mỗi lượt.

```mermaid
flowchart TD
    T(["Chạy nền, mỗi SCAN_INTERVAL_MINUTES"]) --> P1

    P1["Đọc TRANG DANH SÁCH của bộ lọc<br/>chỉ list, không mở chi tiết"]
    P2{"Đọc được hết mọi trang?"}
    P9["DỪNG lượt quét - cảnh báo người<br/>Không xử lý danh sách thiếu"]
    P1 --> P2
    P2 -- "Không" --> P9
    P2 -- "Có" --> P3

    P3["Đối chiếu với DATABASE<br/>khoá: mã đơn"]
    P3 --> N1
    P3 --> R1
    P3 --> X1

    subgraph SN["ĐƠN MỚI - chưa từng thấy"]
        direction TB
        N1["Mở CHI TIẾT đơn<br/>chỉ đơn mới, không mở lại đơn cũ"]
        N2["Lấy STT + Sale phụ trách + ký hiệu nhóm<br/>lưu DB, không đọc lại lần sau"]
        N3["Đưa vào HÀNG ĐỢI GỬI - ưu tiên cao"]
        N1 --> N2 --> N3
    end

    subgraph SR["ĐƠN CŨ - vẫn trong bộ lọc"]
        direction TB
        R1{"Đang ở mốc REMIND_TIMES?"}
        R2{"Quá REMIND_MAX_DAYS?"}
        R3["Đưa vào HÀNG ĐỢI GỬI - nhắc lại"]
        R8["Ngừng nhắc - đẩy sang sổ ngoại lệ"]
        R1 -- "Chưa tới mốc" --> RSKIP["Bỏ qua lượt này"]
        R1 -- "Đúng mốc" --> R2
        R2 -- "Chưa" --> R3
        R2 -- "Rồi" --> R8
    end

    subgraph SX["ĐƠN BIẾN MẤT khỏi bộ lọc"]
        direction TB
        X1["Khách đã lấy hoặc đơn hoàn về"]
        X2["Đóng đơn trong DB - không gửi nữa"]
        X1 --> X2
    end

    N3 --> Q
    R3 --> Q
    Q["HÀNG ĐỢI GỬI<br/>giãn nhịp NOTIFY_RATE_PER_MIN<br/>tôn trọng QUIET_HOURS"]

    Q --> M1
    M1["Lấy ẢNH BÁO ĐƠN<br/>(?) nguồn ảnh chưa xác định"]
    M2{"Lấy được ảnh + link Sale?"}
    M3["Gửi tin cho Sale<br/>(?) qua Messenger hay Pancake"]
    M4["Ghi log: đơn, Sale, thời điểm, kết quả"]
    M9["Ngoại lệ gửi"]
    M1 --> M2
    M2 -- "Có" --> M3 --> M4
    M2 -- "Không" --> M9

    P9 --> ERR
    R8 --> ERR
    M9 --> ERR
    ERR["SỔ NGOẠI LỆ<br/>người xem và xử lý"]

    classDef unknown fill:#FFF4E5,stroke:#E8A33D,stroke-width:2px,color:#7A4E00
    classDef data fill:#E8F1FC,stroke:#3B7DD8,stroke-width:2px,color:#123A6B
    classDef rule fill:#EAF7EC,stroke:#3E9B54,stroke-width:2px,color:#14532D
    classDef action fill:#FFFFFF,stroke:#8A8A8A,stroke-width:1.5px,color:#222222
    classDef problem fill:#FCEAEA,stroke:#C0392B,stroke-width:2px,color:#7B1F1F

    class M1,M3 unknown
    class N2,P3 data
    class P1,Q,R1,R2,X2,N1 rule
    class N3,R3,M4,RSKIP,X1 action
    class P9,R8,M9,ERR problem
```

---

## 3. Bảng cấu hình

Đặt trong `src/config.py` để scraper và backend dùng chung một nguồn.

| Biến | Mặc định | Nghĩa |
|---|---|---|
| `SCAN_INTERVAL_MINUTES` | `15` | Bao lâu quét dashboard một lần |
| `REMIND_TIMES` | `09:00,14:00` | Các mốc nhắc lại đơn cũ |
| `REMIND_MAX_DAYS` | `7` | Nhắc tối đa bao lâu |
| `QUIET_HOURS` | `21:00-07:00` | Không nhắn Sale trong khung này |
| `NOTIFY_RATE_PER_MIN` | `10` | Giãn nhịp gửi, tránh bị coi là spam |

Cấp áp dụng: **chung toàn hệ thống**, không cấu hình riêng theo Sale.

### Bốn quy tắc gửi

1. Đơn **lần đầu** vào bộ lọc → gửi ngay ở lượt quét kế tiếp
2. Đơn **đã báo**, còn trong bộ lọc → chỉ gửi lại ở mốc `REMIND_TIMES`
3. Đơn **rời bộ lọc** → đóng, ngừng gửi
4. Quá `REMIND_MAX_DAYS` → ngừng nhắc, đẩy sang sổ ngoại lệ

---

## 4. Đã xác nhận vs chưa xác nhận

### ✅ Đã xác nhận

- Kênh liên lạc là **Messenger**, không phải Telegram
- Bộ lọc `đơn cần báo` tồn tại trên dashboard
- Tín hiệu cần báo = hàng **đã tới cửa hàng, khách chưa lấy** (mốc 4, không phải mốc 5)
- Đơn rời bộ lọc khi khách lấy hàng hoặc sau 7 ngày hoàn về
- Không chống trùng: còn trong bộ lọc thì còn báo lại
- Khối lượng: 50–200 đơn mỗi lượt
- `Sale phụ trách`, `STT`, `ký hiệu nhóm` nằm ở **trang chi tiết**, không phải trang danh sách
- Danh sách Sale + link Messenger nằm trong **Google Sheet**
- Đơn mới báo ngay; đơn cũ nhắc sáng + chiều; số lần cấu hình được, cấp toàn hệ thống

### 🟧 Chưa xác nhận

| # | Câu hỏi | Chặn cái gì |
|---|---|---|
| 1 | **Ảnh báo đơn lưu ở đâu?** Có tra được theo mã đơn không, hay phải mò trong nhóm Messenger mỗi lần? | Toàn bộ Giai đoạn 3 |
| 2 | Có tồn tại Telegram bot lưu ảnh theo mã đơn không? Spec `711-scraper-context.md` khẳng định có — mâu thuẫn với quy trình Messenger | Kiến trúc |
| 3 | Gửi tin cho Sale qua Messenger hay **Pancake**? Tự động hoá tài khoản Facebook cá nhân vi phạm điều khoản Meta, chế tài là khoá tài khoản | Giai đoạn 4 |
| 4 | Ký hiệu nhóm + STT ghép thành tên nhóm Messenger theo quy tắc nào? | Giai đoạn 2 |
| 5 | Trang danh sách có mã định danh ổn định cho từng dòng không? Cần để đối chiếu tìm đơn mới | Thiết kế TO-BE |
| 6 | Web app vận đơn là `myship.7-11.com.tw` hay một hệ thống forwarder riêng? | Track A |
| 7 | 4 lượt/ngày hiện tại chạy vào giờ nào? Một lượt mất bao lâu? Tỷ lệ ngoại lệ bao nhiêu? | Ước lượng tải |
| 8 | `QUIET_HOURS` mặc định 21:00–07:00 có hợp không? Hàng 7-11 thường về sáng sớm | Cấu hình |

---

## 5. 🚧 Đang bị chặn

**Team hiện chưa có quyền truy cập dashboard.**

Hệ quả: không trả lời được O1–O6, không tìm được selector hay endpoint, không viết được
`src/scraper/seven_eleven.py`, không lưu được fixture test. Track A dừng hoàn toàn.

**Việc gấp nhất hiện tại là xin quyền truy cập**, không phải việc kỹ thuật nào khác. Cần
biết: ai đang giữ tài khoản, vì sao chưa cấp được, dự kiến bao giờ có.

### Làm được ngay, không cần truy cập

- Trả lời câu hỏi 1, 2, 3, 4, 7, 8 ở bảng trên — chỉ cần hỏi người trong công ty
- Chốt Messenger hay Pancake
- Ghi lại quy trình chính xác hơn bằng cách ngồi xem nhân viên báo đơn làm một lượt thật
