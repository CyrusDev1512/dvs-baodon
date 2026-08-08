"""Soạn nội dung tin nhắn gửi Sale — tách khỏi kênh gửi.

Vì sao tách: kênh gửi (Messenger) chưa chốt cách làm an toàn, nhưng NỘI DUNG tin thì
đã biết từ quy trình tay và ảnh mẫu nhóm Messenger thật:
- Quy trình tay (bao-don-flow.md §S4): "MỘT ĐƠN = MỘT TIN RIÊNG, nội dung: Mã S + Ảnh".
- Ảnh mẫu: album 3-4 ảnh, rồi tin mã S (`S9663`), rồi tin STT (`5079`) — mỗi thứ một
  dòng ngắn, không văn vẻ. Giữ đúng dạng đó để Sale nhận ra ngay như tin người gửi.
  (Nếu Sale muốn đúng dạng 3 tin rời như bản tay, bản Notifier thật cứ tách `body`
  theo dòng mà gửi thành nhiều tin — nội dung không đổi.)

Nội dung được dựng sẵn vào `SendTask.body` trong reconcile, nên MỌI Notifier đều gửi
đúng một thứ mà bản dry-run đã in ra — bản thật không thể tự chế lại nội dung khác.

Nhận tham số rời (không nhận SendTask) để module này là lá: notify.py import được nó
mà không sinh vòng import.
"""
from __future__ import annotations

# Các loại tin hợp lệ; reconcile chỉ được phát ra đúng những loại này.
_PREFIX = {
    "first": "",
    "remind": "Nhắc lại — khách chưa lấy:",
    "reopen": "Đơn quay lại danh sách cần báo:",
}
KINDS = tuple(_PREFIX)


def build_message(kind: str, s_code: str | None, stt: str) -> str:
    """Thân tin nhắn (ảnh gửi kèm riêng, xem SendTask.images).

    `kind` lạ sẽ ném KeyError — cố ý: đó là lỗi lập trình, phải lộ ra ở test chứ
    không được âm thầm gửi ra dạng tin "báo lần đầu"."""
    lines: list[str] = []
    prefix = _PREFIX[kind]
    if prefix:
        lines.append(prefix)
    lines.append(s_code or f"(chưa có mã S — đơn STT {stt})")
    lines.append(f"STT {stt}")
    return "\n".join(lines)
