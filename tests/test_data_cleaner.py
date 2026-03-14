"""Unit tests for app.services.data_cleaner — pure functions, no DB needed."""

from app.schemas.fa_case import VLMExtractedData
from app.services.data_cleaner import clean_date, clean_extracted_data, parse_lots


# ── clean_date ─────────────────────────────────────────────────────────


class TestCleanDate:
    def test_removes_bracketed_noise(self):
        assert clean_date("2026/03/02[13829]") == "2026/03/02"

    def test_standard_date_unchanged(self):
        assert clean_date("2026/03/02") == "2026/03/02"

    def test_dash_separator(self):
        assert clean_date("2026-03-02") == "2026-03-02"

    def test_dot_separator(self):
        assert clean_date("2026.03.02") == "2026.03.02"

    def test_date_with_surrounding_text(self):
        assert clean_date("report 2026/01/15 submitted") == "2026/01/15"

    def test_none_returns_none(self):
        assert clean_date(None) is None

    def test_empty_string_returns_none(self):
        assert clean_date("") is None

    def test_no_date_pattern_returns_cleaned_string(self):
        assert clean_date("no date here") == "no date here"

    def test_multiple_brackets_removed(self):
        assert clean_date("2026/01/01[123][456]") == "2026/01/01"


# ── parse_lots ─────────────────────────────────────────────────────────


class TestParseLots:
    def test_comma_separated(self):
        assert parse_lots("LOT-A, LOT-B, LOT-C") == ["LOT-A", "LOT-B", "LOT-C"]

    def test_semicolon_separated(self):
        assert parse_lots("LOT-A; LOT-B") == ["LOT-A", "LOT-B"]

    def test_newline_separated(self):
        assert parse_lots("LOT-A\nLOT-B\nLOT-C") == ["LOT-A", "LOT-B", "LOT-C"]

    def test_mixed_separators(self):
        result = parse_lots("LOT-A, LOT-B; LOT-C\nLOT-D")
        assert result == ["LOT-A", "LOT-B", "LOT-C", "LOT-D"]

    def test_none_returns_empty(self):
        assert parse_lots(None) == []

    def test_empty_string_returns_empty(self):
        assert parse_lots("") == []

    def test_strips_whitespace(self):
        assert parse_lots("  LOT-A ,  LOT-B  ") == ["LOT-A", "LOT-B"]

    def test_single_lot(self):
        assert parse_lots("LOT-ONLY") == ["LOT-ONLY"]

    def test_empty_segments_ignored(self):
        assert parse_lots("LOT-A,,LOT-B") == ["LOT-A", "LOT-B"]


# ── clean_extracted_data ───────────────────────────────────────────────


class TestCleanExtractedData:
    def test_full_data(self):
        data = VLMExtractedData(
            date="2026/03/02[13829]",
            customer="  ACME Corp  ",
            device="  Sensor-X  ",
            model="  M100  ",
            defect_mode=" crack ",
            defect_rate="0.5%",
            defect_lots="LOT-A, LOT-B",
            fab_assembly=" FAB-1 ",
            fa_status=" ongoing ",
            follow_up=" retest next week ",
        )
        result = clean_extracted_data(data)
        assert result["date"] == "2026/03/02"
        assert result["customer"] == "ACME Corp"
        assert result["device"] == "Sensor-X"
        assert result["model"] == "M100"
        assert result["defect_mode"] == "crack"
        assert result["defect_rate_raw"] == "0.5%"
        assert result["defect_lots"] == ["LOT-A", "LOT-B"]
        assert result["fab_assembly"] == "FAB-1"
        assert result["fa_status"] == "ongoing"
        assert result["follow_up"] == "retest next week"

    def test_empty_fields_become_none(self):
        data = VLMExtractedData(
            date=None,
            customer="",
            device="   ",
            model=None,
        )
        result = clean_extracted_data(data)
        assert result["date"] is None
        assert result["customer"] is None
        assert result["device"] is None
        assert result["model"] is None

    def test_minimal_data(self):
        data = VLMExtractedData()
        result = clean_extracted_data(data)
        assert result["date"] is None
        assert result["customer"] is None
        assert result["defect_lots"] == []
