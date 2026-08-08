"""Tra Sale phụ trách → nơi gửi tin (danh bạ Sale).

Trong quy trình tay, đây là bước nhân viên mở Google Sheet "danh sách Sale + link
Messenger" (bao-don-flow.md §S4, bước E1-E2). Dashboard chỉ cho biết TÊN Sale, còn
gửi cho ai thì phải tra ở đây.

Phần khó không phải đọc file mà là TÊN KHÔNG KHỚP NHAU:
- Sale mới chưa có trong danh sách
- Tên viết khác nhau giữa hai nguồn: thừa khoảng trắng, hoa/thường, thiếu dấu
- Hai Sale trùng tên

Cả ba đều dẫn tới "báo nhầm người" hoặc "không biết báo ai". Theo nguyên tắc *thà
không báo còn hơn báo sai*: chỉ gửi khi tra ra ĐÚNG MỘT người; mọi trường hợp khác
ném lỗi để reconcile ghi sổ ngoại lệ và bỏ qua đơn đó cho người xử lý.

Hiện đọc từ file CSV (xuất từ Google Sheet). Khi có link + quyền truy cập Sheet trực
tiếp thì viết thêm một lớp đọc Sheet, phần khớp tên bên dưới giữ nguyên.
"""
from __future__ import annotations

import csv
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from src.scraper.interface import norm_sale_name


@dataclass(frozen=True)
class SaleContact:
    name: str            # tên chuẩn như ghi trong danh sách
    channel: str         # 'messenger'
    link: str            # link/ID để nhắn
    note: str = ""


class SaleLookupError(Exception):
    """Không tra ra đúng một người để gửi."""


class SaleNotFound(SaleLookupError):
    pass


class AmbiguousSale(SaleLookupError):
    pass


def match_key(name: str) -> str:
    """Khoá so khớp chính: bỏ khoảng trắng thừa, không phân biệt hoa/thường."""
    return norm_sale_name(name).casefold()


def loose_key(name: str) -> str:
    """Khoá so khớp nới lỏng: bỏ luôn dấu tiếng Việt.

    Dùng làm lớp DỰ PHÒNG, và chỉ chấp nhận khi ra đúng một ứng viên — vì bỏ dấu
    có thể làm hai tên khác nhau trông giống nhau (Hà và Hạ đều thành "ha")."""
    s = match_key(name).replace("đ", "d")
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if not unicodedata.combining(c)
    )


class SaleDirectory(ABC):
    @abstractmethod
    def lookup(self, sale_name: str) -> SaleContact:
        """Trả về nơi gửi tin cho Sale này; không chắc chắn thì raise."""


class OpenSaleDirectory(SaleDirectory):
    """Danh bạ giả cho chạy thử: chấp nhận mọi tên. KHÔNG dùng khi gửi thật."""

    def lookup(self, sale_name: str) -> SaleContact:
        return SaleContact(name=sale_name, channel="dryrun",
                           link=f"dryrun://sale/{norm_sale_name(sale_name)}")


class CsvSaleDirectory(SaleDirectory):
    """Đọc danh bạ từ CSV xuất ra từ Google Sheet.

    Cột bắt buộc: `sale_name`, `messenger_link`.
    Cột tuỳ chọn: `aliases` (các cách viết khác, phân cách bằng dấu `;`), `note`.
    """

    REQUIRED = ("sale_name", "messenger_link")

    def __init__(self, path: Path):
        self.path = path
        self._exact: dict[str, list[SaleContact]] = {}
        self._loose: dict[str, list[SaleContact]] = {}
        self._load()

    def _load(self) -> None:
        # utf-8-sig: file xuất từ Google Sheet thường có BOM ở đầu.
        with self.path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            missing = [c for c in self.REQUIRED if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(
                    f"{self.path} thiếu cột {', '.join(missing)}."
                    f" Cần các cột: {', '.join(self.REQUIRED)}"
                )
            for row in reader:
                name = norm_sale_name(row.get("sale_name") or "")
                link = (row.get("messenger_link") or "").strip()
                if not name or not link:
                    continue  # dòng trống hoặc chưa điền link → coi như chưa có
                contact = SaleContact(name=name, channel="messenger", link=link,
                                      note=(row.get("note") or "").strip())
                names = [name] + [
                    a for a in (row.get("aliases") or "").split(";") if a.strip()
                ]
                for n in names:
                    self._exact.setdefault(match_key(n), []).append(contact)
                    self._loose.setdefault(loose_key(n), []).append(contact)

    def __len__(self) -> int:
        return len({c.link for lst in self._exact.values() for c in lst})

    def lookup(self, sale_name: str) -> SaleContact:
        for table, how in ((self._exact, match_key), (self._loose, loose_key)):
            found = table.get(how(sale_name), [])
            unique = {c.link: c for c in found}
            if len(unique) == 1:
                return next(iter(unique.values()))
            if len(unique) > 1:
                names = ", ".join(sorted(c.name for c in unique.values()))
                raise AmbiguousSale(
                    f"tên «{sale_name}» khớp {len(unique)} người trong danh bạ"
                    f" ({names}) — không đoán, cần người phân biệt"
                )
        raise SaleNotFound(
            f"«{sale_name}» không có trong danh bạ {self.path.name}"
            " — thêm Sale này vào danh sách rồi chạy lại"
        )


def build_directory(path: Path | None) -> SaleDirectory:
    """Có đường dẫn danh bạ thì dùng, không thì dùng bản chạy thử."""
    return CsvSaleDirectory(path) if path else OpenSaleDirectory()
