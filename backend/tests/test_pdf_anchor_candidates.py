import pathlib

from app.services.parser import extract_text_from_bytes
from app.services.validator import validate_text
from app.services.pdf_layout.candidate_finder import find_anchor_candidates


def test_candidate_finder_returns_candidates_for_pan():
    pdf_path = pathlib.Path(r"D:\\Valido\\24-25ITRPRIYANKA.pdf")
    if not pdf_path.exists():
        # Skip in CI / environments without the sample PDF
        return

    pdf_bytes = pdf_path.read_bytes()
    candidates = find_anchor_candidates(pdf_bytes=pdf_bytes, anchor_text="PAN", max_pages=2)

    assert isinstance(candidates, list)
    assert len(candidates) >= 1
    assert candidates[0].extracted_value


def test_selection_target_is_honored_for_basic_salary():
    """Regression: selecting 2nd 'Basic' occurrence must extract ₹87,760.00 (payslip sample)."""
    pdf_path = pathlib.Path(r"D:\\Valido\\Payslip_AbhishekRai_Aug-2025.pdf")
    if not pdf_path.exists():
        # Skip in CI / environments without the sample PDF
        return

    pdf_bytes = pdf_path.read_bytes()
    text = extract_text_from_bytes(pdf_bytes) or ""

    # This selectionTarget corresponds to the 'Basic ₹87,760.00' token on page 1.
    rules = {
        "fields": [
            {
                "name": "Basic Salary",
                "lookFor": "Basic",
                "strategy": "first",
                "selectionTarget": {
                    "page": 1,
                    "occurrenceIndexOnPage": 1,
                    "anchorBBox": {
                        "x0": 283.323,
                        "top": 196.0855,
                        "x1": 306.5595,
                        "bottom": 206.5855,
                    },
                },
            }
        ]
    }

    report = validate_text(text, rules=rules, pdf_bytes=pdf_bytes)
    assert report["extractions"].get("Basic Salary") == "₹87,760.00"
