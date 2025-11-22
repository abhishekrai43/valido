# app/tasks/worker_tasks.py
"""
Main Worker Tasks Orchestrator
Coordinates PDF processing, validation, and result generation.
Uses modular report_generator and result_packager for clean separation.
"""
# pyright: reportOptionalCall=false, reportOptionalMemberAccess=false, reportOptionalOperand=false, reportArgumentType=false, reportOperatorIssue=false

import os
import json
import time
import io
import zipfile
import re
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime

# Core dependencies
from app.services.parser import extract_text_from_bytes, is_valid_pdf
from app.services.validator import validate_text
from app.utils.logger import get_logger
from PyPDF2 import PdfReader

# Import modularized report and packaging functions
from app.tasks.report_generator import generate_excel_report, generate_pdf_summary
from app.tasks.result_packager import create_results_zip

# Initialize logger
logger = get_logger('worker_tasks')


def _format_table_for_excel(table_dict: Dict[str, Any]) -> str:
    """
    Format table dictionary into readable text for Excel/CSV cells.
    
    Args:
        table_dict: Dictionary with 'headers' and 'data' keys
        
    Returns:
        Formatted string representation of table
    """
    if not table_dict or not isinstance(table_dict, dict):
        return ""
    
    headers = table_dict.get('headers', [])
    data = table_dict.get('data', [])
    
    if not headers and not data:
        return ""
    
    lines = []
    
    # Add headers
    if headers:
        lines.append(" | ".join(str(h) for h in headers))
        lines.append("-" * len(lines[0]))  # Separator line
    
    # Add data rows
    for row in data:
        lines.append(" | ".join(str(cell) for cell in row))
    
    return "\n".join(lines)


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


def process_pdfs_sync(
    files: List[Dict],
    rules: Optional[Dict] = None,
    username: Optional[str] = None,
    results_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    job_metadata: Optional[Dict] = None,
) -> Dict:
    def _emit_progress(state: str, meta: Dict[str, Any]):
        try:
            if progress_callback:
                progress_callback(state, meta)
            
            # Also broadcast via WebSocket for real-time UI updates
            if state == "PROGRESS" and job_metadata:
                watch_folder_id = None
                # Extract watch_folder_id from job_run if available
                job_run_id = job_metadata.get('job_run_id')
                if job_run_id:
                    try:
                        from app.db import get_session
                        from app.models import JobRun
                        with get_session() as session:
                            job_run = session.get(JobRun, job_run_id)
                            if job_run:
                                watch_folder_id = job_run.watch_folder_id
                    except:
                        pass
                
                if watch_folder_id:
                    try:
                        from app.routes.websocket_routes import broadcast_job_status_sync
                        broadcast_job_status_sync(
                            watch_folder_id=watch_folder_id,
                            status="progress",
                            data={
                                "job_run_id": job_run_id,
                                "files_processed": meta.get("processed", 0),
                                "files_found": meta.get("total", 0),
                                "current_file": meta.get("current_file", ""),
                                "percent": meta.get("percent", 0)
                            }
                        )
                    except Exception as ws_error:
                        # Silent fail - don't break job processing for WebSocket issues
                        pass
        except Exception:
            pass

    # Usage tracking removed - now using trial + license system
    
    reports = []
    total_files = 0

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
    
    # Usage limits removed - trial/license checks happen at startup
    
    _emit_progress("PROGRESS", {"processed": 0, "total": total, "current_file": "", "percent": 0})

    files_successfully_validated = 0
    
    for idx, f in enumerate(expanded_files):
        fname = f.get("filename")
        content = f.get("content") or b''

        _emit_progress(
            "PROGRESS",
            {
                "processed": processed,
                "total": total,
                "current_file": fname,
                "percent": int((processed / total * 100)) if total > 0 else 0,
            },
        )

        print(f"Processing {fname}: received {len(content)} bytes")
        if content:
            print(f"First 20 bytes: {content[:20]}")

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
            _emit_progress(
                "PROGRESS",
                {
                    "processed": processed,
                    "total": total,
                    "current_file": fname,
                    "percent": int((processed / total * 100)) if total > 0 else 0,
                },
            )
            continue

        try:
            text = extract_text_from_bytes(content or b'')
            report = validate_text(text, rules, pdf_bytes=content)
            reports.append({"filename": fname, "report": report})
            files_successfully_validated += 1  # Only count successful validations
        except Exception as exc:
            reports.append({"filename": fname, "error": f"processing error: {exc}"})

        processed += 1
        _emit_progress(
            "PROGRESS",
            {
                "processed": processed,
                "total": total,
                "current_file": fname,
                "percent": int((processed / total * 100)) if total > 0 else 0,
            },
        )

    # Ensure task_id and results_dir are properly set
    if not results_dir:
        # Only create new if not provided
        task_id = datetime.utcnow().strftime('%s')
        results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))
        os.makedirs(results_dir, exist_ok=True)
        logger.info(f"✓ Worker created new results directory: {results_dir}")
    else:
        # Use provided results_dir and extract task_id from it
        results_dir = os.path.abspath(results_dir)
        task_id = os.path.basename(results_dir.rstrip("/\\"))
        # Don't create directory here - it's already created by the caller
        logger.info(f"✓ Worker using existing results directory: {results_dir}")

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

    def detect_digital_signature(pdf_bytes: bytes) -> Tuple[str, str]:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            # Check for AcroForm signature fields
            root = reader.trailer.get('/Root', {})
            acroform = root.get('/AcroForm', {}) if isinstance(root, dict) else {}
            fields = acroform.get('/Fields', []) if isinstance(acroform, dict) else []
            for field in fields:
                try:
                    field_obj = field.get_object()
                    if field_obj.get('/FT') == '/Sig':
                        return 'Yes', 'Digital signature field found'
                except Exception:
                    continue
            # Check for /Sig annotation in pages
            for page in reader.pages:
                annots = page.get('/Annots', [])
                # Resolve IndirectObject if needed
                if hasattr(annots, 'get_object'):
                    annots = annots.get_object()
                # Ensure annots is a list
                if not isinstance(annots, list):
                    continue
                for annot_ref in annots:
                    try:
                        annot = annot_ref.get_object() if hasattr(annot_ref, 'get_object') else annot_ref
                        if annot.get('/Subtype') == '/Widget' and annot.get('/FT') == '/Sig':
                            return 'Yes', 'Digital signature annotation found'
                    except Exception:
                        continue
            return 'No', ''
        except Exception as e:
            return 'Error', str(e)

    date_regexes = [
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}\b",  # 21st August 2024
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{2,4}\b",  # August 21st, 2024
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # 11/09/2025
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",  # 2024-08-21
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
                    field_dict = {
                        'name': field.get('name', ''), 
                        'strategy': field.get('strategy', 'first')
                    }
                    # Include column if specified
                    if field.get('column'):
                        field_dict['column'] = field.get('column')
                    extraction_fields.append(field_dict)
                elif isinstance(field, str):
                    extraction_fields.append({'name': field, 'strategy': 'first'})

    csv_rows = []
    for entry in reports:
        fname = entry.get('filename')
        err = entry.get('error', '')
        report = entry.get('report', {})  # Get the validation report
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
        row['validation_report'] = report  # Store report for log generation
        if is_scanned:
            row['Error Details'] = scanned_message

        # Signature detection (text and digital) - only if requested in rules
        if 'signed' in validation_checks:
            is_signed, signed_value = detect_signed(text)
            is_digital, digital_value = detect_digital_signature(content_bytes)
            sig_type = []
            if is_signed == 'Yes':
                sig_type.append('Text')
            if is_digital == 'Yes':
                sig_type.append('Digital')
            if not sig_type:
                sig_type_str = 'None'
            else:
                sig_type_str = ', '.join(sig_type)
            row['Signature Type'] = sig_type_str
            row['Signed'] = is_signed
            if signed_value:
                row['Signature Details'] = signed_value
            row['Digital Signed'] = is_digital
            if digital_value:
                row['Digital Signature Details'] = digital_value

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

        # Use extractions from validation report (which used lookFor text)
        extractions = report.get('extractions', {}) if report else {}
        logger.info(f"DEBUG: Extractions for {fname}: {extractions}")
        logger.info(f"DEBUG: extraction_fields: {extraction_fields}")
        
        # Add all extracted fields (both regular fields and calculations)
        # The extractions dict already has everything including calculated fields
        for display_name, value in extractions.items():
            logger.info(f"DEBUG: Adding column '{display_name}' with value type: {type(value)}")
            
            # Format table data if it's a dictionary with table structure
            if isinstance(value, dict) and 'headers' in value and 'data' in value:
                # Single table - format as text
                logger.info(f"DEBUG: Formatting single table with {len(value.get('data', []))} rows")
                formatted = _format_table_for_excel(value)
                logger.info(f"DEBUG: Formatted table result: {formatted[:200] if formatted else 'EMPTY'}")
                row[display_name] = formatted
            elif isinstance(value, list) and value and isinstance(value[0], dict) and 'headers' in value[0]:
                # Multiple tables - format each and combine
                logger.info(f"DEBUG: Formatting {len(value)} tables")
                formatted_tables = []
                for idx, table in enumerate(value):
                    formatted = _format_table_for_excel(table)
                    logger.info(f"DEBUG: Table {idx + 1} formatted: {len(formatted)} chars")
                    formatted_tables.append(f"--- Table {idx + 1} ---\n" + formatted)
                combined = "\n\n".join(formatted_tables)
                logger.info(f"DEBUG: Combined tables result: {len(combined)} chars total")
                row[display_name] = combined
                logger.info(f"DEBUG: Assigned to row['{display_name}']")
            else:
                # Regular field
                logger.info(f"DEBUG: Regular field value: {str(value)[:100]}")
                row[display_name] = value

        if err:
            row['Error Details'] = err

        csv_rows.append(row)

    # Get list of table extraction field names to exclude from row expansion
    table_field_names = set()
    if extraction_fields:
        for field in extraction_fields:
            if isinstance(field, dict) and field.get('strategy') == 'table_extraction':
                field_name = field.get('name', '')
                # Match the display name transformation used in validator
                display_name = field_name.replace("_", " ").title()
                table_field_names.add(display_name)
                logger.info(f"DEBUG: Excluding table field '{display_name}' from row expansion")

    logger.info(f"DEBUG: Table fields to exclude: {table_field_names}")

    # Expand rows with multiple values (newline-separated) into separate rows
    # BUT exclude table extraction fields from expansion
    expanded_rows = []
    for row in csv_rows:
        # Check if any field has multiple values (contains newlines)
        # Exclude table extraction fields
        multi_value_fields = {}
        for key, value in row.items():
            if key not in table_field_names and isinstance(value, str) and '\n' in value:
                logger.info(f"DEBUG: Field '{key}' has newlines, will expand")
                multi_value_fields[key] = value.split('\n')
            elif key in table_field_names:
                logger.info(f"DEBUG: Field '{key}' is table field, SKIPPING expansion")
        
        # If no multi-value fields, keep the row as is
        if not multi_value_fields:
            expanded_rows.append(row)
        else:
            # Find the maximum number of occurrences
            max_occurrences = max(len(values) for values in multi_value_fields.values())
            
            # Create a row for each occurrence
            for i in range(max_occurrences):
                new_row = row.copy()
                for field, values in multi_value_fields.items():
                    # Use the i-th value, or empty string if this field has fewer values
                    new_row[field] = values[i] if i < len(values) else ''
                expanded_rows.append(new_row)
    
    csv_rows = expanded_rows

    if csv_rows:
        fieldnames = [k for k in csv_rows[0].keys() if k != 'validation_report']
    else:
        fieldnames = ['Filename', 'Status']

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    
    # Clean csv_rows for Excel/PDF generation - remove validation_report
    clean_rows = []
    for row in csv_rows:
        clean_row = {k: v for k, v in row.items() if k != 'validation_report'}
        clean_rows.append(clean_row)

    # Check if this is a table extraction job (has table extraction fields)
    has_table_extraction = any(
        isinstance(f, dict) and f.get('strategy') == 'table_extraction' 
        for f in extraction_fields
    ) if extraction_fields else False

    logger.info(f"DEBUG: has_table_extraction={has_table_extraction}, clean_rows count={len(clean_rows)}")
    if clean_rows:
        logger.info(f"DEBUG: First row keys: {list(clean_rows[0].keys())}")
    
    # Generate Excel report (pass the is_table_extraction flag)
    excel_filename = generate_excel_report(clean_rows, results_dir, timestamp, is_table_extraction=has_table_extraction)
    logger.info(f"DEBUG: Excel generated: {excel_filename}")
    
    # For table extraction, skip PDF and JSON (only Excel + extraction_log)
    if not has_table_extraction:
        # Generate PDF summary with job metadata
        pdf_filename = generate_pdf_summary(clean_rows, results_dir, timestamp, rules, job_metadata)
        
        # Generate JSON report for API
        report_json_path = os.path.join(results_dir, 'report.json')
        json_data = {
            'generated_at': datetime.utcnow().isoformat(),
            'total_files': total,
            'processed': processed,
            'results': clean_rows  # Use clean_rows without validation_report
        }
        with open(report_json_path, 'w', encoding='utf-8') as jf:
            json.dump(json_data, jf, indent=2, ensure_ascii=False)
    else:
        pdf_filename = None
        logger.info("Table extraction job - skipping PDF and JSON generation")
    
    # Generate detailed extraction log for debugging
    log_path = os.path.join(results_dir, 'extraction_log.txt')
    with open(log_path, 'w', encoding='utf-8') as log_file:
        log_file.write("="*80 + "\n")
        log_file.write(f"VALIDO EXTRACTION LOG\n")
        log_file.write(f"Generated: {datetime.utcnow().isoformat()}\n")
        log_file.write(f"Total Files: {total}\n")
        log_file.write(f"Processed: {processed}\n")
        log_file.write("="*80 + "\n\n")
        
        for row in csv_rows:
            log_file.write("\n" + "="*80 + "\n")
            log_file.write(f"FILE: {row.get('Filename', 'Unknown')}\n")
            log_file.write(f"STATUS: {row.get('Status', 'Unknown')}\n")
            log_file.write("="*80 + "\n")
            
            # Get the validation report if available
            if 'validation_report' in row:
                report = row['validation_report']
                
                # PDF Text Preview
                if 'pdf_text_preview' in report:
                    log_file.write("\n--- PDF TEXT PREVIEW (First 1000 chars) ---\n")
                    log_file.write(report['pdf_text_preview'])
                    log_file.write("\n" + "-"*80 + "\n")
                
                # Extraction Log
                if 'extraction_log' in report and report['extraction_log']:
                    log_file.write("\n--- FIELD EXTRACTION DETAILS ---\n")
                    for log_entry in report['extraction_log']:
                        log_file.write(f"\nField: {log_entry.get('field_name', 'Unknown')}\n")
                        log_file.write(f"  Looking for: '{log_entry.get('look_for_text', '')}'\n")
                        log_file.write(f"  Strategy: {log_entry.get('strategy', 'first')}\n")
                        log_file.write(f"  Found: {log_entry.get('found', False)}\n")
                        log_file.write(f"  Extracted Value: '{log_entry.get('extracted_value', '')}'\n")
                        log_file.write(f"  Match Position: {log_entry.get('match_position', -1)}\n")
                        if 'context' in log_entry:
                            log_file.write(f"  Context:\n    {log_entry['context']}\n")
                        log_file.write("-"*40 + "\n")
                
                # Validation Results
                if 'validations' in report and report['validations']:
                    log_file.write("\n--- VALIDATION CHECKS ---\n")
                    for key, val in report['validations'].items():
                        log_file.write(f"{key}: {val}\n")
            
            log_file.write("\n")
    
    # No longer creating ZIP file - users can download individual files
    zip_filename = None

    # User tracking removed - trial/license tracking happens at startup
    
    # Update JobRun record if this is from an automation job
    job_run_id = job_metadata.get('job_run_id') if job_metadata else None
    
    # Count successes and failures FIRST (before any conditional blocks)
    files_succeeded = sum(1 for r in reports if 'report' in r and 'error' not in r)
    files_failed = sum(1 for r in reports if 'error' in r)
    
    if job_metadata and job_run_id:
        try:
            from app.db import get_session
            from app.models import JobRun
            
            with get_session() as session:
                job_run = session.get(JobRun, job_run_id)
                if job_run:
                    job_run.completed_at = datetime.now()
                    job_run.files_processed = processed
                    job_run.files_succeeded = files_succeeded
                    job_run.files_failed = files_failed
                    
                    # Determine final status based on actual results
                    if files_failed == 0:
                        job_run.status = "success"
                    elif files_succeeded > 0:
                        job_run.status = "partial"
                    else:
                        job_run.status = "failed"
                        job_run.error_message = "All files failed to process"
                    
                    session.add(job_run)
                    session.commit()
                    print(f"Updated JobRun {job_run_id}: {job_run.status}, {files_succeeded} succeeded, {files_failed} failed")
                    
                    # Broadcast job completion via WebSocket
                    try:
                        from app.routes.websocket_routes import broadcast_job_status_sync
                        broadcast_job_status_sync(
                            watch_folder_id=job_run.watch_folder_id,
                            status="completed",
                            data={
                                "job_run_id": job_run_id,
                                "final_status": job_run.status,
                                "files_processed": processed,
                                "files_succeeded": files_succeeded,
                                "files_failed": files_failed
                            }
                        )
                    except Exception as ws_error:
                        print(f"Failed to broadcast completion via WebSocket: {ws_error}")
                    
        except Exception as e:
            print(f"Failed to update JobRun: {e}")
    
    # Clean up cloud temp directory if used
    cloud_temp_dir = job_metadata.get('cloud_temp_dir') if job_metadata else None
    if cloud_temp_dir:
        try:
            from app.services.cloud.cloud_orchestrator import CloudOrchestrator
            CloudOrchestrator.cleanup_temp_directory(cloud_temp_dir)
            logger.info(f"Cleaned up cloud temp directory: {cloud_temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup cloud temp directory: {e}")
    
    # Determine response status
    response_status = 'completed'
    response_message = "All files processed successfully" if files_succeeded == total else None
    
    return {
        'status': response_status,
        'message': response_message,
        'total': total,
        'processed': processed,
        'files_succeeded': files_succeeded,
        'files_skipped': 0,
        'files': reports,
        'result_files': {
            'zip': f'/api/v1/tasks/{task_id}/results.zip'
        }
    }


# backward-compatible export name
process_pdfs = process_pdfs_sync
