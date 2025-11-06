from typing import Dict, Optional
from app.utils.logger import get_logger

logger = get_logger("ValidoValidator")
"""Validator stub: apply deterministic rule checks to extracted text.

Replace with the production rules engine in a following phase.
Keep comments short and focused — do not add AI icons or long AI-generated blocks.
"""


def validate_text(text: str, rules: Optional[dict] = None) -> Dict:
    """Return a basic validation report.

    This stub demonstrates the shape of a report. Real validators will return
    per-rule results, confidence scores, and actionable messages.
    """
    try:
        if not isinstance(text, str):
            logger.error("validate_text: input text is not a string")
            return {"error": "Input text must be a string"}
        report = {
            "summary": {
                "length": len(text or ""),
            },
            "rules": [],
        }
        # Legacy stub - validation logic is now handled in worker_tasks.py
        # This function is kept for backwards compatibility
        return report
    except Exception as e:
        logger.error(f"validate_text exception: {type(e).__name__}: {e}")
        return {"error": str(e)}
