"""Reconcile — một lượt quét: fetch → đối chiếu DB → gửi (dry-run) → tổng kết.

Bốn quy tắc gửi (bao-don-flow.md §3):
1. Đơn lần đầu vào bộ lọc → gửi ngay ở lượt quét kế tiếp.
2. Đơn đã báo, còn trong bộ lọc → chỉ gửi lại ở mốc REMIND_TIMES.
3. Đơn rời bộ lọc → đóng, ngừng gửi.
4. Quá REMIND_MAX_DAYS → ngừng nhắc, đẩy sang sổ ngoại lệ.

Không có bảng hàng đợi: quy tắc 1/2 suy ra từ trạng thái lưu trong DB, nên một lần
gửi bị hoãn (QUIET_HOURS) hay bị crash sẽ tự "nợ" sang lượt sau — miễn phí và an toàn.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from src import rules
from src.clock import Clock
from src.config import Settings
from src.db import Store, parse_ts
from src.message import build_message
from src.notify import (
    ImageStore,
    Notifier,
    NotifyError,
    RateLimiter,
    SendTask,
)
from src.sale_directory import OpenSaleDirectory, SaleDirectory, SaleLookupError
from src.scraper.interface import BaseScraper, OrderToReport, ScraperError


@dataclass
class CycleSummary:
    at: _dt.datetime
    aborted: bool = False
    abort_reason: str = ""
    scanned: int = 0
    new: int = 0
    reminded: int = 0
    reopened: int = 0
    not_due: int = 0
    closed: int = 0
    expired: int = 0
    deferred_quiet: int = 0
    skipped_no_image: int = 0
    skipped_no_sale: int = 0
    send_errors: int = 0
    duplicates: int = 0
    sent_lines: list[str] = field(default_factory=list)


def run_cycle(
    scraper: BaseScraper,
    store: Store,
    notifier: Notifier,
    image_store: ImageStore,
    clock: Clock,
    settings: Settings,
    sleep_fn=None,
    sale_directory: SaleDirectory | None = None,
) -> CycleSummary:
    now = clock.now()
    summary = CycleSummary(at=now)

    # 1. FETCH — lỗi là hủy cả lượt, KHÔNG ghi gì vào bảng orders
    #    ("thà không báo còn hơn báo sai": không xử lý danh sách thiếu).
    try:
        orders = scraper.fetch_orders_to_report()
    except ScraperError as e:
        store.log_exception(now, None, "scan thất bại", f"{type(e).__name__}: {e}")
        summary.aborted = True
        summary.abort_reason = f"{type(e).__name__}: {e}"
        return summary
    summary.scanned = len(orders)

    # 2. DEDUP GUARD — STT trùng trong một lượt là cờ đỏ O3 (STT không unique?):
    #    loại các bản trùng khỏi xử lý + ghi sổ, phần còn lại vẫn chạy.
    by_key: dict[str, OrderToReport] = {}
    dup_keys: set[str] = set()
    for o in orders:
        k = rules.order_key(o)
        if k in by_key:
            dup_keys.add(k)
        else:
            by_key[k] = o
    for k in dup_keys:
        del by_key[k]
        summary.duplicates += 1
        store.log_exception(now, k, "STT trùng trong một lượt quét",
                            "cờ đỏ O3 — STT có thể không unique, cần kiểm tra ngay")

    # 3. CLASSIFY — so với DB, áp 4 quy tắc, dựng queue in-memory.
    db_orders = store.get_all()
    queue: list[tuple[OrderToReport, str]] = []  # (đơn, kind)

    for key, o in by_key.items():
        row = db_orders.get(key)
        if row is None:
            store.insert_order(key, o, now)                       # quy tắc 1
            summary.new += 1
            queue.append((o, "first"))
        elif row["status"] == "active":
            store.touch_seen(key, now)
            if rules.is_expired(now, parse_ts(row["first_seen_at"]),
                                settings.remind_max_days):        # quy tắc 4
                store.expire_order(key)
                summary.expired += 1
                store.log_exception(now, o.stt, "quá REMIND_MAX_DAYS",
                                    f"ngừng nhắc sau {settings.remind_max_days} ngày,"
                                    " người xử lý tiếp")
            elif row["first_notified_at"] is None:                # nợ quy tắc 1
                queue.append((o, "first"))
            elif rules.due_remind_mark(now, parse_ts(row["last_notified_at"]),
                                       settings.remind_times):    # quy tắc 2
                queue.append((o, "remind"))
            else:
                summary.not_due += 1
        elif row["status"] == "closed":
            # Đơn đã đóng lại xuất hiện: báo lại ngay + ghi sổ (chốt 07/08/2026).
            store.reopen_order(key, now)
            summary.reopened += 1
            store.log_exception(now, o.stt, "đơn quay lại bộ lọc sau khi đóng",
                                "bất thường — người nên kiểm tra")
            queue.append((o, "reopen"))
        else:  # expired nhưng vẫn trong bộ lọc: không nhắc nữa, chỉ ghi nhận còn thấy
            store.touch_seen(key, now)

    for key, row in db_orders.items():
        if key not in by_key and row["status"] == "active":       # quy tắc 3
            store.close_order(key, now)
            summary.closed += 1

    # 4. SEND — trong QUIET_HOURS thì không gửi gì; trạng thái chưa-báo giữ nguyên
    #    nên lượt đầu tiên sau giờ im lặng sẽ tự gửi bù.
    if rules.in_quiet_hours(now, settings.quiet_hours):
        summary.deferred_quiet = len(queue)
        return summary

    directory = sale_directory or OpenSaleDirectory()
    limiter = RateLimiter(settings.notify_rate_per_min,
                          sleep_fn if sleep_fn is not None else (lambda s: None))
    for o, kind in queue:
        key = rules.order_key(o)
        # Không biết chắc gửi cho ai thì KHÔNG gửi — thà không báo còn hơn báo nhầm.
        try:
            contact = directory.lookup(o.sale_name)
        except SaleLookupError as e:
            summary.skipped_no_sale += 1
            store.log_exception(now, o.stt, "không tra được Sale trong danh bạ", str(e))
            continue
        images = image_store.get_images(o)
        if not images:  # ảnh bắt buộc (chốt 07/08/2026) — thiếu là không gửi
            summary.skipped_no_image += 1
            store.log_exception(now, o.stt, "không có ảnh báo đơn",
                                "ảnh là bắt buộc — bỏ qua, người xử lý")
            continue
        limiter.wait_turn()
        task = SendTask(order_key=key, stt=o.stt, s_code=o.s_code,
                        sale_name=o.sale_name, kind=kind, images=images,
                        body=build_message(kind, o.s_code, o.stt),
                        sale_link=contact.link, sale_channel=contact.channel)
        try:
            result = notifier.send(task)
        except NotifyError as e:
            summary.send_errors += 1
            store.log_exception(now, o.stt, "gửi tin thất bại", str(e))
            continue
        store.mark_notified(key, kind, o.sale_name, now, result)
        if kind == "remind":
            summary.reminded += 1
        summary.sent_lines.append(
            f"{o.sale_name} ← STT {o.stt} ({kind}, {len(images)} ảnh)")

    return summary
