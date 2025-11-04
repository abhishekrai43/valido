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

        # Basic validation
        valid = False
        try:
            valid = is_valid_pdf(content or b'')
        except Exception:
            valid = False

        if not valid:
            reports.append({"filename": fname, "error": "invalid or corrupted pdf"})
            processed += 1
            try:
                self.update_state(state="PROGRESS", meta={"processed": processed, "total": total})
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
            self.update_state(state="PROGRESS", meta={"processed": processed, "total": total})
        except Exception:
            pass

    # Prepare results directory and files
    task_id = getattr(self.request, 'id', None) or datetime.utcnow().strftime('%s')
    results_dir = os.path.abspath(os.path.join(os.getcwd(), '..', '..', 'results', task_id))
    os.makedirs(results_dir, exist_ok=True)

    # Helper heuristics for CSV fields
    def detect_contains_invoice(t: str) -> str:
        return 'yes' if t and 'invoice' in t.lower() else 'no'

    def detect_signed(t: str) -> str:
        if not t:
            return 'no'
        kws = ['signature', 'signed by', '/s/', 'signatory', 'electronically signed']
        tl = t.lower()
        for k in kws:
            if k in tl:
                return 'yes'
        return 'no'

    date_regexes = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2},? \d{2,4}\b",
    ]
    date_re = re.compile('|'.join(date_regexes), re.IGNORECASE)

    def detect_dated_and_signed_date(t: str) -> Tuple[str, str]:
        if not t:
            return 'no', ''
        m = date_re.search(t)
        if m:
            return 'yes', m.group(0)
        return 'no', ''

    # Build CSV rows from reports and extracted text
    csv_rows = []
    for entry in reports:
        fname = entry.get('filename')
        err = entry.get('error', '')
        rep = entry.get('report') or {}

        # Try to get extracted text length from report if available; otherwise empty
        # We didn't store text per-file earlier; attempt to re-extract for metadata (best-effort)
        text = ''
        pages = ''
        try:
            # look for matching expanded_files entry
            for ef in expanded_files:
                if ef.get('filename') == fname:
                    text = extract_text_from_bytes(ef.get('content') or b'') or ''
                    break
        except Exception:
            text = ''

        text_length = len(text or '')
        contains_invoice = detect_contains_invoice(text)
        signed = detect_signed(text)
        dated, signed_date = detect_dated_and_signed_date(text)

        # rule pass/fail counts from report
        rule_pass = 0
        rule_fail = 0
        rules_info = rep.get('rules') if isinstance(rep, dict) else None
        if isinstance(rules_info, list):
            for r in rules_info:
                res = r.get('result')
                if res == 'pass':
                    rule_pass += 1
                else:
                    rule_fail += 1

        notes = ''
        if isinstance(text, str) and text.startswith('[binary-pdf-content-no-text-extracted]'):
            notes = 'OCR not available or no text extracted'

        csv_rows.append({
            'task_id': task_id,
            'filename': fname,
            'pages': pages,
            'text_length': text_length,
            'contains_invoice': contains_invoice,
            'signed': signed,
            'dated': dated,
            'signed_date': signed_date,
            'rule_pass_count': rule_pass,
            'rule_fail_count': rule_fail,
            'error': err,
            'notes': notes,
        })

    # Write CSV
    csv_path = os.path.join(results_dir, 'results.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as cf:
        writer = csv.DictWriter(cf, fieldnames=[
            'task_id', 'filename', 'pages', 'text_length', 'contains_invoice', 'signed', 'dated', 'signed_date',
            'rule_pass_count', 'rule_fail_count', 'error', 'notes'
        ])
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    # Write full JSON report
    report_path = os.path.join(results_dir, 'report.json')
    with open(report_path, 'w', encoding='utf-8') as jf:
        json.dump({'task_id': task_id, 'total': total, 'processed': processed, 'files': reports}, jf, indent=2)

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
            'report_json': f'/api/v1/tasks/{task_id}/report.json'
        }
    }

