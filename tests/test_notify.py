"""Test notifier dry-run, kho ảnh giả lập và rate limiter."""
from __future__ import annotations

from src.notify import DryRunImageStore, DryRunNotifier, ImageRef, RateLimiter, SendTask
from tests.conftest import make_order


def _task(stt="1502"):
    return SendTask(order_key=stt, stt=stt, s_code="S9663",
                    sale_name="Nguyễn Thu Hà", kind="first",
                    images=(ImageRef(stt, "dryrun", f"dryrun://{stt}/1"),),
                    body="S9663\nSTT 1502")


def test_dryrun_notifier_records_tasks():
    n = DryRunNotifier(echo=False)
    assert n.send(_task()) == "dry-run"
    assert len(n.sent) == 1 and n.sent[0].stt == "1502"


def test_dryrun_echo_prints_the_body_that_will_be_sent(capsys):
    """Dòng in ra chính là nội dung Sale sẽ nhận — đường kiểm tra chính của người."""
    DryRunNotifier(echo=True).send(_task())
    out = capsys.readouterr().out
    assert "Nguyễn Thu Hà" in out and "S9663" in out and "STT 1502" in out
    assert "1 ảnh" in out




def test_image_store_multiple_images_and_missing():
    store = DryRunImageStore(missing={"1509"})
    assert len(store.get_images(make_order(stt="1502"))) == 2  # album nhiều ảnh
    assert store.get_images(make_order(stt="1509")) == ()      # giả lập thiếu ảnh


def test_rate_limiter_sleep_pattern():
    sleeps: list[float] = []
    limiter = RateLimiter(10, sleeps.append)  # 10 tin/phút → 6s giữa các tin
    for _ in range(3):
        limiter.wait_turn()
    assert sleeps == [6.0, 6.0]  # không chờ trước tin đầu tiên


def test_rate_limiter_zero_rate_never_sleeps():
    sleeps: list[float] = []
    limiter = RateLimiter(0, sleeps.append)
    limiter.wait_turn()
    limiter.wait_turn()
    assert sleeps == []
