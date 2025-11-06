# app/tasks/worker_tasks.py
# Refactored so core logic is a synchronous callable usable by both Celery workers
# and the single-process in-process runner.

import time
import io
import zipfile
import os
import csv
import json
import re
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime

# celery_app may or may not be present depending on runtime environment.
# In your repo it exists; importing here preserves compatibility for Celery-based deployments.
try:
    from backend.celery_app import celery_app
except Exception:
    celery_app = None  # safe fallback for single-process packaging

# Import the parser and validator from the app package.
from app.services.parser import extract_text_from_bytes, is_valid_pdf
from app.services.validator import validate_text


# -------------------------
# Helper: chunk demo task (kept for compatibility)
# -------------------------
if celery_app is not None:
    @celery_app.task(bind=True)
    def process_in_chunks_worker(self, items: List[Any], chunk_size: int = 50):
        total = len(items or [])
        processed = 0
        outputs = []
        for i in range(0, total, chunk_size):
            chunk = items[i : i + chunk_size]
            time.sleep(0.01)
            chunk_out = [len(x) if isinstance(x, (str, bytes)) else 1 for x in chunk]
            outputs.extend(chunk_out)
            processed += len(chunk)
            try:
                self.update_state(state="PROGRESS", meta={"processed": processed, "total": total})
            except Exception:
                pass
        return {"status": "completed", "total": total, "processed": processed, "sample": outputs[:10]}
else:
    # Provide a no-Celery fallback (callable) for local use
    def process_in_chunks_worker(items: List[Any], chunk_size: int = 50):
        total = len(items or [])
        processed = 0
        outputs = []
        for i in range(0, total, chunk_size):
            chunk = items[i : i + chunk_size]
            time.sleep(0.01)
            chunk_out = [len(x) if isinstance(x, (str, bytes)) else 1 for x in chunk]
            outputs.extend(chunk_out)
            processed += len(chunk)
        return {"status": "completed", "total": total, "processed": processed, "sample": outputs[:10]}


# -------------------------
# Core sync processor (callable)
# -------------------------
def process_pdfs_sync(
    files: List[Dict],
    rules: Optional[Dict] = None,
    username: Optional[str] = None,
    results_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Dict:
    """
    Synchronous callable that processes uploaded PDFs (or ZIPs).
    - files: list of {"filename": str, "content": bytes}
    - rules: optional dict for validator
    - username: optional username for DB counters
    - results_dir: directory path where results will be written (must exist or will be created)
    - progress_callback: optional callable(progress_state, meta_dict)
      Example: lambda state, meta: celery_self.update_state(state=state, meta=meta)
    Returns a dict summary with same structure as previous Celery task.
    """
    # helper to emit progress if provided
    def _emit_progress(state: str, meta: Dict[str, Any]):
        try:
            if progress_callback:
                progress_callback(state, meta)
        except Exception:
            pass

    reports = []
    total_files = 0

    # Expand zip files
    expanded_files: List[Dict[str, Any]] = []
    for entry in files:
        filename = entry.get("filename")
        content = entry.get("content") or b''
        total_files += 1

        is_zip = False
        if filename and filename.lower().endswith(".zip"):
            is_zip = True
        else:
            if isinstance(content, (bytes, bytearray)) and content[:4] == b"PK\x03\x04":
                is_zip = True

        if is_zip:
            try:
                with io.BytesIO(content) as bio:
                    with zipfile.ZipFile(bio) as zf:
                        for zi in zf.infolist():
                            if zi.filename.lower().endswith(".pdf"):
                                with zf.open(zi) as f:
                                    file_bytes = f.read()
                                    expanded_files.append({"filename": zi.filename, "content": file_bytes})
            except Exception:
                reports.append({"filename": filename, "error": "failed to extract zip"})
        else:
            expanded_files.append({"filename": filename, "content": content or b''})

    total = len(expanded_files)
    processed = 0

    for f in expanded_files:
        fname = f.get("filename")
        content = f.get("content") or b''

        # Progress update
        _emit_progress("PROGRESS", {
            "processed": processed,
            "total": total,
            "current_file": fname,
            "percent": int((processed / total * 100)) if total > 0 else 0
        })

        # Debug prints (safe for local logs)
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
            _emit_progress("PROGRESS", {
                "processed": processed, "total": total, "current_file": fname,
                "percent": int((processed / total * 100)) if total > 0 else 0
            })
            continue

        # Extract and validate
        try:
            text = extract_text_from_bytes(content or b'')
            report = validate_text(text, rules)
            reports.append({"filename": fname, "report": report})
        except Exception as exc:
            reports.append({"filename": fname, "error": f"processing error: {exc}"})

        processed += 1
        _emit_progress("PROGRESS", {
            "processed": processed, "total": total, "current_file": fname,
            "percent": int((processed / total * 100)) if total > 0 else 0
        })

    # Prepare results directory and files
    # Determine or create task_id/results_dir
    task_id = None
    if results_dir:
        results_dir = os.path.abspath(results_dir)
        task_id = os.path.basename(results_dir.rstrip("/\\"))
    else:
        # fallback: generate a timestamp-id
        task_id = datetime.utcnow().strftime('%s')
        results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))

    os.makedirs(results_dir, exist_ok=True)

    # Helper functions (same detection/extraction/validation logic as before)
    def detect_signed(t: str) -> Tuple[str, str]:
        if not t:
            return 'No', ''
        kws = ['signature', 'signed by', '/s/', 'signatory', 'electronically signed', 'signed:', '/sig/']
        tl = t.lower()
        for k in kws:
            if k in tl:
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
        if not t:
            return 'No', ''
        m = date_re.search(t)
        if m:
            return 'Yes', m.group(0)
        return 'No', ''

    def check_must_contain(t: str, rule: dict) -> Tuple[str, str]:
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
        if not content_bytes or not rule:
            return 'Unknown', '0'
        try:
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
        if not text:
            return ''
        field_lower = field_name.lower().replace('_', ' ')
        patterns = [
            (rf"\b{re.escape(field_lower)}\s*[:]\s*([^\n\r]+)", re.IGNORECASE),
            (rf"\b{re.escape(field_lower)}\s+([A-Za-z0-9₹$€£¥₨,.]+[^\n\r]*?)(?:\s{{2,}}|\n|$)", re.IGNORECASE),
            (rf"\b{re.escape(field_lower)}\s*\n\s*([^\n\r]+)", re.IGNORECASE),
        ]
        all_matches = []
        for pattern, flags in patterns:
            matches = re.finditer(pattern, text, flags)
            for m in matches:
                value = m.group(1).strip()
                if value.isupper() and len(value.split()) <= 3:
                    continue
                value = re.sub(r'\s{2,}', ' ', value)
                value = value.split('\t')[0]
                currency_map = {'₹': 'Rs.', '₨': 'Rs.', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '$': 'USD'}
                for symbol, replacement in currency_map.items():
                    if symbol in value:
                        if value.startswith(symbol):
                            value = replacement + ' ' + value[1:].strip()
                        else:
                            value = value.replace(symbol, replacement)
                if len(value) > 100:
                    value = value[:100].rsplit(' ', 1)[0]
                cleaned_value = value.strip()
                if cleaned_value and cleaned_value not in all_matches:
                    all_matches.append(cleaned_value)
        if not all_matches:
            return ''
        if strategy == 'last':
            return all_matches[-1]
        elif strategy == 'all':
            return ' | '.join(all_matches)
        else:
            return all_matches[0]

    # Parse rules into checks & fields
    validation_checks = []
    extraction_fields = []
    must_contain_rules = []
    must_not_contain_rules = []
    page_count_rules = None

    if isinstance(rules, dict):
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
            if validations.get('must_contain'):
                must_contain_rules.append(validations['must_contain'])
            if validations.get('must_not_contain'):
                must_not_contain_rules.append(validations['must_not_contain'])
            if validations.get('page_count'):
                page_count_rules = validations['page_count']
        # backward compatibility keys
        if rules.get('validate_signed'):
            validation_checks.append('signed')
        if rules.get('validate_dated'):
            validation_checks.append('dated')
        if rules.get('validate_signed_and_dated'):
            if 'signed' not in validation_checks:
                validation_checks.append('signed')
            if 'dated' not in validation_checks:
                validation_checks.append('dated')
        fields = rules.get('fields') or []
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, dict):
                    extraction_fields.append({'name': field.get('name', ''), 'strategy': field.get('strategy', 'first')})
                elif isinstance(field, str):
                    extraction_fields.append({'name': field, 'strategy': 'first'})

    # Build CSV rows
    csv_rows = []
    for entry in reports:
        fname = entry.get('filename')
        err = entry.get('error', '')
        # find content & text
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

        is_scanned = text.startswith('[SCANNED_PDF]')
        scanned_message = ''
        if is_scanned:
            scanned_message = text.replace('[SCANNED_PDF]', '').strip()
            text = ''

        row = {'Filename': fname, 'Status': 'Scanned PDF' if is_scanned else ('Error' if err else 'Success')}
        if is_scanned:
            row['Error Details'] = scanned_message

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

        for idx, rule in enumerate(must_contain_rules):
            search_term = rule.get('text', '')
            case_info = ' (case-sensitive)' if rule.get('case_sensitive') else ''
            col_name = f'Contains \"{search_term}\"{case_info}'
            result, snippet = check_must_contain(text, rule)
            row[col_name] = result
            if snippet:
                row[f'{col_name} - Found'] = snippet

        for idx, rule in enumerate(must_not_contain_rules):
            search_term = rule.get('text', '')
            case_info = ' (case-sensitive)' if rule.get('case_sensitive') else ''
            col_name = f'Does NOT Contain \"{search_term}\"{case_info}'
            result, snippet = check_must_not_contain(text, rule)
            row[col_name] = result
            if snippet and result == 'Fail':
                row[f'{col_name} - Found'] = snippet

        if page_count_rules:
            operator = page_count_rules.get('operator', '==')
            value = page_count_rules.get('value', 0)
            op_text = {'==': 'exactly', '>=': 'at least', '<=': 'at most'}.get(operator, operator)
            col_name = f'Page Count ({op_text} {value})'
            result, actual_count = check_page_count(content_bytes, page_count_rules)
            row[col_name] = result
            row['Actual Page Count'] = actual_count

        for field in extraction_fields:
            field_name = field.get('name', field) if isinstance(field, dict) else field
            field_strategy = field.get('strategy', 'first') if isinstance(field, dict) else 'first'
            field_display = field_name.replace('_', ' ').title()
            extracted_value = extract_field_from_text(text, field_name, field_strategy) if text else ''
            row[field_display] = extracted_value

        if err:
            row['Error Details'] = err

        csv_rows.append(row)

    # Determine CSV columns
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
    else:
        fieldnames = ['Filename', 'Status']

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'valido_results_{timestamp}.csv'
    csv_path = os.path.join(results_dir, csv_filename)
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for row in csv_rows:
            safe_row = {}
            for key, value in row.items():
                if value is None:
                    safe_row[key] = ''
                elif isinstance(value, bytes):
                    safe_row[key] = value.decode('utf-8', errors='replace')
                else:
                    safe_row[key] = str(value)
            writer.writerow(safe_row)

    zip_filename = f'valido_results_{timestamp}.zip'
    zip_path = os.path.join(results_dir, zip_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv_path, csv_filename)

    # Optional DB counter increment
    if username:
        try:
            from app.db import get_session
            from app.models import User
            from sqlmodel import select
            with get_session() as session:
                u = session.exec(select(User).where(User.username == username)).first()
                if not u:
                    u = User(username=username, total_processed=processed)
                    session.add(u)
                else:
                    u.total_processed = (u.total_processed or 0) + processed
                    session.add(u)
                session.commit()
        except Exception:
            pass

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


# -------------------------
# Celery task registration (backwards compatibility)
# -------------------------
# Register a Celery task that calls the sync function, but keep `process_pdfs`
# name bound to the synchronous function for imports used by the local runner.
if celery_app is not None:
    # We register a named Celery task that will call process_pdfs_sync and
    # compute results_dir from the Celery request id (to mimic earlier behavior).
    def _celery_progress_callback(self):
        # creates a callback closure to call self.update_state
        def cb(state: str, meta: Dict[str, Any]):
            try:
                self.update_state(state=state, meta=meta)
            except Exception:
                pass
        return cb

    def _make_celery_task(func):
        # wrap so Celery gets a task named exactly as before
        @celery_app.task(bind=True, name='backend.app.tasks.worker_tasks.process_pdfs')
        def _task(self, files, rules=None, username=None):
            # compute results_dir from request id
            task_id = getattr(self.request, 'id', None) or datetime.utcnow().strftime('%s')
            results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))
            os.makedirs(results_dir, exist_ok=True)
            return func(files, rules, username, results_dir, progress_callback=_celery_progress_callback(self))
        return _task

    # Register the celery task (keeps Celery deployments working)
    try:
        process_pdfs_celery = _make_celery_task(process_pdfs_sync)
    except Exception:
        process_pdfs_celery = None

# Export name `process_pdfs` as the synchronous function for local runner compatibility.
# This lets `from app.tasks.worker_tasks import process_pdfs` return a plain callable.
process_pdfs = process_pdfs_sync
