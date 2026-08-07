"""E2E: timeline 2 ngày với FakeClock — vòng đời trọn vẹn của một lô đơn."""
from __future__ import annotations

from src.notify import DryRunImageStore, DryRunNotifier
from src.reconcile import run_cycle
from src.scraper.mock import MockScraper
from tests.conftest import make_order


def test_two_day_lifecycle(store, clock, settings):
    n = DryRunNotifier(echo=False)
    img = DryRunImageStore()
    a = make_order(stt="1502", sale="Nguyễn Thu Hà")
    b = make_order(stt="1503", sale="Trần Minh")

    def go(orders):
        return run_cycle(MockScraper(orders=orders), store, n, img, clock, settings)

    # 08:50 ngày 1: hai đơn mới → gửi ngay (quy tắc 1)
    clock.set(2026, 8, 7, 8, 50)
    s = go([a, b])
    assert s.new == 2 and len(n.sent) == 2

    # 09:05: qua mốc 09:00 → nhắc cả hai (quy tắc 2)
    clock.set(2026, 8, 7, 9, 5)
    s = go([a, b])
    assert s.reminded == 2 and len(n.sent) == 4

    # 09:20: im lặng — chưa tới mốc kế
    clock.set(2026, 8, 7, 9, 20)
    s = go([a, b])
    assert s.not_due == 2 and len(n.sent) == 4

    # 14:10: mốc 14:00 → nhắc; đơn b biến mất → đóng, không gửi (quy tắc 3)
    clock.set(2026, 8, 7, 14, 10)
    s = go([a])
    assert s.reminded == 1 and s.closed == 1 and len(n.sent) == 5
    assert store.get_all()["1503"]["status"] == "closed"

    # 09:05 ngày 2: mốc mới của ngày mới → nhắc a
    clock.set(2026, 8, 8, 9, 5)
    s = go([a])
    assert s.reminded == 1 and len(n.sent) == 6

    # Ngày 15 (quá REMIND_MAX_DAYS=7): a quá hạn → ngừng nhắc, vào sổ (quy tắc 4)
    clock.set(2026, 8, 15, 9, 5)
    s = go([a])
    assert s.expired == 1 and len(n.sent) == 6
    assert store.get_all()["1502"]["status"] == "expired"

    # Audit đầy đủ: đơn nào, loại gì, lúc nào (DoD #4)
    kinds = [r["kind"] for r in store.notifications_for("1502")]
    assert kinds == ["first", "remind", "remind", "remind"]
