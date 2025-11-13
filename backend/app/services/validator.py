from typing import Dict, Optional, List, Any, Tuple
import re
from app.utils.logger import get_logger
from app.services.extractor import (
    extract_between_markers,
    extract_with_lookfor,
    apply_extraction_strategy,
    extract_column_from_value
)

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
    
    # Create case-insensitive lookup for extractions
    # The extractions dict has title-cased keys, but formula may use original casing
    extractions_lower = {k.lower(): v for k, v in extractions.items()}
    
    # Detect if any source field has currency
    has_currency = False
    currency_symbol = ''
    
    # Build expression by finding field names and replacing with values
    expression = formula
    
    # Get all field names from extractions and sort by length (longest first) to avoid partial matches
    field_names_to_try = sorted(
        list(extractions.keys()) + list(extractions_lower.keys()),
        key=len,
        reverse=True
    )
    
    for field_name in field_names_to_try:
        # Skip if field name not in formula (case-insensitive check)
        if field_name.lower() not in formula.lower():
            continue
        
        # Try case-insensitive lookup
        field_value = extractions_lower.get(field_name.lower())
        if not field_value:
            # Try exact match as fallback
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
        
        # Replace field name with the clean number (case-insensitive)
        # Use regex with case-insensitive flag
        expression = re.sub(
            r'\b' + re.escape(field_name) + r'\b', 
            str(clean_num), 
            expression, 
            flags=re.IGNORECASE
        )
    
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
    column: Optional[str] = None,
    start_marker: Optional[str] = None,
    end_marker: Optional[str] = None
) -> str:
    """
    Extract field value from text with multiple extraction strategies.
    
    Args:
        text: Full document text
        field_name: Name of the field (fallback if look_for not provided)
        strategy: "first", "last", "all", or "between" for multiple matches
        look_for: Specific text to search for (overrides field_name) - for standard extraction
        column: For multi-column tables (column name, "first", "last", "1", "2", etc.)
        start_marker: Starting marker for "between" strategy
        end_marker: Ending marker for "between" strategy
    
    Returns:
        Extracted value as string. For "all" strategy, returns multiple values joined by " | "
    
    Examples:
        Standard extraction:
            _extract_field(text, "Employee Name", look_for="Name:", strategy="first")
        
        Between markers:
            _extract_field(text, "Invoice Number", strategy="between", 
                         start_marker="Invoice #", end_marker=" Date")
        
        Multi-column table:
            _extract_field(text, "PF Amount", look_for="PF Employee", 
                         strategy="first", column="Per Month")
    """
    if not text:
        return ""
    
    # Handle "between" strategy - check if markers are provided
    # Note: When strategy=="between", the caller passes occurrence ("first"/"all") as strategy parameter
    # and provides start_marker/end_marker to indicate between extraction
    if start_marker and end_marker:
        if not start_marker or not end_marker:
            logger.warning(f"Between strategy requires start_marker and end_marker for field '{field_name}'")
            return ""
        # strategy parameter contains the occurrence ("first", "all", etc.)
        return extract_between_markers(text, start_marker, end_marker, strategy)
    
    # Standard extraction using look_for patterns
    search_term = look_for if look_for else field_name
    if not search_term:
        return ""
    
    # Get all matches with positions
    match_list = extract_with_lookfor(text, search_term, strategy)
    
    if not match_list:
        return ""
    
    # Extract just the values
    matches = [v for _, v in match_list]
    
    # Apply strategy to select value(s)
    selected_value = apply_extraction_strategy(matches, strategy)
    
    # If column is specified, extract from multi-column value
    if column and selected_value:
        selected_value = extract_column_from_value(selected_value, column)
    
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
                    
                    # For "between" strategy, get the occurrence (first/all/last)
                    # Default to "first" if not specified
                    if strat == "between":
                        occurrence_strat = f.get("occurrence", "first")
                        logger.info(f"DEBUG: Between field '{name}' - using occurrence: {occurrence_strat}")
                    else:
                        occurrence_strat = strat
                    
                    # Debug logging for between strategy
                    if strat == "between":
                        logger.info(f"DEBUG: Processing between field '{name}': {f}")
                else:
                    name = str(f)
                    strat = "first"
                    occurrence_strat = "first"
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
                
                # Get markers for "between" strategy
                start_marker = f.get("startMarker") if isinstance(f, dict) else None
                end_marker = f.get("endMarker") if isinstance(f, dict) else None
                
                # For between strategy, use occurrence_strat instead of strat for matching
                extraction_strategy = occurrence_strat if strat == "between" else strat
                
                # Extract value
                value = _extract_field(
                    text, 
                    name, 
                    extraction_strategy, 
                    look_for, 
                    col,
                    start_marker,
                    end_marker
                )
                display = name.replace("_", " ").title()
                report["extractions"][display] = value
                
                # Validate extracted value
                validation_result = _validate_field_value(value, field_config)
                
                # Add detailed log entry
                # For between strategy, show markers instead of lookFor
                if strat == "between":
                    look_for_display = f"Between: '{start_marker}' and '{end_marker}'"
                else:
                    look_for_display = look_for or name
                
                log_entry = {
                    "field_name": name,
                    "look_for_text": look_for_display,
                    "strategy": strat,
                    "extracted_value": value,
                    "found": value is not None and value != "",
                    "validation": validation_result  # Add validation results
                }
                
                # Find where the lookFor text appears in PDF (skip for between strategy)
                if look_for and strat != "between":
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
        # Calculations are processed in order, and each calculation's result
        # is added to the extractions dict so subsequent calculations can reference it
        calculations = rules.get("calculations", [])
        if calculations and isinstance(calculations, list):
            for calc in calculations:
                if not isinstance(calc, dict):
                    continue
                    
                calc_name = calc.get("name")
                formula = calc.get("formula")
                
                if not calc_name or not formula:
                    continue
                
                # Evaluate formula using extracted field values AND previous calculation results
                # This enables chained calculations: Calc1 = A + B, Calc2 = Calc1 + C
                value = _compute_formula(formula, report["extractions"])
                display = calc_name.replace("_", " ").title()
                
                # Add result to extractions dict IMMEDIATELY so next calculation can use it
                report["extractions"][display] = value
                
                # Also add with original name (without title case) for formula matching
                # This ensures both "Gross Salary" and "Gross_Salary" work in formulas
                if display != calc_name:
                    report["extractions"][calc_name] = value
                
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
