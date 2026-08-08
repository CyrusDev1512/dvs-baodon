"""Test danh bạ Sale — trọng tâm là các kiểu tên lệch nhau giữa hai nguồn."""
from __future__ import annotations

import pytest

from src.sale_directory import (
    AmbiguousSale,
    CsvSaleDirectory,
    OpenSaleDirectory,
    SaleNotFound,
    build_directory,
    loose_key,
    match_key,
)

CSV = """sale_name,messenger_link,aliases,note
Nguyễn Thu Hà,https://m.me/thuha,Nguyen Thu Ha;Thu Hà,
Trần Minh,https://m.me/tranminh,,
Lê Thị Bích Ngọc,https://m.me/bichngoc,,nghỉ phép
"""


@pytest.fixture
def directory(tmp_path):
    p = tmp_path / "sales.csv"
    p.write_text(CSV, encoding="utf-8")
    return CsvSaleDirectory(p)


class TestKeys:
    def test_match_key_ignores_case_and_extra_spaces(self):
        assert match_key("  NGUYỄN   thu hà ") == match_key("Nguyễn Thu Hà")

    def test_loose_key_drops_vietnamese_diacritics(self):
        assert loose_key("Nguyễn Thu Hà") == "nguyen thu ha"
        assert loose_key("Đỗ Lan Anh") == "do lan anh"


class TestLookup:
    def test_exact_name(self, directory):
        assert directory.lookup("Trần Minh").link == "https://m.me/tranminh"

    def test_tolerates_case_and_whitespace(self, directory):
        assert directory.lookup("  trần  MINH ").link == "https://m.me/tranminh"

    def test_name_without_diacritics_still_found(self, directory):
        """Dashboard hay hiển thị tên không dấu."""
        assert directory.lookup("Tran Minh").link == "https://m.me/tranminh"

    def test_alias_column(self, directory):
        assert directory.lookup("Thu Hà").link == "https://m.me/thuha"

    def test_unknown_sale_raises_with_actionable_message(self, directory):
        with pytest.raises(SaleNotFound) as e:
            directory.lookup("Hoàng Văn Mới")
        assert "Hoàng Văn Mới" in str(e.value) and "thêm Sale này" in str(e.value)

    def test_extra_columns_and_notes_are_kept(self, directory):
        assert directory.lookup("Lê Thị Bích Ngọc").note == "nghỉ phép"

    def test_len_counts_distinct_people_not_aliases(self, directory):
        assert len(directory) == 3


class TestAmbiguity:
    def test_two_people_same_name_never_guessed(self, tmp_path):
        p = tmp_path / "s.csv"
        p.write_text("sale_name,messenger_link\nTrần Minh,https://m.me/a\n"
                     "Trần Minh,https://m.me/b\n", encoding="utf-8")
        with pytest.raises(AmbiguousSale) as e:
            CsvSaleDirectory(p).lookup("Trần Minh")
        assert "2 người" in str(e.value)

    def test_diacritics_collision_is_ambiguous_not_a_guess(self, tmp_path):
        """«Hà» và «Hạ» bỏ dấu đều thành «ha» — không được chọn bừa."""
        p = tmp_path / "s.csv"
        p.write_text("sale_name,messenger_link\nNguyễn Hà,https://m.me/ha\n"
                     "Nguyễn Hạ,https://m.me/hb\n", encoding="utf-8")
        d = CsvSaleDirectory(p)
        assert d.lookup("Nguyễn Hà").link == "https://m.me/ha"   # đúng dấu vẫn ra
        with pytest.raises(AmbiguousSale):
            d.lookup("Nguyen Ha")                                # không dấu → mơ hồ


class TestFileHandling:
    def test_bom_from_google_sheet_export(self, tmp_path):
        p = tmp_path / "s.csv"
        p.write_text(CSV, encoding="utf-8-sig")     # Sheet xuất ra có BOM
        assert CsvSaleDirectory(p).lookup("Trần Minh").link == "https://m.me/tranminh"

    def test_missing_column_says_which_one(self, tmp_path):
        p = tmp_path / "s.csv"
        p.write_text("ten_sale,link\nA,B\n", encoding="utf-8")
        with pytest.raises(ValueError) as e:
            CsvSaleDirectory(p)
        assert "sale_name" in str(e.value) and "messenger_link" in str(e.value)

    def test_rows_without_link_are_skipped(self, tmp_path):
        p = tmp_path / "s.csv"
        p.write_text("sale_name,messenger_link\nChưa Có Link,\nTrần Minh,https://m.me/x\n",
                     encoding="utf-8")
        d = CsvSaleDirectory(p)
        assert len(d) == 1
        with pytest.raises(SaleNotFound):
            d.lookup("Chưa Có Link")

    def test_shipped_example_file_is_valid(self):
        """sales.example.csv trong repo phải mở được — người dùng copy từ đó."""
        from pathlib import Path

        from src.config import PROJECT_ROOT

        d = CsvSaleDirectory(Path(PROJECT_ROOT) / "sales.example.csv")
        assert len(d) == 5
        assert d.lookup("Nguyen Thu Ha").channel == "messenger"


def test_build_directory_falls_back_to_open(tmp_path):
    assert isinstance(build_directory(None), OpenSaleDirectory)
    assert build_directory(None).lookup("Ai Đó").channel == "dryrun"
    p = tmp_path / "s.csv"
    p.write_text(CSV, encoding="utf-8")
    assert isinstance(build_directory(p), CsvSaleDirectory)
