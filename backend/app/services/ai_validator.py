from typing import Dict, Optional, List, Any, Tuple, Union
import re
# Assuming app.utils.logger is available
# from app.utils.logger import get_logger 
# logger = get_logger("ValidoValidator")

# --- PLACEHOLDER FOR LOGGER (Since app.utils is not available) ---
class DummyLogger:
    def error(self, msg): print(f"ERROR: {msg}")
    def info(self, msg): print(f"INFO: {msg}")
logger = DummyLogger()
# -----------------------------------------------------------------

# Reuse helper functions from the canonical validator module when available.
# To avoid strict function-type mismatches reported by type-checkers, import
# the module and assign callables to Any-typed names.
try:
    import app.services.validator as _validator
except Exception:
    _validator = None


def _find_date(text: str):
    return _validator._find_date(text) if _validator else None


def _find_all_dates(text: str) -> List[str]:
    return _validator._find_all_dates(text) if _validator else []


def _find_signature_snippet(text: str):
    return _validator._find_signature_snippet(text) if _validator else None


def _match_text_rule(text: str, rule: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    if _validator:
        return _validator._match_text_rule(text, rule)
    return "No", None


def _match_not_contain_rule(text: str, rule: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    if _validator:
        return _validator._match_not_contain_rule(text, rule)
    return "Pass", None



def _extract_field_by_regex(text: str, rule: Dict[str, Any]) -> Tuple[Union[str, int, float, List[Union[int, float, str]]], str]:
    """
    Executes a field extraction rule based on the AI-generated schema.
    Handles custom regex, extraction strategy, and data type conversion.
    """
    regex_pattern = rule.get("regex_pattern")
    field_name = rule.get("field", "Unknown Field")
    strategy = rule.get("strategy", "first").lower()
    data_type = rule.get("data_type", "string").lower()

    if not regex_pattern:
        logger.error(f"Extraction rule for '{field_name}' missing regex_pattern.")
        return "", ""

    matches: List[str] = []
    try:
        # Note: re.finditer looks for capturing group 1, as instructed to the AI
        pattern = re.compile(regex_pattern, re.IGNORECASE)
        for m in pattern.finditer(text or ""):
            if len(m.groups()) > 0:
                # Clean up extracted value
                v = m.group(1).strip().replace(',', '') 
                if v:
                    matches.append(v)
    except re.error as e:
        logger.error(f"Regex error for '{field_name}': {e}")
        return "", ""

    if not matches:
        return "", ""

    # 1. Apply Strategy
    raw_result: Union[str, List[str], int, float]
    if strategy == "all":
        raw_result = matches
    elif strategy == "last":
        raw_result = matches[-1]
    else: # 'first'
        raw_result = matches[0]

    # 2. Convert Data Type
    final_result: Union[str, int, float, List[Union[int, float, str]]]
    if isinstance(raw_result, list):
        final_result = []
        for val in raw_result:
            try:
                if data_type == "float":
                    final_result.append(float(val))
                elif data_type == "int":
                    final_result.append(int(val))
                else:
                    final_result.append(val)
            except ValueError:
                # Only append if data_type is string, otherwise skip
                if data_type == "string":
                    final_result.append(val)
    else:
        try:
            if data_type == "float":
                final_result = float(raw_result)
            elif data_type == "int":
                final_result = int(raw_result)
            else:
                final_result = raw_result
        except ValueError:
            final_result = raw_result
    
    # Return a snippet of the context around the *first* match for debugging
    first_match = pattern.search(text)
    snippet = ""
    if first_match:
        idx = first_match.start()
        start = max(0, idx - 40)
        end = min(len(text), idx + 80)
        snippet = text[start:end].strip()
        
    return final_result, snippet


def _match_numeric_aggregation_rule(extracted_data: Union[Any, List[Any]], rule: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """
    Executes a numeric aggregation rule (e.g., GPA > 3.5 across all semesters).
    Assumes extracted_data is a list of numbers if rule.condition is set.
    """
    condition = rule.get("condition", "").lower()
    value = rule.get("value")
    
    if not isinstance(extracted_data, list):
        # This rule should only run on lists of extracted data (strategy='all')
        return "N/A", "Data not a list (required strategy='all')"

    if not isinstance(value, (int, float)):
        return "Fail", f"Rule value is invalid: {value}"

    numbers = [x for x in extracted_data if isinstance(x, (int, float))]
    
    if not numbers:
        return "No", "No numeric data found for validation."

    result = "Pass"
    fail_reason = None

    if condition == "all_greater_than":
        if not all(n > value for n in numbers):
            result = "Fail"
            fail_reason = f"At least one value is not greater than {value}. Found: {numbers}"
    elif condition == "any_less_than":
        if any(n < value for n in numbers):
            result = "Fail"
            fail_reason = f"At least one value is less than {value}. Found: {numbers}"
    elif condition == "min_value":
        if min(numbers) < value:
            result = "Fail"
            fail_reason = f"Minimum value ({min(numbers)}) is less than required minimum of {value}."
    elif condition == "max_value":
        if max(numbers) > value:
            result = "Fail"
            fail_reason = f"Maximum value ({max(numbers)}) is greater than required maximum of {value}."
    else:
        result = "N/A"
        fail_reason = f"Unsupported condition: {condition}"
        
    return result, fail_reason


def validate_text(text: str, rules: Optional[dict] = None) -> Dict:
    """
    Main validation function, adapted to use the new, structured AI ruleset.
    """
    try:
        if not isinstance(text, str):
            logger.error("validate_text: input text is not a string")
            return {"error": "Input text must be a string"}

        report: Dict[str, Any] = {
            "summary": {"length": len(text or "")},
            "extractions": {}, # Stores the results of ExtractionRule execution
            "validations": {}, # Stores the results of ValidationRule execution
        }
        
        if not isinstance(rules, dict):
             return report

        # --- PHASE 1: Execute Extractions ---
        # Store extracted data in a dictionary for easy reference by validation rules
        extracted_data_map: Dict[str, Any] = {}
        extraction_rules = rules.get("extractions", [])
        
        for rule in extraction_rules:
            field_name = rule.get("field")
            if not field_name: continue
            
            value, snippet = _extract_field_by_regex(text, rule)
            extracted_data_map[field_name] = value
            
            # Populate the final report with extraction results
            report["extractions"][field_name] = {
                "value": value,
                "data_type": rule.get("data_type"),
                "strategy": rule.get("strategy"),
                "snippet": snippet
            }

        # --- PHASE 2: Execute Validations ---
        validation_rules = rules.get("validations", [])
        
        for i, rule in enumerate(validation_rules):
            v_type = rule.get("type", "")
            description = rule.get("description", f"Rule {i+1}")
            result = "N/A"
            detail = "Rule type not recognized."

            if v_type == "contains_text":
                result, detail = _match_text_rule(text, rule)
            elif v_type == "not_contains_text":
                result, detail = _match_not_contain_rule(text, rule)
            elif v_type == "numeric_aggregation":
                field_ref = rule.get("field_reference")
                data_to_validate = extracted_data_map.get(field_ref)
                if data_to_validate is not None:
                    result, detail = _match_numeric_aggregation_rule(data_to_validate, rule)
                else:
                    result, detail = "Fail", f"Reference field '{field_ref}' not extracted or not found."
            
            # Populate the final report with validation results
            report["validations"][description] = {
                "result": result,
                "type": v_type,
                "detail": detail
            }

        # The old hardcoded 'signed' and 'dated' checks can be replaced by the AI if needed,
        # but are kept here for existing compatibility/simplicity if no AI rule overrides them.
        if "signed" not in report["validations"]:
             snippet = _find_signature_snippet(text)
             report["validations"]["Document Signed (Legacy)"] = {"result": "Yes" if snippet else "No", "detail": snippet}
        
        if "dated" not in report["validations"]:
             found_date = _find_date(text)
             all_dates = _find_all_dates(text)
             report["validations"]["Document Dated (Legacy)"] = {"result": "Yes" if found_date else "No", "detail": found_date, "all_dates": all_dates}


        return report

    except Exception as e:
        logger.error(f"validate_text exception: {type(e).__name__}: {e}")
        return {"error": str(e)}