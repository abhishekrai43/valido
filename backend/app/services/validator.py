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


def _extract_clean_number(value: str) -> Optional[float]:
    """
    Extract clean number from text with UNIVERSAL currency symbols and formatting.
    Handles:
    - Currency: ₹, $, €, £, ¥, ₨, ¢, ₩, ₪, ₣, etc.
    - Indian format: 10,00,000 or 1,00,00,000
    - Western format: 1,000,000 or 10,000,000
    - Mixed: $1,234.56 or ₹1,23,456.78
    - Text suffixes: "Only", "per annum", "/-", etc.
    """
    if not value:
        return None
    
    # Remove all currency symbols (covers all major currencies)
    cleaned = re.sub(r'[₹$€£¥₨¢₩₪₣\s]', '', value)
    
    # Remove trailing text like "Only", "per annum", "/-" etc
    # But keep numbers, commas, periods, and dashes
    cleaned = re.sub(r'[a-zA-Z/-]+$', '', cleaned)
    
    # Remove ALL commas (works for both Indian and Western formats)
    cleaned = cleaned.replace(',', '')
    
    # Handle negative numbers and parentheses (accounting format)
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _validate_field_value(value: str, field_config: dict) -> dict:
    """Validate extracted field value against validation rules"""
    validations = field_config.get('validations', [])
    field_type = field_config.get('type', 'text')
    results = []
    all_passed = True
    
    if not validations or not value:
        return {'valid': True, 'checks': []}
    
    for validation in validations:
        val_type = validation.get('type')
        val_value = validation.get('value')
        
        if field_type == 'text':
            if val_type == 'minLength':
                passes = len(value) >= int(val_value)
                results.append({
                    'type': 'minLength',
                    'passes': passes,
                    'expected': val_value,
                    'actual': len(value)
                })
                all_passed = all_passed and passes
                
            elif val_type == 'maxLength':
                passes = len(value) <= int(val_value)
                results.append({
                    'type': 'maxLength',
                    'passes': passes,
                    'expected': val_value,
                    'actual': len(value)
                })
                all_passed = all_passed and passes
                
            elif val_type == 'pattern':
                passes = bool(re.search(val_value, value))
                results.append({
                    'type': 'pattern',
                    'passes': passes,
                    'pattern': val_value
                })
                all_passed = all_passed and passes
        
        elif field_type == 'number':
            clean_num = _extract_clean_number(value)
            if clean_num is not None:
                if val_type == 'min':
                    passes = clean_num >= float(val_value)
                    results.append({
                        'type': 'min',
                        'passes': passes,
                        'expected': val_value,
                        'actual': clean_num
                    })
                    all_passed = all_passed and passes
                    
                elif val_type == 'max':
                    passes = clean_num <= float(val_value)
                    results.append({
                        'type': 'max',
                        'passes': passes,
                        'expected': val_value,
                        'actual': clean_num
                    })
                    all_passed = all_passed and passes
                    
                elif val_type == 'equals':
                    passes = abs(clean_num - float(val_value)) < 0.01  # Allow tiny floating point differences
                    results.append({
                        'type': 'equals',
                        'passes': passes,
                        'expected': val_value,
                        'actual': clean_num
                    })
                    all_passed = all_passed and passes
            else:
                # Could not parse as number
                results.append({
                    'type': val_type,
                    'passes': False,
                    'error': 'Could not parse as number'
                })
                all_passed = False
    
    return {'valid': all_passed, 'checks': results}


def _compute_formula(formula: str, extractions: dict) -> Optional[str]:
    """
    Evaluate a mathematical formula with field references and math functions.
    
    Args:
        formula: Expression like "GrossSalary - PF - Tax" or "GrossSalary * 10%" 
                 (no curly braces, just field names)
        extractions: Dict of extracted field values
    
    Returns:
        Computed result as string, or None if evaluation fails
    
    Supports:
        - Basic operators: + - * /
        - Percentage: % (converts to /100, e.g., "10%" becomes "0.10")
        - Math functions: log, sqrt, abs, round, floor, ceil, sin, cos, tan, exp, pow
    
    Example:
        formula = "GrossSalary - GrossSalary * 10%"
        extractions = {"Gross Salary": "₹ 1,68,979"}
        result = "₹ 1,52,081"  (168979 - 168979*0.10)
    """
    import math
    
    if not formula or not extractions:
        return None
    
    # Detect if any source field has currency
    has_currency = False
    currency_symbol = ''
    
    # Build expression by finding field names and replacing with values
    expression = formula
    
    # Sort field names by length (longest first) to avoid partial matches
    field_names = sorted(extractions.keys(), key=len, reverse=True)
    
    for field_name in field_names:
        field_value = extractions.get(field_name)
        if not field_value:
            continue
        
        # Detect currency
        if not has_currency:
            for symbol in ['₹', '$', '€', '£', '¥', '₨', '¢', '₩', '₪', '₣']:
                if symbol in str(field_value):
                    has_currency = True
                    currency_symbol = symbol
                    break
        
        # Extract clean number
        clean_num = _extract_clean_number(str(field_value))
        if clean_num is None:
            continue
        
        # Replace field name with the clean number
        # Use word boundaries to avoid partial replacements
        expression = re.sub(r'\b' + re.escape(field_name) + r'\b', str(clean_num), expression)
    
    # Handle percentage notation: "10%" becomes "0.10"
    # Find patterns like "number%" and replace with "number/100"
    expression = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'(\1/100)', expression)
    
    # Evaluate the mathematical expression
    try:
        # Create safe evaluation environment with math functions
        safe_dict = {
            "__builtins__": {},
            "log": math.log,
            "log10": math.log10,
            "sqrt": math.sqrt,
            "abs": abs,
            "round": round,
            "floor": math.floor,
            "ceil": math.ceil,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "exp": math.exp,
            "pow": pow,
            "min": min,
            "max": max,
        }
        
        result = eval(expression, safe_dict, {})
        
        # Format result
        if has_currency:
            # Format with commas
            if result >= 0:
                formatted = f"{currency_symbol} {result:,.0f}"
            else:
                formatted = f"-{currency_symbol} {abs(result):,.0f}"
            return formatted
        else:
            return str(round(result, 2))
            
    except Exception as e:
        logger.error(f"Failed to evaluate formula '{formula}': {e}")
        return None


def _extract_field(
    text: str, 
    field_name: str, 
    strategy: str = "first", 
    look_for: Optional[str] = None,
    column: Optional[str] = None  # Column name from table header OR "first"/"last"/"all"
) -> str:
    """
    Extract field value from text with optional column selection for tables.
    
    Args:
        text: Full document text
        field_name: Name of the field (fallback if look_for not provided)
        strategy: "first", "last", or "all" for multiple matches
        look_for: Specific text to search for (overrides field_name)
        column: For multi-column tables:
            - Column header name: "Per Month", "Monthly", "Annual", etc.
            - Position: "first", "second", "last" 
            - Index: "1", "2", "3" (1-based)
            - None: returns all columns (may be multiple values)
    
    Returns:
        Extracted value as string. For multi-column matches without column specified,
        returns all values space-separated.
    
    Example:
        Table:
                            Per Month    Per Annum
        (-) PF Employee     ₹ 1,800      ₹ 21,600
        
        column="Per Month" → "₹ 1,800"
        column="Per Annum" → "₹ 21,600"
        column="first" → "₹ 1,800"
        column=None → "₹ 1,800 ₹ 21,600"
    """
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
    
    # Check if search_term already ends with colon
    has_colon = search_term.rstrip().endswith(':')
    
    patterns = [
        # Pattern 1a: "SearchTerm: value" or "SearchTerm value" - UNIVERSAL colon-separated pattern
        # If lookFor has colon, match it directly; otherwise match optional period/space then colon
        # Captures everything until newline or double-space (common in tables)
        rf"{escaped_term}\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)" if has_colon else rf"{escaped_term}[.\s]*[:]\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)",
        
        # Pattern 1b: "SearchTerm value" - for descriptive phrases (no colon)
        # Stops at common transition words - UNIVERSAL for any language
        rf"{escaped_term}\s+([A-Z][^\n\r]+?)(?:\s+(?:within|at|in the|on the|by the|with the|from the|to the|as the|is|are)\s|\s{{2,}}|\n|$)",
        
        # Pattern 2: "SearchTerm (X) value" - handles parenthetical markers
        # UNIVERSAL for tables with markers like "(A)", "(1)", etc.
        rf"{escaped_term}\s*\([A-Za-z0-9]\)\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)",
        
        # Pattern 3: "(-) SearchTerm value" or "(+) SearchTerm value" - prefix operators
        # UNIVERSAL for financial tables showing deductions/additions
        rf"\([+\-]\)\s*{escaped_term}\s+([^\n\r]+?)(?:\s{{2,}}|\n|$)",
        
        # Pattern 4: "SearchTerm value" - UNIVERSAL number/word capture
        # Handles: currency symbols (₹$€£¥₨), numbers with commas (both styles), 
        # slashes, dashes, parentheses, and multi-word values
        # Stops at double-space (table columns), newline, or sentence boundaries
        rf"{escaped_term}\s+([+\-₹$€£¥₨]?[\w₹$€£¥₨,.\/\-\(\)@–]+(?:\s+[\w₹$€£¥₨,.\/\-\(\)@–]+)*?)(?:\s{{2,}}|\n|\.\s+[A-Z]|$)",
        
        # Pattern 5: "SearchTerm" on one line, value on next line
        # UNIVERSAL for documents with term-value on separate lines
        rf"{escaped_term}\s*\n+\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)",
    ]
    
    # Collect all matches with their positions
    match_list: List[tuple[int, str]] = []  # (position, value)
    for pat in patterns:
        try:
            for m in re.finditer(pat, text, flags=re.IGNORECASE if not look_for else 0):
                v = m.group(1).strip()
                # Clean up extra whitespace
                v = re.sub(r"\s{2,}", " ", v)
                # Remove ONLY trailing colons/semicolons (not commas - they might be significant)
                v = re.sub(r'[;:]+$', '', v).strip()
                if v and len(v) > 0:
                    # Store position and value, avoid duplicates
                    if not any(existing_v == v for _, existing_v in match_list):
                        match_list.append((m.start(), v))
        except re.error:
            continue
    
    if not match_list:
        return ""
    
    # Sort by position to get document order
    match_list.sort(key=lambda x: x[0])
    matches = [v for _, v in match_list]
    
    # Apply strategy first
    if strategy == "last":
        selected_value = matches[-1]
    elif strategy == "all":
        selected_value = " | ".join(matches)
    else:  # "first"
        selected_value = matches[0]
    
    # If column is specified, extract from multi-column value
    if column and selected_value:
        # Split by multiple spaces (table column separator)
        columns = re.split(r'\s{2,}', selected_value.strip())
        
        if len(columns) > 1:  # Multi-column detected
            # Handle column selection
            if column == "first":
                return columns[0]
            elif column == "last":
                return columns[-1]
            elif column == "all":
                return " | ".join(columns)
            elif column.isdigit():
                # 1-based index
                idx = int(column) - 1
                if 0 <= idx < len(columns):
                    return columns[idx]
            else:
                # Try to match column name (case-insensitive)
                # Look backwards in text to find table headers
                # For now, just return first column if no match
                # TODO: Implement header detection
                return columns[0]
    
    return selected_value


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
                    field_config = f  # Keep full config for validation
                else:
                    name = str(f)
                    strat = "first"
                    look_for = None
                    col = None
                    field_config = {"name": name, "type": "text", "validations": []}
                    
                if not name:
                    continue
                
                # Skip computed fields in the fields array (legacy support)
                field_type = f.get("type") if isinstance(f, dict) else "text"
                if field_type == "computed":
                    continue  # Will be handled in calculations section below
                
                # Normal extraction field
                # Extract column if specified
                col = f.get("column") if isinstance(f, dict) else None
                
                # Extract value
                value = _extract_field(text, name, strat, look_for, col)
                display = name.replace("_", " ").title()
                report["extractions"][display] = value
                
                # Validate extracted value
                validation_result = _validate_field_value(value, field_config)
                
                # Add detailed log entry
                log_entry = {
                    "field_name": name,
                    "look_for_text": look_for or name,
                    "strategy": strat,
                    "extracted_value": value,
                    "found": value is not None and value != "",
                    "validation": validation_result  # Add validation results
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
        
        # Process calculations (if any) after all fields are extracted
        calculations = rules.get("calculations", [])
        if calculations and isinstance(calculations, list):
            for calc in calculations:
                if not isinstance(calc, dict):
                    continue
                    
                calc_name = calc.get("name")
                formula = calc.get("formula")
                
                if not calc_name or not formula:
                    continue
                
                # Evaluate formula using extracted field values
                value = _compute_formula(formula, report["extractions"])
                display = calc_name.replace("_", " ").title()
                report["extractions"][display] = value
                
                # Add log entry for calculation
                log_entry = {
                    "field_name": calc_name,
                    "type": "calculation",
                    "formula": formula,
                    "computed_value": value,
                    "found": value is not None and value != ""
                }
                report["extraction_log"].append(log_entry)

        return report

    except Exception as e:
        logger.error(f"validate_text exception: {type(e).__name__}: {e}")
        return {"error": str(e)}
