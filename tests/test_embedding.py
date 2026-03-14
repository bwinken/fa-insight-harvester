"""Unit tests for app.services.embedding — build_case_text (pure function)."""

from unittest.mock import MagicMock

from app.services.embedding import build_case_text


def _make_case(**kwargs):
    """Create a mock FACase with given field values."""
    case = MagicMock()
    defaults = {
        "customer": None,
        "device": None,
        "model": None,
        "defect_mode": None,
        "defect_rate_raw": None,
        "fab_assembly": None,
        "fa_status": None,
        "follow_up": None,
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(case, k, v)
    return case


class TestBuildCaseText:
    def test_all_fields(self):
        case = _make_case(
            customer="ACME",
            device="SensorX",
            model="M100",
            defect_mode="crack",
            defect_rate_raw="0.5%",
            fab_assembly="FAB-1",
            fa_status="ongoing",
            follow_up="retest",
        )
        text = build_case_text(case)
        assert "Customer: ACME" in text
        assert "Device: SensorX" in text
        assert "Model: M100" in text
        assert "Defect Mode: crack" in text
        assert "Defect Rate: 0.5%" in text
        assert "FAB/Assembly: FAB-1" in text
        assert "FA Status: ongoing" in text
        assert "Follow Up: retest" in text
        # Fields are joined with pipe
        assert " | " in text

    def test_partial_fields(self):
        case = _make_case(customer="ACME", defect_mode="crack")
        text = build_case_text(case)
        assert text == "Customer: ACME | Defect Mode: crack"

    def test_empty_case(self):
        case = _make_case()
        text = build_case_text(case)
        assert text == ""

    def test_single_field(self):
        case = _make_case(customer="ACME")
        text = build_case_text(case)
        assert text == "Customer: ACME"
        assert " | " not in text
