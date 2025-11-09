from typing import Dict, Optional, List, Any, Tuple
import re
from app.utils.logger import get_logger

logger = get_logger("ValidoValidator")

# ------ DATE REGEX (broad) ------
# Covers:
#  - 2025-03-15, 2025/03/15
#  - 15/03/2025, 5-3-25, 05/03/25
#  - March 5, 2025  | Mar 5th 2025 | 5 March 2025
#  - Ordinals (1st, 2nd, 3rd)
#  - Month abbreviations and full names, optional comma
_MONTHS = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|sept|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_ORDINAL = r"(?:st|nd|rd|th)?"
# numeric date formats
_NUMERIC_DATE = r"(?:\b\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4}\b|\b\d{4}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{1,2}\b)"
# month name formats
_MONTH_NAME_DATE = rf"(?:\b\d{{1,2}}{_ORDINAL}?\s+(?:of\s+)?{_MONTHS}(?:,?\s*\d{{2,4}})?\b|\b{_MONTHS}\s+\d{{1,2}}{_ORDINAL}?(?:,?\s*\d{{2,4}})?\b)"
# combined pattern
_DATE_PATTERN = re.compile(rf"({_NUMERIC_DATE}|{_MONTH_NAME_DATE})", re.IGNORECASE)

# ------ SIGNATURE PATTERNS ------
# Keywords and common variants used in legal/financial docs
_SIGNATURE_KEYWORDS = [
    r"signed(?:\s+by)?", r"signature", r"signed\s*:", r"signatory", r"authoris(?:ed|ed) signatory",
    r"authorised", r"authorised\s*signatory", r"electronically signed", r"digitally signed",
    r"/s/", r"/sig/", r"sig\.", r"per\s*:", r"for\s+the", r"on behalf of", r"witness", r"accepted by"
]
_SIGNATURE_PATTERN = re.compile(rf"\b({'|'.join([k for k in _SIGNATURE_KEYWORDS])})\b", re.IGNORECASE)

# Attempt to capture "Signed by John Doe" style (name capture)
_SIGNATURE_WITH_NAME = re.compile(
    rf"\b(?:signed(?:\s+by)?|signature\s*[:]\s*|sig\.\s*)(?:\s+by\s+)?([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'`.\- ]{{1,120}})",
    re.IGNORECASE
)


def _find_date(text: str) -> Optional[str]:
    if not text:
        return None
    m = _DATE_PATTERN.search(text)
    return m.group(0).strip() if m else None


def _find_all_dates(text: str) -> List[str]:
    if not text:
        return []
    return [m.group(0).strip() for m in _DATE_PATTERN.finditer(text)]


def _find_signature_snippet(text: str) -> Optional[str]:
    if not text:
        return None
    # prioritized: try to capture "Signed by <Name>"
    m_name = _SIGNATURE_WITH_NAME.search(text)
    if m_name:
        name = m_name.group(1).strip()
        start = max(0, m_name.start() - 30)
        end = min(len(text), m_name.end() + 30)
        return text[start:end].strip()
    # fallback: find keyword and return context
    m = _SIGNATURE_PATTERN.search(text)
    if m:
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 80)
        return text[start:end].strip()
    return None


def _match_text_rule(text: str, rule: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    if not rule or not isinstance(rule, dict):
        return "No", None
    needle = rule.get("text", "")
    if not needle:
        return "No", None
    case_sensitive = bool(rule.get("case_sensitive", False))
    hay = text if case_sensitive else (text or "").lower()
    key = needle if case_sensitive else needle.lower()
    idx = hay.find(key)
    if idx == -1:
        return "No", None
    start = max(0, idx - 40)
    end = min(len(text), idx + len(needle) + 40)
    snippet = text[start:end].strip()
    return "Yes", snippet


def _match_not_contain_rule(text: str, rule: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    if not rule or not isinstance(rule, dict):
        return "Pass", None
    needle = rule.get("text", "")
    if not needle:
        return "Pass", None
    case_sensitive = bool(rule.get("case_sensitive", False))
    hay = text if case_sensitive else (text or "").lower()
    key = needle if case_sensitive else needle.lower()
    idx = hay.find(key)
    if idx == -1:
        return "Pass", None
    start = max(0, idx - 40)
    end = min(len(text), idx + len(needle) + 40)
    snippet = text[start:end].strip()
    return "Fail", snippet


def _extract_field(text: str, field_name: str, strategy: str = "first", look_for: Optional[str] = None) -> str:
    """
    Extract a field value from text.
    If look_for is provided, it searches for that exact text followed by the value.
    Otherwise, it falls back to searching by field_name.
    """
    if not text:
        return ""
    
    # Use look_for if provided, otherwise fall back to field_name
    search_term = look_for if look_for else field_name
    if not search_term:
        return ""
    
    # Escape special regex characters in the search term
    escaped_term = re.escape(search_term)
    
    patterns = [
        # Pattern 1: "SearchTerm: value" or "SearchTerm :value"
        rf"{escaped_term}\s*[:]\s*([^\n\r]+)",
        # Pattern 2: "SearchTerm value" (captures until double space or newline)
        rf"{escaped_term}\s+([A-Za-z0-9₹$€£¥₨,.\/\-]+[^\n\r]*?)(?:\s{{2,}}|\n|$)",
        # Pattern 3: "SearchTerm" on one line, value on next
        rf"{escaped_term}\s*\n\s*([^\n\r]+)",
    ]
    
    matches: List[str] = []
    for pat in patterns:
        try:
            for m in re.finditer(pat, text, flags=re.IGNORECASE if not look_for else 0):
                v = m.group(1).strip()
                # Clean up extra whitespace
                v = re.sub(r"\s{2,}", " ", v)
                if v and v not in matches:
                    matches.append(v)
        except re.error:
            continue
    
    if not matches:
        return ""
    
    if strategy == "last":
        return matches[-1]
    if strategy == "all":
        return " | ".join(matches)
    return matches[0]


def validate_text(text: str, rules: Optional[dict] = None) -> Dict:
    try:
        if not isinstance(text, str):
            logger.error("validate_text: input text is not a string")
            return {"error": "Input text must be a string"}

        report: Dict[str, Any] = {
            "summary": {"length": len(text or "")},
            "validations": {},
            "contains": [],
            "not_contains": [],
            "extractions": {},
            "extraction_log": [],  # Detailed log for debugging
            "pdf_text_preview": text[:1000] if text else ""  # First 1000 chars of PDF
        }

        validations = {}
        must_contain = []
        must_not_contain = []
        fields = []

        if isinstance(rules, dict):
            validations = rules.get("validations", {}) or {}
            if rules.get("validate_signed"):
                validations["signed"] = True
            if rules.get("validate_dated"):
                validations["dated"] = True
            if rules.get("validate_signed_and_dated"):
                validations["signed_and_dated"] = True
            maybe_must = validations.get("must_contain") or rules.get("must_contain")
            if maybe_must:
                must_contain = maybe_must if isinstance(maybe_must, list) else [maybe_must]
            maybe_not = validations.get("must_not_contain") or rules.get("must_not_contain")
            if maybe_not:
                must_not_contain = maybe_not if isinstance(maybe_not, list) else [maybe_not]
            fields = rules.get("fields") or []

        if validations.get("signed") or validations.get("signed_and_dated"):
            snippet = _find_signature_snippet(text)
            report["validations"]["signed"] = {"result": "Yes" if snippet else "No", "snippet": snippet}

        if validations.get("dated") or validations.get("signed_and_dated"):
            found_date = _find_date(text)
            all_dates = _find_all_dates(text)
            report["validations"]["dated"] = {"result": "Yes" if found_date else "No", "date": found_date, "all_dates": all_dates}

        for r in must_contain:
            if isinstance(r, str):
                rdict = {"text": r, "case_sensitive": False}
            else:
                rdict = r
            res, snip = _match_text_rule(text, rdict)
            report["contains"].append({"rule": rdict, "result": res, "snippet": snip})

        for r in must_not_contain:
            if isinstance(r, str):
                rdict = {"text": r, "case_sensitive": False}
            else:
                rdict = r
            res, snip = _match_not_contain_rule(text, rdict)
            report["not_contains"].append({"rule": rdict, "result": res, "snippet": snip})

        if isinstance(fields, list):
            for f in fields:
                if isinstance(f, dict):
                    name = f.get("name") or f.get("field") or ""
                    strat = f.get("strategy", "first")
                    look_for = f.get("lookFor") or f.get("look_for")
                else:
                    name = str(f)
                    strat = "first"
                    look_for = None
                if not name:
                    continue
                
                # Extract value
                value = _extract_field(text, name, strat, look_for)
                display = name.replace("_", " ").title()
                report["extractions"][display] = value
                
                # Add detailed log entry
                log_entry = {
                    "field_name": name,
                    "look_for_text": look_for or name,
                    "strategy": strat,
                    "extracted_value": value,
                    "found": value is not None and value != ""
                }
                
                # Find where the lookFor text appears in PDF
                if look_for:
                    search_text = look_for.lower() if not look_for else look_for
                    idx = text.lower().find(search_text.lower()) if text else -1
                    if idx != -1:
                        # Get 200 chars context around the match
                        start = max(0, idx - 100)
                        end = min(len(text), idx + len(search_text) + 100)
                        log_entry["context"] = text[start:end]
                        log_entry["match_position"] = idx
                    else:
                        log_entry["context"] = "Text not found in PDF"
                        log_entry["match_position"] = -1
                
                report["extraction_log"].append(log_entry)

        return report

    except Exception as e:
        logger.error(f"validate_text exception: {type(e).__name__}: {e}")
        return {"error": str(e)}
