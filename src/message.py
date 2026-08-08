"""Soạn nội dung tin nhắn gửi Sale — tách khỏi kênh gửi.

Vì sao tách: kênh gửi (Messenger) chưa chốt cách làm an toàn, nhưng NỘI DUNG tin thì
đã biết từ quy trình tay và ảnh mẫu nhóm Messenger thật:
- Quy trình tay (bao-don-flow.md §S4): "MỘT ĐƠN = MỘT TIN RIÊNG, nội dung: Mã S + Ảnh".
- Ảnh mẫu: album 3-4 ảnh, rồi tin mã S (`S9663`), rồi tin STT (`5079`) — mỗi thứ một
  dòng ngắn, không văn vẻ. Giữ đúng dạng đó để Sale nhận ra ngay như tin người gửi.

Khi có kênh gửi thật, bản Notifier mới chỉ việc gọi build_message() — không phải nghĩ
lại nội dung.
"""
from __future__ import annotations

from src.notify import SendTask

_PREFIX = {
    "first": "",
    "remind": "Nhắc lại — khách chưa lấy:",
    "reopen": "Đơn quay lại danh sách cần báo:",
}


def build_message(task: SendTask) -> str:
    """Thân tin nhắn (ảnh gửi kèm riêng, xem task.images)."""
    lines: list[str] = []
    prefix = _PREFIX.get(task.kind, "")
    if prefix:
        lines.append(prefix)
    lines.append(task.s_code or f"(chưa có mã S — đơn STT {task.stt})")
    lines.append(f"STT {task.stt}")
    return "\n".join(lines)
