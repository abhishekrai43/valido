from backend.celery_app import celery_app
import time
import io
import zipfile
import os
import csv
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Import the parser and validator from the app package. Tasks run inside the worker
# process where the repository root is typically on PYTHONPATH and the package name
# for the code in `backend/app` is `app`.
from app.services.parser import extract_text_from_bytes, is_valid_pdf
from app.services.validator import validate_text


@celery_app.task(bind=True)
def process_in_chunks_worker(self, items: List[Any], chunk_size: int = 50):
    """Example worker task that processes items in chunks.

    Kept for backwards compatibility and demonstration. `items` can be any serializable
    iterable but the task `process_pdfs` (below) should be preferred for PDF uploads.
    """
    total = len(items or [])
    processed = 0
    outputs = []

    for i in range(0, total, chunk_size):
        chunk = items[i : i + chunk_size]
        # Simulate processing latency for demonstration; replace with real processing.
        time.sleep(0.01)
        # Simple transformation example: for strings return their length, otherwise 1
        chunk_out = [len(x) if isinstance(x, (str, bytes)) else 1 for x in chunk]
        outputs.extend(chunk_out)
        processed += len(chunk)

        # Best-effort progress update
        try:
            self.update_state(state="PROGRESS", meta={"processed": processed, "total": total})
        except Exception:
            pass

    return {"status": "completed", "total": total, "processed": processed, "sample": outputs[:10]}


@celery_app.task(bind=True)
def process_pdfs(self, files: List[Dict], rules: Optional[Dict] = None, username: Optional[str] = None) -> Dict:
    """Process uploaded PDFs (or zip containing PDFs).

    `files` should be a list of dicts: {"filename": str, "content": bytes}
    `rules` is an optional dict passed to the validator.

    Returns a dict with per-file validation reports and aggregated status.
    """
    # Debug: Print rules to see what we're receiving
    print(f"DEBUG: Received rules: {json.dumps(rules, indent=2) if rules else 'None'}")
    
    reports = []
    total_files = 0

    # Expand any zip files included in the `files` list
    expanded_files: List[Dict[str, Any]] = []
    for entry in files:
        filename = entry.get("filename")
        content = entry.get("content") or b''
        total_files += 1

        # Detect zip by filename extension or ZIP header
        is_zip = False
        if filename and filename.lower().endswith(".zip"):
            is_zip = True
        else:
            # quick header check
            if isinstance(content, (bytes, bytearray)) and content[:4] == b"PK\x03\x04":
                is_zip = True

        if is_zip:
            try:
                with io.BytesIO(content) as bio:
                    with zipfile.ZipFile(bio) as zf:
                        for zi in zf.infolist():
                            # Only process files that look like PDFs
                            if zi.filename.lower().endswith(".pdf"):
                                with zf.open(zi) as f:
                                    file_bytes = f.read()
                                    expanded_files.append({"filename": zi.filename, "content": file_bytes})
            except Exception:
                # If the zip failed to open, record an error report for the original file
                reports.append({"filename": filename, "error": "failed to extract zip"})
        else:
            expanded_files.append({"filename": filename, "content": content or b''})

    # Now process expanded_files one-by-one and update progress
    total = len(expanded_files)
    processed = 0

    for f in expanded_files:
        fname = f.get("filename")
        content = f.get("content") or b''

        # Update progress with current file info
        try:
            self.update_state(
                state="PROGRESS", 
                meta={
                    "processed": processed, 
                    "total": total, 
                    "current_file": fname,
                    "percent": int((processed / total * 100)) if total > 0 else 0
                }
            )
        except Exception:
            pass

        # Debug: check what we received
        print(f"Processing {fname}: received {len(content)} bytes")
        if content:
            print(f"First 20 bytes: {content[:20]}")

        # Basic validation
        valid = False
        try:
            valid = is_valid_pdf(content or b'')
            if not valid:
                print(f"PDF validation failed for {fname}: is_valid_pdf returned False")
        except Exception as e:
            print(f"PDF validation exception for {fname}: {type(e).__name__}: {e}")
            valid = False

        if not valid:
            reports.append({"filename": fname, "error": "invalid or corrupted pdf"})
            processed += 1
            try:
                self.update_state(
                    state="PROGRESS", 
                    meta={
                        "processed": processed, 
                        "total": total, 
                        "current_file": fname,
                        "percent": int((processed / total * 100)) if total > 0 else 0
                    }
                )
            except Exception:
                pass
            continue

        # Extract text and validate
        try:
            text = extract_text_from_bytes(content or b'')
            report = validate_text(text, rules)
            reports.append({"filename": fname, "report": report})
        except Exception as exc:
            reports.append({"filename": fname, "error": f"processing error: {exc}"})

        processed += 1
        try:
            self.update_state(
                state="PROGRESS", 
                meta={
                    "processed": processed, 
                    "total": total, 
                    "current_file": fname,
                    "percent": int((processed / total * 100)) if total > 0 else 0
                }
            )
        except Exception:
            pass

    # Prepare results directory and files
    task_id = getattr(self.request, 'id', None) or datetime.utcnow().strftime('%s')
    # Generate timestamp for unique filenames
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    # Write results to the same path the API expects: ./results/<task_id>
    results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))
    os.makedirs(results_dir, exist_ok=True)

    # Helper functions for validation checks
    def detect_signed(t: str) -> Tuple[str, str]:
        """Check if document appears to be signed. Returns (yes/no, found_text)"""
        if not t:
            return 'No', ''
        kws = ['signature', 'signed by', '/s/', 'signatory', 'electronically signed', 'signed:', '/sig/']
        tl = t.lower()
        for k in kws:
            if k in tl:
                # Extract a snippet around the match
                idx = tl.find(k)
                snippet = t[max(0, idx-10):min(len(t), idx+50)].strip()
                return 'Yes', snippet[:100]
        return 'No', ''

    date_regexes = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2},? \d{2,4}\b",
    ]
    date_re = re.compile('|'.join(date_regexes), re.IGNORECASE)

    def detect_dated(t: str) -> Tuple[str, str]:
        """Check if document contains a date. Returns (yes/no, date_found)"""
        if not t:
            return 'No', ''
        m = date_re.search(t)
        if m:
            return 'Yes', m.group(0)
        return 'No', ''

    def check_must_contain(t: str, rule: dict) -> Tuple[str, str]:
        """Check if text contains required phrase.
        Returns (Yes/No, matched_snippet or empty)
        """
        if not t or not rule:
            return 'No', ''
        
        search_text = rule.get('text', '')
        if not search_text:
            return 'No', ''
        
        case_sensitive = rule.get('case_sensitive', False)
        
        if case_sensitive:
            found = search_text in t
            if found:
                idx = t.find(search_text)
                snippet = t[max(0, idx-20):min(len(t), idx+len(search_text)+20)].strip()
                return 'Yes', snippet[:100]
        else:
            found = search_text.lower() in t.lower()
            if found:
                idx = t.lower().find(search_text.lower())
                snippet = t[max(0, idx-20):min(len(t), idx+len(search_text)+20)].strip()
                return 'Yes', snippet[:100]
        
        return 'No', ''
    
    def check_must_not_contain(t: str, rule: dict) -> Tuple[str, str]:
        """Check if text does NOT contain forbidden phrase.
        Returns (Pass/Fail, matched_snippet if failed or empty)
        """
        if not t or not rule:
            return 'Pass', ''
        
        search_text = rule.get('text', '')
        if not search_text:
            return 'Pass', ''
        
        case_sensitive = rule.get('case_sensitive', False)
        
        if case_sensitive:
            found = search_text in t
            if found:
                idx = t.find(search_text)
                snippet = t[max(0, idx-20):min(len(t), idx+len(search_text)+20)].strip()
                return 'Fail', snippet[:100]
        else:
            found = search_text.lower() in t.lower()
            if found:
                idx = t.lower().find(search_text.lower())
                snippet = t[max(0, idx-20):min(len(t), idx+len(search_text)+20)].strip()
                return 'Fail', snippet[:100]
        
        return 'Pass', ''
    
    def check_page_count(content_bytes: bytes, rule: dict) -> Tuple[str, str]:
        """Check if PDF page count meets criteria.
        Returns (Pass/Fail, actual_count_string)
        """
        if not content_bytes or not rule:
            return 'Unknown', '0'
        
        try:
            # Count pages using PyMuPDF (fitz)
            import fitz
            
            doc = fitz.open(stream=content_bytes, filetype="pdf")
            page_count = len(doc)
            doc.close()
            
            operator = rule.get('operator', '==')
            value = int(rule.get('value', 0))
            
            result = False
            if operator == '==':
                result = page_count == value
            elif operator == '>=':
                result = page_count >= value
            elif operator == '<=':
                result = page_count <= value
            
            return ('Pass' if result else 'Fail'), str(page_count)
        except Exception as e:
            return 'Error', f'Could not count pages: {str(e)[:50]}'

    def extract_field_from_text(text: str, field_name: str, strategy: str = 'first') -> str:
        """Extract field value from text. Looks for label followed by value.
        
        Handles various patterns:
        - "Label: Value"
        - "Label Value" (with whitespace)
        - "Label\nValue" (on next line)
        Ignores section headers (all caps followed by newline)
        Handles currency symbols and special characters
        
        Args:
            text: The text to extract from
            field_name: The field label to look for
            strategy: 'first' (default), 'last', or 'all' - which occurrence(s) to return
        
        Returns:
            For 'first'/'last': single value string (empty if not found)
            For 'all': comma-separated string of all values found (empty if none)
        """
        if not text:
            return ''
        
        # Normalize field name variants
        field_lower = field_name.lower().replace('_', ' ')
        
        # Try multiple pattern styles
        # Match currency symbols, numbers, alphanumeric, common punctuation
        patterns = [
            # Pattern 1: Label: Value (most common)
            (rf"\b{re.escape(field_lower)}\s*[:]\s*([^\n\r]+)", re.IGNORECASE),
            # Pattern 2: Label followed by value on same line with whitespace separator
            (rf"\b{re.escape(field_lower)}\s+([A-Za-z0-9₹$€£¥₨,.]+[^\n\r]*?)(?:\s{{2,}}|\n|$)", re.IGNORECASE),
            # Pattern 3: Label on one line, value on next line
            (rf"\b{re.escape(field_lower)}\s*\n\s*([^\n\r]+)", re.IGNORECASE),
        ]
        
        # Collect all matches across all patterns
        all_matches = []
        
        for pattern, flags in patterns:
            matches = re.finditer(pattern, text, flags)
            for m in matches:
                value = m.group(1).strip()
                
                # Skip if it looks like a section header (all caps words)
                if value.isupper() and len(value.split()) <= 3:
                    continue
                
                # Clean up common artifacts
                value = re.sub(r'\s{2,}', ' ', value)  # Multiple spaces to single
                value = value.split('\t')[0]  # Stop at tab
                
                # Handle encoding issues with currency symbols
                # Replace common currency symbols with ASCII equivalents for CSV compatibility
                currency_map = {
                    '₹': 'Rs.',
                    '₨': 'Rs.',
                    '€': 'EUR',
                    '£': 'GBP',
                    '¥': 'JPY',
                    '$': 'USD'
                }
                for symbol, replacement in currency_map.items():
                    if symbol in value:
                        # Keep the symbol if it's at the start, otherwise preserve original
                        if value.startswith(symbol):
                            value = replacement + ' ' + value[1:].strip()
                        else:
                            value = value.replace(symbol, replacement)
                
                # Take first reasonable chunk
                if len(value) > 100:
                    value = value[:100].rsplit(' ', 1)[0]  # Cut at word boundary
                
                cleaned_value = value.strip()
                if cleaned_value and cleaned_value not in all_matches:
                    all_matches.append(cleaned_value)
        
        # Return based on strategy
        if not all_matches:
            return ''
        
        if strategy == 'last':
            return all_matches[-1]
        elif strategy == 'all':
            return ' | '.join(all_matches)
        else:  # 'first' or default
            return all_matches[0]

    # Parse rules to understand what user wants to extract/validate
    validation_checks = []
    extraction_fields = []
    must_contain_rules = []
    must_not_contain_rules = []
    page_count_rules = None
    
    if isinstance(rules, dict):
        # Handle validation checks - frontend sends {validations: {signed: true, dated: true, ...}}
        validations = rules.get('validations', {})
        if isinstance(validations, dict):
            if validations.get('signed'):
                validation_checks.append('signed')
            if validations.get('dated'):
                validation_checks.append('dated')
            if validations.get('signed_and_dated'):
                if 'signed' not in validation_checks:
                    validation_checks.append('signed')
                if 'dated' not in validation_checks:
                    validation_checks.append('dated')
            
            # Handle must_contain validation
            if validations.get('must_contain'):
                must_contain_rules.append(validations['must_contain'])
            
            # Handle must_not_contain validation
            if validations.get('must_not_contain'):
                must_not_contain_rules.append(validations['must_not_contain'])
            
            # Handle page_count validation
            if validations.get('page_count'):
                page_count_rules = validations['page_count']
        
        # Also support legacy format for backwards compatibility
        if rules.get('validate_signed'):
            validation_checks.append('signed')
        if rules.get('validate_dated'):
            validation_checks.append('dated')
        if rules.get('validate_signed_and_dated'):
            if 'signed' not in validation_checks:
                validation_checks.append('signed')
            if 'dated' not in validation_checks:
                validation_checks.append('dated')
        
        # Handle field extraction
        fields = rules.get('fields') or []
        if isinstance(fields, list):
            # Support both formats: [{name: 'field', strategy: 'first'}] or ['field']
            for field in fields:
                if isinstance(field, dict):
                    extraction_fields.append({
                        'name': field.get('name', ''),
                        'strategy': field.get('strategy', 'first')
                    })
                elif isinstance(field, str):
                    # Legacy format: string field names default to 'first' strategy
                    extraction_fields.append({'name': field, 'strategy': 'first'})

    # Build CSV rows - one row per file with all checks and extractions
    csv_rows = []
    for entry in reports:
        fname = entry.get('filename')
        err = entry.get('error', '')
        
        # Extract text and content for this file
        text = ''
        content_bytes = b''
        try:
            for ef in expanded_files:
                if ef.get('filename') == fname:
                    content_bytes = ef.get('content') or b''
                    text = extract_text_from_bytes(content_bytes) or ''
                    break
        except Exception:
            text = ''

        # Build row with filename first
        row = {
            'Filename': fname,
            'Status': 'Error' if err else 'Success',
        }

        # Add validation check columns
        if 'signed' in validation_checks:
            is_signed, signed_value = detect_signed(text)
            row['Signed'] = is_signed
            if signed_value:
                row['Signature Details'] = signed_value

        if 'dated' in validation_checks:
            is_dated, date_value = detect_dated(text)
            row['Dated'] = is_dated
            if date_value:
                row['Date Found'] = date_value

        # Add must_contain validation columns
        for idx, rule in enumerate(must_contain_rules):
            search_term = rule.get('text', '')
            case_info = ' (case-sensitive)' if rule.get('case_sensitive') else ''
            col_name = f'Contains "{search_term}"{case_info}'
            result, snippet = check_must_contain(text, rule)
            row[col_name] = result
            if snippet:
                row[f'{col_name} - Found'] = snippet
        
        # Add must_not_contain validation columns
        for idx, rule in enumerate(must_not_contain_rules):
            search_term = rule.get('text', '')
            case_info = ' (case-sensitive)' if rule.get('case_sensitive') else ''
            col_name = f'Does NOT Contain "{search_term}"{case_info}'
            result, snippet = check_must_not_contain(text, rule)
            row[col_name] = result
            if snippet and result == 'Fail':
                row[f'{col_name} - Found'] = snippet
        
        # Add page_count validation column
        if page_count_rules:
            operator = page_count_rules.get('operator', '==')
            value = page_count_rules.get('value', 0)
            op_text = {'==': 'exactly', '>=': 'at least', '<=': 'at most'}.get(operator, operator)
            col_name = f'Page Count ({op_text} {value})'
            result, actual_count = check_page_count(content_bytes, page_count_rules)
            row[col_name] = result
            row['Actual Page Count'] = actual_count

        # Add extraction field columns
        for field in extraction_fields:
            field_name = field.get('name', field) if isinstance(field, dict) else field
            field_strategy = field.get('strategy', 'first') if isinstance(field, dict) else 'first'
            field_display = field_name.replace('_', ' ').title()
            extracted_value = extract_field_from_text(text, field_name, field_strategy) if text else ''
            row[field_display] = extracted_value

        # Add error/notes if any
        if err:
            row['Error Details'] = err
        
        csv_rows.append(row)

    # Determine CSV columns dynamically
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
    else:
        fieldnames = ['Filename', 'Status']

    # Write CSV with proper encoding and error handling - use unique filename
    csv_filename = f'valido_results_{timestamp}.csv'
    csv_path = os.path.join(results_dir, csv_filename)
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for row in csv_rows:
            # Ensure all values are safe for CSV (handle None, bytes, etc.)
            safe_row = {}
            for key, value in row.items():
                if value is None:
                    safe_row[key] = ''
                elif isinstance(value, bytes):
                    safe_row[key] = value.decode('utf-8', errors='replace')
                else:
                    safe_row[key] = str(value)
            writer.writerow(safe_row)

    # Create ZIP file with only CSV (no JSON report to keep size small) - use unique filename
    zip_filename = f'valido_results_{timestamp}.zip'
    zip_path = os.path.join(results_dir, zip_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv_path, csv_filename)

    # If a username was provided, increment their processed counter in the DB
    if username:
        try:
            from app.db import get_session
            from app.models import User
            from sqlmodel import select

            with get_session() as session:
                u = session.exec(select(User).where(User.username == username)).first()
                if not u:
                    # create user record if missing (simple behavior)
                    u = User(username=username, total_processed=processed)
                    session.add(u)
                else:
                    u.total_processed = (u.total_processed or 0) + processed
                    session.add(u)
                session.commit()
        except Exception:
            # Don't fail the task if DB update fails; just continue
            pass

    # Return result with download info (API exposes download endpoint)
    return {
        'status': 'completed',
        'total': total,
        'processed': processed,
        'files': reports,
        'result_files': {
            'csv': f'/api/v1/tasks/{task_id}/result.csv',
            'zip': f'/api/v1/tasks/{task_id}/results.zip'
        }
    }

