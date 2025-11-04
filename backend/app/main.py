from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from .services.parser import extract_text_from_bytes
from .services.validator import validate_text
from typing import List, Optional
from fastapi import Form
from backend.celery_app import celery_app
from celery.result import AsyncResult
import io
import zipfile
import json

app = FastAPI(title="PDF Validator (stub)")

# Allow CORS for local development so the served frontend can call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# Initialize DB tables (SQLite via SQLModel)
try:
    from .db import create_db_and_tables

    create_db_and_tables()
except Exception:
    # If import fails in some environments (tests or tooling), continue without crash
    pass


@app.post("/api/v1/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Accept a single PDF upload and return a validation report.

    This is a minimal stub: it extracts text via the parser stub and runs
    basic deterministic validation via the validator stub.
    """
    # Guard: some UploadFile implementations may have filename==None per typing; be defensive
    filename_val = (file.filename or "").lower()
    if not filename_val.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF uploads are accepted")

    body = await file.read()
    try:
        text = extract_text_from_bytes(body)
    except Exception as exc:
        # Keep comments short and actionable; avoid long AI notes in code.
        raise HTTPException(status_code=500, detail=f"parser error: {exc}")

    report = validate_text(text)
    return JSONResponse(content={"filename": file.filename, "report": report})


@app.post("/api/v1/submit")
async def submit_files(
    files: List[UploadFile] = File(...),
    rules: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
):
    """Accept one or more PDF files or a ZIP (containing PDFs) and optional rules JSON.

    Returns a Celery task id that can be polled for progress/result.
    """
    # Parse rules if provided (expect JSON string in a form field)
    parsed_rules = None
    if rules:
        # rules may arrive as a str, bytes, or a form part with various quoting styles.
        # Be defensive: attempt json.loads, fall back to ast.literal_eval, or a
        # single-quote-to-double-quote heuristic before failing.
        raw = rules
        if isinstance(raw, (bytes, bytearray)):
            try:
                raw = raw.decode('utf-8')
            except Exception:
                raw = raw.decode('latin-1')
        # Trim whitespace
        if isinstance(raw, str):
            raw_str = raw.strip()
        else:
            raw_str = str(raw)

        # Try strict JSON first
        try:
            parsed_rules = json.loads(raw_str)
        except Exception as exc_json:
            # Try a normalization pass that fixes common non-JSON JS-like object syntaxes.
            try:
                import re

                # 1) Normalize repeated single quotes to a single double-quote
                normalized = re.sub(r"'{2,}", '"', raw_str)
                # 2) Add double quotes around unquoted property names: {key: -> {"key":
                normalized = re.sub(r'([\{,\s])(\w[\w\d_]*)\s*:', r'\1"\2":', normalized)
                parsed_rules = json.loads(normalized)
            except Exception:
                # Try Python literal eval (handles single-quoted dicts)
                try:
                    import ast

                    parsed_rules = ast.literal_eval(raw_str)
                except Exception:
                    # Last resort: replace any remaining single quotes with double quotes and try JSON again
                    try:
                        parsed_rules = json.loads(raw_str.replace("'", '"'))
                    except Exception:
                        # Log the raw payload for debugging and return a helpful error
                        print('Failed to parse rules payload:', repr(raw_str))
                        raise HTTPException(status_code=400, detail=f"invalid rules JSON: {exc_json}")

    # Read file bytes into a serializable structure for the Celery task
    payload = []
    for f in files:
        content = await f.read()
        payload.append({"filename": f.filename, "content": content})

    # Enqueue background Celery task by importing the task function so Celery registers
    # and names the task consistently with the running package layout.
    try:
        from app.tasks.worker_tasks import process_pdfs
    except Exception:
        # Fallback import path if the package is referenced differently in the running environment
        from backend.app.tasks.worker_tasks import process_pdfs

    # Use send_task with the registered task name to avoid static analysis issues
    task_name = getattr(process_pdfs, 'name', None) or 'backend.app.tasks.worker_tasks.process_pdfs'
    celery_task = celery_app.send_task(task_name, args=(payload, parsed_rules, username))
    return JSONResponse(content={"task_id": celery_task.id})


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Return Celery task state and meta/result if available."""
    res = AsyncResult(task_id, app=celery_app)
    response = {"task_id": task_id, "state": res.state}
    try:
        info = res.info
        # Ensure info is JSON-serializable; otherwise fall back to string representation.
        try:
            # quick check
            json.dumps(info)
            response["info"] = info
        except Exception:
            response["info"] = str(info)
    except Exception:
        response["info"] = None
    return JSONResponse(content=response)


@app.get("/api/v1/tasks/{task_id}/result.csv")
async def download_task_csv(task_id: str):
    """Serve the CSV results for a completed task if available."""
    results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))
    csv_path = os.path.join(results_dir, 'results.csv')
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSV result not found")
    return FileResponse(csv_path, media_type='text/csv', filename=f"{task_id}-results.csv")


@app.get("/api/v1/tasks/{task_id}/report.json")
async def download_task_report(task_id: str):
    results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))
    report_path = os.path.join(results_dir, 'report.json')
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_path, media_type='application/json', filename=f"{task_id}-report.json")


# Include ruleset routes if available
try:
    from .routes.ruleset_routes import router as ruleset_router

    app.include_router(ruleset_router)
except Exception:
    # not critical at runtime; routes may be missing during partial edits
    pass


# Include user routes if available
try:
    from .routes.user_routes import router as user_router

    app.include_router(user_router)
except Exception:
    pass


# Include AI stub routes if available
try:
    from .routes.ai_stub import router as ai_router

    app.include_router(ai_router)
except Exception:
    pass


# Serve frontend static files (try a few likely locations so Docker-mounted or image-copied frontend is found)
try:
    candidates = [
        os.path.abspath(os.path.join(os.getcwd(), '..', 'frontend')),
        os.path.abspath(os.path.join(os.getcwd(), 'frontend')),
        '/app/frontend',
        os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'frontend')),
    ]
    for frontend_dir in candidates:
        if frontend_dir and os.path.exists(frontend_dir):
            # Mount static files after API routes so API endpoints (e.g. /api/v1/...) are matched first.
            app.mount('/', StaticFiles(directory=frontend_dir, html=True), name='frontend')
            break
except Exception:
    # Non-fatal: if static files can't be mounted in some environments, continue.
    pass
