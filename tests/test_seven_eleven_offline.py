"""Test parse offline từ fixture HTML thật (đã sanitize).

Theo DoD trong docs/711-scraper-context.md: sau khi khảo sát site thật, lưu một trang
danh sách vào tests/fixtures/dashboard_sample.html rồi bỏ skip test này.
"""
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "dashboard_sample.html"


@pytest.mark.skipif(not FIXTURE.exists(), reason="chưa có fixture từ site thật")
def test_parse_dashboard_sample():
    # TODO: gọi hàm parse của SevenElevenScraper trên FIXTURE,
    # assert ra list[OrderToReport] với stt/sale_name đã normalize đúng.
    raise AssertionError("viết test parse khi đã có fixture + selector")
