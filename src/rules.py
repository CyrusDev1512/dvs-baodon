"""Quy tắc thuần của nghiệp vụ báo đơn — không I/O, không sqlite, chỉ tính toán.

Đây là lõi được unit-test dày nhất. Mọi quyết định "có gửi không, gửi vì mốc nào"
đều nằm ở đây; reconcile.py chỉ ghép các hàm này với DB.
"""
from __future__ import annotations

import datetime as _dt
from datetime import time

from src.scraper.interface import OrderToReport


def order_key(order: OrderToReport) -> str:
    """Khoá đối chiếu giữa các lượt quét.

    Hiện tại = `stt` (join key bắt buộc của contract). Câu hỏi O3 (STT có unique
    toàn cục không) và câu 5 (mã định danh trên trang danh sách) chưa xác nhận —
    khi có mã đơn thật (CCxxxx qua `raw`), CHỈ sửa hàm này + migration user_version.
    """
    return order.stt


def in_quiet_hours(t: _dt.datetime | time, quiet: tuple[time, time]) -> bool:
    """Trong khung không-nhắn-Sale? Cho phép khung qua nửa đêm (21:00-07:00)."""
    tt = t.time() if isinstance(t, _dt.datetime) else t
    start, end = quiet
    if start > end:  # qua nửa đêm: 21:00 -> 07:00 hôm sau
        return tt >= start or tt < end
    return start <= tt < end


def due_remind_mark(
    now: _dt.datetime,
    last_notified_at: _dt.datetime,
    remind_times: tuple[time, ...],
) -> _dt.datetime | None:
    """Mốc nhắc nào đang "nợ"? Trả về mốc muộn nhất M sao cho M <= now và
    last_notified_at < M; không có thì None.

    Tính chất (được test chốt chặt):
    - Không bắn lặp trong ngày: gửi xong thì last_notified_at >= M, các lượt quét
      15' sau đó trả None cho tới mốc kế.
    - Mốc bị lỡ (máy tắt lúc 09:00, chạy lại 10:30) vẫn bắn bù, vì
      last_notified_at vẫn < mốc 09:00.
    - Xét cả mốc của ngày hôm trước để đơn không bị bỏ qua khi máy nghỉ dài.
    """
    candidates: list[_dt.datetime] = []
    for day_offset in (0, -1):
        day = now.date() + _dt.timedelta(days=day_offset)
        for mark_time in remind_times:
            mark = _dt.datetime.combine(day, mark_time)
            if mark <= now and last_notified_at < mark:
                candidates.append(mark)
    return max(candidates) if candidates else None


def is_expired(
    now: _dt.datetime, first_seen_at: _dt.datetime, max_days: int
) -> bool:
    """Quá REMIND_MAX_DAYS kể từ lần đầu HỆ THỐNG thấy đơn (không phải lúc hàng
    thật tới cửa hàng — contract không có timestamp đó)."""
    return now - first_seen_at >= _dt.timedelta(days=max_days)
