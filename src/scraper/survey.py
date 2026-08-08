"""Công cụ khảo sát — tự trả lời O5 (dashboard có endpoint JSON nội bộ không?).

Thay vì ngồi đọc tab Network trong DevTools bằng mắt, chạy công cụ này rồi cứ duyệt
dashboard như bình thường. Nó ghi lại mọi request nền, chấm điểm và chỉ ra request
nào nhiều khả năng là "danh sách đơn":

    python -m src.scraper.survey

→ mở bộ lọc «đơn cần báo», bấm sang trang 2, rồi quay lại bấm Enter.

Kết quả: bảng xếp hạng in ra màn hình + file đầy đủ trong debug/ để đọc kỹ.

⚠️ File trong debug/ CHỨA DỮ LIỆU KHÁCH THẬT (tên, SĐT, địa chỉ). Nó nằm trong
.gitignore. Muốn dùng làm fixture test thì phải xoá sạch dữ liệu khách trước.
Bảng in ra màn hình chỉ hiện TÊN TRƯỜNG, không hiện giá trị, nên chụp màn hình gửi
cho nhau được.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

from src.config import get_settings
from src.scraper.session import browser_context


def find_record_list(data) -> tuple[str, int, list[str]] | None:
    """Tìm mảng bản ghi lớn nhất trong một body JSON.

    Trả về (đường dẫn tới mảng, số phần tử, tên các trường) hoặc None.
    Chỉ trả về TÊN TRƯỜNG — không bao giờ trả giá trị, để in ra màn hình an toàn.
    """
    best: tuple[str, int, list[str]] | None = None

    def walk(node, path: str) -> None:
        nonlocal best
        if isinstance(node, list):
            objs = [x for x in node if isinstance(x, dict)]
            if objs and (best is None or len(objs) > best[1]):
                keys: list[str] = []
                for o in objs[:5]:  # gộp khoá của vài bản ghi đầu
                    for k in o:
                        if k not in keys:
                            keys.append(k)
                best = (path or "(gốc)", len(objs), keys)
            for i, item in enumerate(node[:3]):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)

    walk(data, "")
    return best


def score(entry: dict) -> int:
    """Càng nhiều bản ghi càng giống danh sách đơn."""
    return entry.get("record_count") or 0


def attach_recorder(page) -> list[dict]:
    """Gắn bộ ghi nhận vào một trang; trả về danh sách sẽ được điền dần."""
    captured: list[dict] = []

    def on_response(response) -> None:
        try:
            req = response.request
            if req.resource_type not in ("xhr", "fetch"):
                return
            ctype = (response.header_value("content-type") or "").lower()
            entry: dict = {
                "url": response.url,
                "method": req.method,
                "status": response.status,
                "content_type": ctype,
                "post_data": req.post_data,
            }
            if "json" in ctype:
                try:
                    data = response.json()
                except Exception:
                    data = None
                if data is not None:
                    entry["body"] = data
                    found = find_record_list(data)
                    if found:
                        entry["record_path"], entry["record_count"], entry["fields"] = found
            captured.append(entry)
        except Exception as e:  # không để lỗi ghi nhận làm hỏng phiên duyệt
            captured.append({"url": getattr(response, "url", "?"), "error": str(e)})

    page.on("response", on_response)
    return captured


def _capture(context, url: str) -> list[dict]:
    page = context.new_page()
    captured = attach_recorder(page)
    page.goto(url)
    print("Cửa sổ trình duyệt đã mở, đang ghi lại các request nền.")
    print("→ Nếu bị hỏi đăng nhập: đăng nhập bằng tay (chạy `--login` trước sẽ đỡ bước này).")
    print("→ Mở bộ lọc «đơn cần báo», TẢI LẠI TRANG, rồi bấm sang trang 2 nếu có.")
    print("→ Xong quay lại đây bấm Enter.")
    input()
    print(f"\nURL cuối cùng (chép vào NOTES.md): {page.url}")
    return captured


def print_report(captured: list[dict]) -> None:
    with_records = sorted(
        [c for c in captured if c.get("record_count")], key=score, reverse=True
    )
    print(f"\nGhi nhận {len(captured)} request nền (XHR/fetch).")
    if not with_records:
        print("\nKHÔNG thấy request JSON nào trả về danh sách bản ghi.")
        print("→ Nhiều khả năng bảng đơn nằm sẵn trong HTML, phải đọc bằng trình duyệt.")
        print("→ Ghi kết luận này vào O5 trong NOTES.md.")
        return

    print("\n--- ỨNG VIÊN 'DANH SÁCH ĐƠN' (nhiều bản ghi nhất xếp trước) ---")
    for c in with_records[:5]:
        print(f"\n{c['method']} {c['url']}")
        print(f"  {c['record_count']} bản ghi tại `{c['record_path']}`")
        print(f"  Các trường: {', '.join(c['fields'])}")
        if c.get("post_data"):
            print(f"  Dữ liệu gửi lên: {c['post_data'][:200]}")
    print("\n→ Chép URL + tên trường vào mục O5 trong NOTES.md.")
    print("→ Tìm trong danh sách trường xem có STT / tên Sale / mã S không —")
    print("  đó chính là câu trả lời cho O2 và câu hỏi 5.")


def save_capture(captured: list[dict], debug_dir: Path = Path("debug")) -> Path:
    debug_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = debug_dir / f"network-capture-{stamp}.json"
    out.write_text(json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Khảo sát dashboard: bắt endpoint JSON")
    parser.add_argument("--url", help="URL mở đầu (mặc định SEVEN_ELEVEN_URL)")
    args = parser.parse_args(argv)

    settings = get_settings()
    url = args.url or settings.seven_eleven_url
    if not url:
        print("Chưa đặt SEVEN_ELEVEN_URL trong .env và cũng không truyền --url.")
        return 1

    with browser_context(settings, headless=False) as context:
        captured = _capture(context, url)

    print_report(captured)
    out = save_capture(captured)
    print(f"\nBản đầy đủ: {out}")
    print("⚠️ File này chứa dữ liệu khách thật — xoá sạch trước khi dùng làm fixture.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
