"""Test nội dung tin gửi Sale — bám đúng dạng tin tay (mã S + STT, không văn vẻ)."""
from __future__ import annotations

import pytest

from src.message import build_message


def test_first_message_is_scode_then_stt():
    assert build_message("first", "S9663", "5079") == "S9663\nSTT 5079"


def test_remind_and_reopen_have_prefix():
    assert build_message("remind", "S9663", "5079").startswith("Nhắc lại")
    assert build_message("reopen", "S9663", "5079").startswith("Đơn quay lại")


def test_missing_s_code_still_identifies_order():
    body = build_message("first", None, "5079")
    assert "5079" in body and "chưa có mã S" in body


def test_unknown_kind_raises_instead_of_silently_looking_like_first():
    with pytest.raises(KeyError):
        build_message("reminder", "S9663", "5079")  # gõ nhầm 'remind'
