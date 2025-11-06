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

# Do NOT import models at module import time here; register them during startup
# to avoid metadata duplication and ensure tables are created once when the app
# process is fully initialized.

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


@app.on_event("startup")
async def _on_startup():
    """FastAPI startup hook: import model definitions and create DB tables.

    This ensures models are registered with SQLModel/SQLAlchemy only when the
    application process starts (avoids double-registration when modules are
    imported in different contexts or by tooling)."""
    try:
        # Import models so SQLModel metadata is populated
        from . import models  # noqa: F401
        from .db import create_db_and_tables

        create_db_and_tables()
        print("✓ Database tables created successfully (startup)")
    except Exception as e:
        # Startup should not crash hard for non-fatal issues in some dev/test flows.
        # Log and continue so other routes may still be inspected during dev.
        print(f"Warning: Failed to initialize database at startup: {e}")
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
    # Limit to 500 files per batch
    if len(files) > 500:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 500 files allowed per batch. Please split your upload into smaller batches."
        )
    
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
    # Find the CSV file with timestamp pattern
    import glob
    csv_files = glob.glob(os.path.join(results_dir, 'valido_results_*.csv'))
    if not csv_files:
        # Fallback to old naming for backward compatibility
        csv_path = os.path.join(results_dir, 'results.csv')
        if not os.path.exists(csv_path):
            raise HTTPException(status_code=404, detail="CSV result not found")
        return FileResponse(csv_path, media_type='text/csv', filename=f"{task_id}-results.csv")
    
    # Use the most recent file if multiple exist
    csv_path = max(csv_files, key=os.path.getctime)
    filename = os.path.basename(csv_path)
    return FileResponse(csv_path, media_type='text/csv', filename=filename)


@app.get("/api/v1/tasks/{task_id}/report.json")
async def download_task_report(task_id: str):
    results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))
    report_path = os.path.join(results_dir, 'report.json')
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_path, media_type='application/json', filename=f"{task_id}-report.json")


@app.get("/api/v1/tasks/{task_id}/results.zip")
async def download_task_zip(task_id: str):
    """Serve the ZIP file containing CSV results."""
    results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))
    # Find the ZIP file with timestamp pattern
    import glob
    zip_files = glob.glob(os.path.join(results_dir, 'valido_results_*.zip'))
    if not zip_files:
        # Fallback to old naming for backward compatibility
        zip_path = os.path.join(results_dir, 'results.zip')
        if not os.path.exists(zip_path):
            raise HTTPException(status_code=404, detail="ZIP file not found")
        return FileResponse(zip_path, media_type='application/zip', filename=f"valido-results-{task_id}.zip")
    
    # Use the most recent file if multiple exist
    zip_path = max(zip_files, key=os.path.getctime)
    filename = os.path.basename(zip_path)
    return FileResponse(zip_path, media_type='application/zip', filename=filename)


# Include ruleset routes if available
try:
    # Models already imported at top of file
    from .routes.ruleset_routes import router as ruleset_router

    app.include_router(ruleset_router)
    print("✓ Ruleset routes included successfully")
except Exception as e:
    # not critical at runtime; routes may be missing during partial edits
    print(f"Warning: Failed to include ruleset routes: {e}")
    pass


# Include user routes if available
try:
    from .routes.user_routes import router as user_router

    app.include_router(user_router)
except Exception:
    pass


# Include watch folder routes
try:
    from .routes.watch_folder_routes import router as watch_folder_router

    app.include_router(watch_folder_router)
    print("✓ Watch folder routes included successfully")
except Exception as e:
    print(f"Warning: Failed to include watch folder routes: {e}")
    pass


# Include agent download routes
try:
    from .routes.agent_routes import router as agent_router

    app.include_router(agent_router)
    print("✓ Agent download routes included successfully")
except Exception as e:
    print(f"Warning: Failed to include agent routes: {e}")
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
