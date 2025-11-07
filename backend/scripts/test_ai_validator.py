#!/usr/bin/env python3
"""
Simple local test runner for the AI validator.

Run from the `backend` folder with your virtualenv activated:

    & venv\Scripts\Activate.ps1
    python scripts/test_ai_validator.py

This script loads a sample text and a sample ruleset (matching the expected output
from `ai_stub`) and prints the validation report returned by `validate_text()`.
"""
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path so `app` package imports work when run from backend/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ai_validator import validate_text


SAMPLE_TEXT = """
Invoice
Total Amount: $1,234.56

Signed by: John Doe
Date: 2025-10-10

This is the final invoice.
"""

SAMPLE_RULESET = {
    "name": "General Document Check",
    "source_text": "Check for signature date and total amount > 1000, and ensure it does not contain DRAFT",
    "extractions": [
        {
            "field": "Total Amount",
            "regex_pattern": r"(?:Total\\s+Amount|Amount\\s+Due|Total)[:\\s$€£]*([\\d,]+\\.?\\d{0,2})",
            "strategy": "first",
            "data_type": "float",
        }
    ],
    "validations": [
        {
            "type": "contains_text",
            "description": "The document must contain a signature date.",
            "text": "date",
            "case_sensitive": False,
        },
        {
            "type": "numeric_aggregation",
            "description": "Verify that the Total Amount is greater than 1000.",
            "field_reference": "Total Amount",
            "condition": "min_value",
            "value": 1000.0,
        },
        {
            "type": "not_contains_text",
            "description": "The document must not contain the word 'DRAFT'.",
            "text": "DRAFT",
            "case_sensitive": True,
        },
    ],
}


def main():
    print("Running local AI validator test...\n")
    report = validate_text(SAMPLE_TEXT, {
        "extractions": SAMPLE_RULESET["extractions"],
        "validations": SAMPLE_RULESET["validations"],
    })

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
