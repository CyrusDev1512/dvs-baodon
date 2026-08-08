"""Giao diện gửi tin + kho ảnh, kèm bản DryRun (chưa có kênh gửi thật).

Hai quyết định nghiệp vụ đã chốt 07/08/2026:
- ẢNH LÀ BẮT BUỘC trong mọi tin gửi — không có ảnh thì không gửi, ghi sổ ngoại lệ.
- Một tin có thể kèm NHIỀU ảnh (nhóm Messenger thật đăng album 3-4 ảnh + tin mã S
  + tin STT riêng — theo ảnh mẫu người dùng cung cấp).

Chưa chốt: cách gửi Messenger an toàn (tự động hoá tài khoản cá nhân vi phạm ToS
Meta) và khoá tra ảnh của bot Telegram (STT / mã S / mã vận đơn). Vì vậy chỉ có ABC
+ DryRun ở đây; bản thật là một class mới, không sửa chỗ khác.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.scraper.interface import OrderToReport


class NotifyError(Exception):
    """Gửi tin thất bại — ghi sổ ngoại lệ, không làm hỏng cả lượt."""


@dataclass(frozen=True)
class ImageRef:
    key: str          # khoá đã dùng để tra (hiện tại: stt)
    source: str       # 'dryrun' | 'telegram-bot' (tương lai)
    location: str     # ví dụ: dryrun://1502, file path, telegram file_id


@dataclass(frozen=True)
class SendTask:
    order_key: str
    stt: str
    s_code: str | None
    sale_name: str
    kind: str                          # 'first' | 'remind' | 'reopen'
    images: tuple[ImageRef, ...]       # luôn >= 1 ảnh (ảnh bắt buộc)
    body: str                          # nội dung đã soạn sẵn (src/message.py)
    sale_link: str                     # nơi gửi, tra từ danh bạ Sale
    sale_channel: str                  # 'messenger' | 'dryrun'


class ImageStore(ABC):
    @abstractmethod
    def get_images(self, order: OrderToReport) -> tuple[ImageRef, ...]:
        """Toàn bộ ảnh báo đơn của đơn này; rỗng = không có ảnh (sẽ không gửi).

        Nhận cả OrderToReport để khoá tra (STT / mã S / mã vận đơn qua raw) là chi
        tiết nội bộ của implementation — khi bot Telegram trả lời khoá tra là gì,
        chỉ sửa một class."""


class Notifier(ABC):
    @abstractmethod
    def send(self, task: SendTask) -> str:
        """Gửi `task.body` kèm `task.images` cho Sale. Trả về mô tả kết quả để ghi
        audit; lỗi thì raise NotifyError.

        Bản thật KHÔNG tự soạn lại nội dung — dùng đúng `task.body` để những gì
        dry-run in ra chính là những gì Sale nhận được."""


class DryRunImageStore(ImageStore):
    """Giả lập kho ảnh: mỗi đơn 2 ảnh dryrun://; `missing` để giả lập thiếu ảnh."""

    def __init__(self, missing: set[str] | None = None):
        self.missing = missing or set()

    def get_images(self, order: OrderToReport) -> tuple[ImageRef, ...]:
        if order.stt in self.missing:
            return ()
        return (
            ImageRef(key=order.stt, source="dryrun", location=f"dryrun://{order.stt}/1"),
            ImageRef(key=order.stt, source="dryrun", location=f"dryrun://{order.stt}/2"),
        )


class DryRunNotifier(Notifier):
    """In ra những gì SẼ gửi, không chạm mạng. Ghi lại vào self.sent để test."""

    def __init__(self, echo: bool = True):
        self.echo = echo
        self.sent: list[SendTask] = []

    def send(self, task: SendTask) -> str:
        self.sent.append(task)
        if self.echo:
            print(
                f"[DRY-RUN] GỬI {task.sale_name} <{task.sale_link}>"
                f" ← {task.body.replace(chr(10), ' / ')}"
                f" [{len(task.images)} ảnh] ({task.kind})"
            )
        return "dry-run"


class FailingNotifier(Notifier):
    """Cho test: luôn lỗi với các STT chỉ định."""

    def __init__(self, inner: Notifier, fail_stt: set[str]):
        self.inner = inner
        self.fail_stt = fail_stt

    def send(self, task: SendTask) -> str:
        if task.stt in self.fail_stt:
            raise NotifyError(f"giả lập lỗi gửi cho STT {task.stt}")
        return self.inner.send(task)


class RateLimiter:
    """Giãn nhịp NOTIFY_RATE_PER_MIN: chờ 60/rate giây giữa hai lần gửi liên tiếp
    (không chờ trước lần đầu). sleep_fn inject được để test/không chờ thật."""

    def __init__(self, rate_per_min: int, sleep_fn):
        self._interval = 60.0 / rate_per_min if rate_per_min > 0 else 0.0
        self._sleep = sleep_fn
        self._sent_any = False

    def wait_turn(self) -> None:
        if self._sent_any and self._interval > 0:
            self._sleep(self._interval)
        self._sent_any = True
