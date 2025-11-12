# app/routes/validation_routes.py
"""
PDF Validation Routes
Handles file uploads, task submission, and result downloads.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional
import os
import json
import uuid
import glob
import re
import ast

from app.services.parser import extract_text_from_bytes
from app.services.validator import validate_text
from app.utils.logger import get_logger
from app.utils.usage_tracker import check_usage_limit, record_usage
from app.db import get_session

logger = get_logger("ValidationRoutes")

router = APIRouter(prefix="/api/v1", tags=["validation"])

# Will be set during router registration
RESULTS_ROOT = None

def set_results_root(path: str):
    """Set the results root path."""
    global RESULTS_ROOT
    RESULTS_ROOT = path


def ensure_results_dir(task_id: str) -> str:
    """Ensure results directory exists for task."""
    if not RESULTS_ROOT:
        raise ValueError("RESULTS_ROOT not configured")
    p = os.path.join(RESULTS_ROOT, task_id)
    os.makedirs(p, exist_ok=True)
    return p


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and validate a single PDF file.
    Returns immediate validation results.
    """
    logger.info(f"Upload request for file: {file.filename}")
    
    filename_val = (file.filename or "").lower()
    if not filename_val.endswith('.pdf'):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF uploads are accepted")

    try:
        body = await file.read()
        if len(body) == 0:
            logger.warning(f"Empty file uploaded: {file.filename}")
            raise HTTPException(status_code=400, detail="Empty file not allowed")
        
        logger.info(f"Processing file: {file.filename}, size: {len(body)} bytes")
        text = extract_text_from_bytes(body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Parser error for {file.filename}: {exc}")
        raise HTTPException(status_code=500, detail=f"parser error: {exc}")

    report = validate_text(text)
    logger.info(f"Validation complete for {file.filename}")
    return JSONResponse(content={"filename": file.filename, "report": report})


@router.post("/submit")
async def submit_files(
    files: List[UploadFile] = File(...),
    rules: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
):
    """
    Submit batch of files for processing with optional rules.
    Returns task_id for tracking progress.
    """
    logger.info(f"Submit request with {len(files)} files, username: {username}")
    
    # Check usage limits for free tier
    with get_session() as db:
        usage_status = check_usage_limit(db)
        
        if usage_status['exceeded']:
            logger.warning(f"Free tier limit exceeded: {usage_status['count']}/{usage_status['limit']}")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Free tier limit reached",
                    "message": f"You've processed {usage_status['count']} PDFs this month. Free tier limit is {usage_status['limit']} PDFs/month.",
                    "upgrade_url": "https://valido-app.github.io/#pricing"
                }
            )
        
        # Show warning if approaching limit
        if usage_status['warning']:
            logger.info(f"Usage warning: {usage_status['remaining']} PDFs remaining")
    
    # Validate file count
    if len(files) > 500:
        logger.warning(f"Too many files: {len(files)}")
        raise HTTPException(
            status_code=400,
            detail="Maximum 500 files allowed per batch. Please split your upload into smaller batches."
        )

    # Validate file types and sizes
    total_size = 0
    for f in files:
        if not f.filename:
            logger.warning("File without filename")
            raise HTTPException(status_code=400, detail="File must have a filename")
        
        filename_lower = f.filename.lower()
        if not (filename_lower.endswith('.pdf') or filename_lower.endswith('.zip')):
            logger.warning(f"Invalid file type: {f.filename}")
            raise HTTPException(
                status_code=400, 
                detail=f"Only PDF and ZIP files allowed: {f.filename}"
            )
        
        # No file size limit for local desktop app
        content = await f.read()
        total_size += len(content)
        await f.seek(0)  # Reset for later read

    # No total upload size limit for local desktop app

    # Parse rules with defensive handling
    parsed_rules = None
    if rules:
        parsed_rules = _parse_rules(rules)

    # Read file bytes
    payload = []
    for f in files:
        content = await f.read()
        payload.append({"filename": f.filename, "content": content})

    # Create task and submit to worker
    task_id = str(uuid.uuid4())
    results_dir = ensure_results_dir(task_id)
    logger.info(f"Task {task_id} created, results dir: {results_dir}")

    # Submit to local worker
    try:
        import sys
        # Go up 3 levels: validation_routes.py -> routes -> app -> backend
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        
        from local_worker import submit_task
        submit_task(
            "process_pdfs",
            files=payload,
            rules=parsed_rules,
            username=username,
            results_dir=results_dir,
            task_id=task_id
        )
        logger.info(f"Task {task_id} submitted to local worker")
    except Exception as e:
        logger.error(f"Failed to submit task to local worker: {e}")
        return JSONResponse(
            content={"task_id": task_id, "error": "Failed to submit task"}
        )

    return JSONResponse(content={"task_id": task_id})


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status and progress of a processing task."""
    logger.info(f"Task status request for {task_id}")
    
    # Validate task_id format
    try:
        uuid.UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid task_id format: {task_id}")
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    # Query local worker for status
    try:
        import sys
        # Go up 3 levels: validation_routes.py -> routes -> app -> backend
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        
        from local_worker import get_task_status as get_worker_status
        task_info = get_worker_status(task_id)
        
        if task_info:
            state = task_info.get("status")
            # Normalize for frontend compatibility
            info = {}
            result = task_info.get("result")
            if isinstance(result, dict):
                info.update(result)
            else:
                info["result"] = result
            info["error"] = task_info.get("error")
            
            return JSONResponse(
                content={"task_id": task_id, "state": state, "info": info}
            )
        else:
            return JSONResponse(
                content={"task_id": task_id, "state": "UNKNOWN", "info": None}
            )
    except Exception as e:
        logger.error(f"Failed to get task status from worker: {e}")
        return JSONResponse(
            content={"task_id": task_id, "state": "UNKNOWN", "info": None}
        )


@router.get("/tasks/{task_id}/result.csv")
async def download_task_csv(task_id: str):
    """Download CSV results for a completed task."""
    logger.info(f"CSV download request for {task_id}")
    
    # Validate task_id
    try:
        uuid.UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid task_id for CSV: {task_id}")
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    # Security: prevent path traversal
    results_dir = os.path.join(RESULTS_ROOT, task_id)
    if not results_dir.startswith(RESULTS_ROOT):
        logger.error(f"Path traversal attempt: {results_dir}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Find CSV file
    csv_files = glob.glob(os.path.join(results_dir, 'valido_results_*.csv'))
    if not csv_files:
        csv_path = os.path.join(results_dir, 'results.csv')
        if not os.path.exists(csv_path):
            logger.warning(f"CSV not found for {task_id}")
            raise HTTPException(status_code=404, detail="CSV result not found")
        return FileResponse(
            csv_path, 
            media_type='text/csv', 
            filename=f"{task_id}-results.csv"
        )
    
    # Return most recent CSV
    csv_path = max(csv_files, key=os.path.getctime)
    filename = os.path.basename(csv_path)
    return FileResponse(csv_path, media_type='text/csv', filename=filename)


@router.get("/tasks/{task_id}/report.json")
async def download_task_report(task_id: str):
    """Download JSON report for a completed task."""
    # Validate task_id
    try:
        uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    results_dir = os.path.join(RESULTS_ROOT, task_id)
    report_path = os.path.join(results_dir, 'report.json')
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        report_path, 
        media_type='application/json', 
        filename=f"{task_id}-report.json"
    )


@router.get("/tasks/{task_id}/results.zip")
async def download_task_zip(task_id: str):
    """Download ZIP package containing all results for a task."""
    logger.info(f"ZIP download request for {task_id}")
    
    # Validate task_id
    try:
        uuid.UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid task_id for ZIP: {task_id}")
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    # Security: prevent path traversal
    results_dir = os.path.join(RESULTS_ROOT, task_id)
    if not results_dir.startswith(RESULTS_ROOT):
        logger.error(f"Path traversal attempt: {results_dir}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Find ZIP file
    zip_files = glob.glob(os.path.join(results_dir, 'valido_results_*.zip'))
    if not zip_files:
        logger.warning(f"ZIP not found for {task_id}")
        raise HTTPException(status_code=404, detail="ZIP result not found")
    
    # Return most recent ZIP
    zip_path = max(zip_files, key=os.path.getctime)
    filename = os.path.basename(zip_path)
    return FileResponse(
        zip_path, 
        media_type='application/zip', 
        filename=filename
    )


def _parse_rules(rules: str) -> dict:
    """
    Parse rules with defensive handling for various formats.
    Tries: JSON -> normalized JSON -> ast.literal_eval -> quote replacement.
    """
    raw = rules
    
    # Handle bytes
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode('utf-8')
        except Exception:
            raw = raw.decode('latin-1')
    
    raw_str = raw.strip() if isinstance(raw, str) else str(raw)
    
    # Try standard JSON
    try:
        return json.loads(raw_str)
    except Exception as exc_json:
        logger.warning(f"Failed to parse rules JSON: {exc_json}")
    
    # Try normalized JSON
    try:
        normalized = re.sub(r"'{2,}", '"', raw_str)
        normalized = re.sub(r'([\{,\s])(\w[\w\d_]*)\s*:', r'\1"\2":', normalized)
        return json.loads(normalized)
    except Exception:
        pass
    
    # Try ast.literal_eval
    try:
        return ast.literal_eval(raw_str)
    except Exception:
        pass
    
    # Try quote replacement
    try:
        return json.loads(raw_str.replace("'", '"'))
    except Exception:
        logger.error(f"Invalid rules payload: {raw_str[:100]}...")
        raise HTTPException(
            status_code=400, 
            detail="Invalid rules JSON format"
        )


@router.get("/usage")
async def get_usage_info():
    """Get current usage information for free tier."""
    with get_session() as db:
        usage_status = check_usage_limit(db)
        
        from app.utils.usage_tracker import get_usage_display
        display_text = get_usage_display(db)
        
        return JSONResponse(content={
            "count": usage_status['count'],
            "limit": usage_status['limit'],
            "remaining": usage_status['remaining'],
            "exceeded": usage_status['exceeded'],
            "warning": usage_status['warning'],
            "display": display_text
        })
