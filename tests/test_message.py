"""Test nội dung tin gửi Sale — bám đúng dạng tin tay (mã S + STT, không văn vẻ)."""
from __future__ import annotations

from src.message import build_message
from src.notify import ImageRef, SendTask


def _task(kind="first", s_code="S9663", stt="5079"):
    return SendTask(order_key=stt, stt=stt, s_code=s_code,
                    sale_name="Nguyễn Thu Hà", kind=kind,
                    images=(ImageRef(stt, "dryrun", "dryrun://x"),))


def test_first_message_is_scode_then_stt():
    assert build_message(_task()) == "S9663\nSTT 5079"


def test_remind_and_reopen_have_prefix():
    assert build_message(_task(kind="remind")).startswith("Nhắc lại")
    assert build_message(_task(kind="reopen")).startswith("Đơn quay lại")


def test_missing_s_code_still_identifies_order():
    body = build_message(_task(s_code=None))
    assert "5079" in body and "chưa có mã S" in body
