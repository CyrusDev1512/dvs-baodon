"""Test công cụ khảo sát O5 — phần phân tích (thuần) và phần bắt request (thật).

Test bắt request dựng một web server giả ngay trên máy, trang của nó gọi một
endpoint JSON giống hệt cách dashboard thật hay làm. Nếu công cụ tìm ra endpoint đó
thì nó cũng sẽ tìm ra endpoint thật — kiểm được trước khi có tài khoản.
"""
from __future__ import annotations

import http.server
import json
import threading

import pytest

from src.scraper.survey import attach_recorder, find_record_list, print_report

ORDERS = [
    {"stt": f"15{i:02d}", "sale": "Nguyễn Thu Hà", "s_code": f"S96{i:02d}",
     "status": 4, "ma_don": f"CC2608{i:02d}S1211"}
    for i in range(12)
]

PAGE = b"""<!doctype html><meta charset="utf-8"><body>dang tai...
<script>fetch('/api/orders?page=1').then(r=>r.json()).then(d=>{
  document.body.textContent = 'xong ' + d.data.rows.length;});</script>"""


class TestFindRecordList:
    def test_finds_nested_array_and_field_names(self):
        body = {"code": 0, "data": {"total": 12, "rows": ORDERS}}
        path, count, fields = find_record_list(body)
        assert path == "data.rows"
        assert count == 12
        assert "stt" in fields and "sale" in fields and "ma_don" in fields

    def test_picks_the_largest_array(self):
        body = {"filters": [{"id": 1}, {"id": 2}], "rows": ORDERS}
        path, count, _ = find_record_list(body)
        assert path == "rows" and count == 12

    def test_none_when_no_records(self):
        assert find_record_list({"code": 0, "message": "ok"}) is None
        assert find_record_list([1, 2, 3]) is None      # mảng số, không phải bản ghi

    def test_returns_only_field_names_never_values(self):
        """Bảng in ra màn hình phải an toàn để chụp gửi cho nhau."""
        _, _, fields = find_record_list({"rows": ORDERS})
        blob = " ".join(fields)
        assert "Nguyễn Thu Hà" not in blob and "CC2608" not in blob


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (tên do thư viện chuẩn quy định)
        if self.path.startswith("/api/orders"):
            payload = json.dumps({"code": 0, "data": {"total": 12, "rows": ORDERS}})
            body = payload.encode()
            ctype = "application/json"
        else:
            body, ctype = PAGE, "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # tắt log ra stderr khi chạy test
        pass


@pytest.fixture
def fake_dashboard():
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


def test_recorder_catches_the_json_endpoint(fake_dashboard, capsys):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            pytest.skip(f"chưa cài chromium: {e}")
        try:
            page = browser.new_page()
            captured = attach_recorder(page)
            page.goto(fake_dashboard)
            page.wait_for_function("document.body.textContent.startsWith('xong')")
        finally:
            browser.close()

    hits = [c for c in captured if c.get("record_count")]
    assert len(hits) == 1, f"phải tìm ra đúng 1 endpoint danh sách, được {captured}"
    hit = hits[0]
    assert "/api/orders" in hit["url"] and hit["method"] == "GET"
    assert hit["record_count"] == 12 and hit["record_path"] == "data.rows"
    assert "stt" in hit["fields"]

    print_report(captured)
    out = capsys.readouterr().out
    assert "/api/orders" in out and "12 bản ghi" in out
    assert "Nguyễn Thu Hà" not in out  # báo cáo không lộ dữ liệu khách


def test_report_says_so_when_there_is_no_json_endpoint(capsys):
    print_report([{"url": "http://x/ping", "method": "GET", "status": 200}])
    out = capsys.readouterr().out
    assert "KHÔNG thấy" in out and "HTML" in out
