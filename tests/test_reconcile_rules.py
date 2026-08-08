"""Test 4 quy tắc gửi + các nhánh ngoại lệ của run_cycle."""
from __future__ import annotations

from src.db import Store
from src.notify import DryRunImageStore, DryRunNotifier, FailingNotifier
from src.reconcile import run_cycle
from src.scraper.interface import ParseError
from src.sale_directory import CsvSaleDirectory
from src.scraper.mock import MockScraper
from tests.conftest import make_order


def cycle(store, clock, settings, orders=None, error=None,
          notifier=None, image_store=None, sale_directory=None):
    return run_cycle(
        MockScraper(orders=orders, error=error) if orders is not None or error else MockScraper(orders=[]),
        store,
        notifier or DryRunNotifier(echo=False),
        image_store or DryRunImageStore(),
        clock,
        settings,
        sale_directory=sale_directory,
    )


def test_rule1_new_order_sent_immediately(store, clock, settings):
    n = DryRunNotifier(echo=False)
    s = cycle(store, clock, settings, orders=[make_order()], notifier=n)
    assert s.new == 1
    assert [t.kind for t in n.sent] == ["first"]
    assert store.get_all()["1502"]["first_notified_at"] is not None


def test_rule2_remind_only_at_mark(store, clock, settings):
    n = DryRunNotifier(echo=False)
    clock.set(2026, 8, 7, 8, 0)
    cycle(store, clock, settings, orders=[make_order()], notifier=n)   # first lúc 08:00

    clock.set(2026, 8, 7, 8, 30)                                       # chưa tới mốc
    s = cycle(store, clock, settings, orders=[make_order()], notifier=n)
    assert s.not_due == 1 and len(n.sent) == 1

    clock.set(2026, 8, 7, 9, 5)                                        # qua mốc 09:00
    s = cycle(store, clock, settings, orders=[make_order()], notifier=n)
    assert s.reminded == 1
    assert [t.kind for t in n.sent] == ["first", "remind"]

    clock.set(2026, 8, 7, 9, 20)                                       # không bắn lặp
    s = cycle(store, clock, settings, orders=[make_order()], notifier=n)
    assert s.not_due == 1 and len(n.sent) == 2


def test_rule3_absent_closed_nothing_sent(store, clock, settings):
    n = DryRunNotifier(echo=False)
    cycle(store, clock, settings, orders=[make_order()], notifier=n)
    s = cycle(store, clock, settings, orders=[], notifier=n)           # đơn biến mất
    assert s.closed == 1
    assert store.get_all()["1502"]["status"] == "closed"
    assert len(n.sent) == 1                                            # không gửi thêm


def test_rule4_expired_logged_never_queued_again(store, clock, settings):
    n = DryRunNotifier(echo=False)
    clock.set(2026, 8, 1, 8, 0)
    cycle(store, clock, settings, orders=[make_order()], notifier=n)
    clock.set(2026, 8, 8, 9, 5)                                        # ngày thứ 8
    s = cycle(store, clock, settings, orders=[make_order()], notifier=n)
    assert s.expired == 1 and len(n.sent) == 1
    assert store.get_all()["1502"]["status"] == "expired"
    assert store.exception_count() == 1
    s = cycle(store, clock, settings, orders=[make_order()], notifier=n)  # vẫn trong lọc
    assert s.expired == 0 and len(n.sent) == 1                            # không nhắc nữa


def test_rule1_debt_after_quiet_hours(store, clock, settings):
    n = DryRunNotifier(echo=False)
    clock.set(2026, 8, 7, 22, 0)                                       # trong giờ im lặng
    s = cycle(store, clock, settings, orders=[make_order()], notifier=n)
    assert s.new == 1 and s.deferred_quiet == 1 and n.sent == []

    clock.set(2026, 8, 8, 7, 10)                                       # hết giờ im lặng
    s = cycle(store, clock, settings, orders=[make_order()], notifier=n)
    assert [t.kind for t in n.sent] == ["first"]                       # nợ được trả


def test_reopen_after_close(store, clock, settings):
    n = DryRunNotifier(echo=False)
    clock.set(2026, 8, 7, 8, 0)
    cycle(store, clock, settings, orders=[make_order()], notifier=n)
    cycle(store, clock, settings, orders=[], notifier=n)               # đóng
    clock.set(2026, 8, 7, 10, 0)
    s = cycle(store, clock, settings, orders=[make_order()], notifier=n)  # quay lại
    assert s.reopened == 1
    row = store.get_all()["1502"]
    assert row["reopen_count"] == 1 and row["status"] == "active"
    assert n.sent[-1].kind == "reopen"                                 # báo lại ngay
    assert store.exception_count() == 1                                # + ghi sổ bất thường


def test_duplicate_stt_excluded_and_logged(store, clock, settings):
    n = DryRunNotifier(echo=False)
    dup = [make_order(stt="1502"), make_order(stt="1502", sale="Trần Minh")]
    s = cycle(store, clock, settings, orders=dup, notifier=n)
    assert s.duplicates == 1 and s.new == 0 and n.sent == []
    assert store.exception_count() == 1


def test_scraper_error_aborts_zero_writes(store, clock, settings):
    s = cycle(store, clock, settings, error=ParseError("đọc thiếu trang 2"))
    assert s.aborted and "ParseError" in s.abort_reason
    assert store.get_all() == {}                                       # 0 ghi orders
    assert store.exception_count() == 1                                # nhưng có ghi sổ


def test_missing_image_skips_send(store, clock, settings):
    n = DryRunNotifier(echo=False)
    s = cycle(store, clock, settings, orders=[make_order()],
              notifier=n, image_store=DryRunImageStore(missing={"1502"}))
    assert s.skipped_no_image == 1 and n.sent == []
    assert store.get_all()["1502"]["first_notified_at"] is None        # vẫn nợ
    assert store.exception_count() == 1


def test_unknown_sale_is_never_guessed(store, clock, settings, tmp_path):
    """Không tra được Sale trong danh bạ thì tuyệt đối không gửi cho ai."""
    csv = tmp_path / "s.csv"
    csv.write_text("sale_name,messenger_link\nTrần Minh,https://m.me/x\n",
                   encoding="utf-8")
    n = DryRunNotifier(echo=False)
    orders = [make_order(stt="1502", sale="Nguyễn Thu Hà"),   # chưa có trong danh bạ
              make_order(stt="1503", sale="Trần Minh")]
    s = cycle(store, clock, settings, orders=orders, notifier=n,
              sale_directory=CsvSaleDirectory(csv))
    assert s.skipped_no_sale == 1
    assert [t.stt for t in n.sent] == ["1503"]                  # đơn kia vẫn gửi
    assert n.sent[0].sale_link == "https://m.me/x"              # gửi đúng nơi
    assert store.get_all()["1502"]["first_notified_at"] is None  # còn nợ, sẽ thử lại
    assert store.exception_count() == 1


def test_ambiguous_sale_name_blocks_send(store, clock, settings, tmp_path):
    """Hai Sale trùng tên: thà không báo còn hơn báo nhầm người."""
    csv = tmp_path / "s.csv"
    csv.write_text("sale_name,messenger_link\nTrần Minh,https://m.me/a\n"
                   "Trần Minh,https://m.me/b\n", encoding="utf-8")
    n = DryRunNotifier(echo=False)
    s = cycle(store, clock, settings, orders=[make_order(sale="Trần Minh")],
              notifier=n, sale_directory=CsvSaleDirectory(csv))
    assert s.skipped_no_sale == 1 and n.sent == []
    assert store.exception_count() == 1


def test_one_send_error_does_not_stop_rest(store, clock, settings):
    inner = DryRunNotifier(echo=False)
    n = FailingNotifier(inner, fail_stt={"1502"})
    orders = [make_order(stt="1502"), make_order(stt="1503", sale="Trần Minh")]
    s = cycle(store, clock, settings, orders=orders, notifier=n)
    assert s.send_errors == 1
    assert [t.stt for t in inner.sent] == ["1503"]                     # đơn kia vẫn gửi
    assert store.get_all()["1502"]["first_notified_at"] is None        # lỗi → chưa đánh dấu
    assert store.get_all()["1503"]["first_notified_at"] is not None
