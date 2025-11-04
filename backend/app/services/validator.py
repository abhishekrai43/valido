"""Validator stub: apply deterministic rule checks to extracted text.

Replace with the production rules engine in a following phase.
Keep comments short and focused — do not add AI icons or long AI-generated blocks.
"""

from typing import Dict, Optional


def validate_text(text: str, rules: Optional[dict] = None) -> Dict:
    """Return a basic validation report.

    This stub demonstrates the shape of a report. Real validators will return
    per-rule results, confidence scores, and actionable messages.
    """
    report = {
        "summary": {
            "length": len(text or ""),
            "contains_invoice": False,
        },
        "rules": [],
    }

    if text and "invoice" in text.lower():
        report["summary"]["contains_invoice"] = True
        report["rules"].append({"id": "rule_invoice_present", "result": "pass"})
    else:
        report["rules"].append({"id": "rule_invoice_present", "result": "fail"})

    return report
