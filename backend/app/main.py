# main.py (replace your existing backend FastAPI entrypoint with this)
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import json
import uuid
import asyncio
import time
import traceback
import glob
import sys
from typing import List, Optional, Dict, Any

# Absolute imports for PyInstaller compatibility
from app.services.parser import extract_text_from_bytes
from app.services.validator import validate_text
from app.utils.logger import get_logger
from app.db import get_session
from app.models import User, Ruleset, WatchFolder
from app.license import get_license_banner, LicenseManager
# Optional: load .env for local development (contains OPENAI_API_KEY)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; environment variables are preferred in production
    pass

# AI stub import (generate ruleset using OpenAI)
try:
    from app.routes.ai_stub import generate_ruleset_from_prompt
except Exception:
    generate_ruleset_from_prompt = None

logger = get_logger("ValidoMain")

# Do not import DB models at top-level beyond startup (same pattern you had)
app = FastAPI(title="PDF Validator (single-process)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Network info utility
def get_local_ip():
    """Get the local IP address for network access."""
    try:
        # Create a socket to get the local IP
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "192.168.1.100"  # Fallback

@app.get("/api/v1/network-info")
def get_network_info():
    """Get network access information."""
    local_ip = get_local_ip()
    return {
        "localhost": "http://localhost:8000",
        "network": f"http://{local_ip}:8000"
    }

@app.get("/api/v1/results-path")
def get_results_path():
    """Get the local path where results are stored."""
    results_dir = os.path.abspath(os.path.join(os.getcwd(), "results"))
    return {
        "results_directory": results_dir,
        "exists": os.path.exists(results_dir)
    }

# Simple in-memory task registry.
# Structure:
# tasks[task_id] = {"state":"PENDING"|"STARTED"|"SUCCESS"|"FAILURE", "info":..., "result_path":..., "created_at":...}
# Note: Task state now managed by local_worker.py

RESULTS_ROOT = os.path.abspath(os.path.join(os.getcwd(), "results"))

def ensure_results_dir(task_id: str):
    p = os.path.join(RESULTS_ROOT, task_id)
    os.makedirs(p, exist_ok=True)
    return p


# -- Startup DB registration (same as before) --
@app.on_event("startup")
async def _on_startup():
    try:
        from . import models  # noqa: F401
        from .db import create_db_and_tables
        create_db_and_tables()
        logger.info("Database tables created successfully (startup)")
    except Exception as e:
        logger.error(f"Failed to initialize database at startup: {e}")
        # continue; DB may be optional in local dev


# -- Health --
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# -- Diagnostics --
@app.get("/api/v1/diagnostics")
async def diagnostics():
    """Get system diagnostics information."""
    logger.info("Diagnostics request")
    import psutil
    import platform
    from app.db import get_session
    from app.models import User, Ruleset, WatchFolder

    try:
        # System info
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_free": psutil.disk_usage('/').free if os.name == 'posix' else psutil.disk_usage('C:\\').free,
        }

        # Database stats
        with get_session() as session:
            db_stats = {
                "users_count": session.query(User).count(),
                "rulesets_count": session.query(Ruleset).count(),
                "watch_folders_count": session.query(WatchFolder).count(),
            }

        # Application stats
        results_dir = os.path.join(os.getcwd(), "results")
        app_stats = {
            "results_dir_exists": os.path.exists(results_dir),
            "results_files_count": len(os.listdir(results_dir)) if os.path.exists(results_dir) else 0,
            "uptime": "N/A",  # Would need to track start time
        }

        return {
            "system": system_info,
            "database": db_stats,
            "application": app_stats,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Diagnostics error: {e}", exc_info=True)
        return {"error": str(e)}


@app.get("/api/v1/diagnostics/export")
async def export_diagnostics():
    """
    Export comprehensive diagnostics package for support.
    Returns a ZIP file containing:
    - System information
    - Recent logs (last 1000 lines)
    - Error logs
    - Database statistics
    - Validation summaries
    
    Customer can download this and email to support for remote debugging.
    """
    logger.info("Diagnostics export requested")
    import tempfile
    import zipfile
    import psutil
    import platform
    from app.db import get_session
    from app.models import User, Ruleset, WatchFolder
    from app.utils.logger import get_recent_logs, get_error_logs
    
    try:
        # Create temporary directory for diagnostics
        with tempfile.TemporaryDirectory() as temp_dir:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # 1. System information
            system_info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "disk_free_gb": round((psutil.disk_usage('/').free if os.name == 'posix' else psutil.disk_usage('C:\\').free) / (1024**3), 2),
                "timestamp": timestamp,
            }
            
            system_file = os.path.join(temp_dir, 'system_info.json')
            with open(system_file, 'w') as f:
                json.dump(system_info, f, indent=2)
            
            # 2. License status
            try:
                license_info = LicenseManager.get_license_info()
                license_file = os.path.join(temp_dir, 'license_info.json')
                with open(license_file, 'w') as f:
                    json.dump(license_info, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not export license info: {e}")
            
            # 3. Database statistics
            try:
                with get_session() as session:
                    db_stats = {
                        "users": session.query(User).count(),
                        "rulesets": session.query(Ruleset).count(),
                        "watch_folders": session.query(WatchFolder).count(),
                        "watch_folders_active": session.query(WatchFolder).filter(WatchFolder.enabled == True).count(),
                    }
                
                db_file = os.path.join(temp_dir, 'database_stats.json')
                with open(db_file, 'w') as f:
                    json.dump(db_stats, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not export database stats: {e}")
            
            # 4. Recent logs (last 1000 lines)
            recent_logs = get_recent_logs(1000)
            log_file = os.path.join(temp_dir, 'recent_logs.txt')
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(recent_logs)
            
            # 5. Error logs
            error_logs = get_error_logs(500)
            error_file = os.path.join(temp_dir, 'error_logs.txt')
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(error_logs)
            
            # 6. Validation summaries (last 10 validations)
            results_dir = os.path.join(os.getcwd(), "results")
            if os.path.exists(results_dir):
                result_folders = sorted([
                    d for d in os.listdir(results_dir)
                    if os.path.isdir(os.path.join(results_dir, d))
                ], reverse=True)[:10]
                
                summaries = []
                for folder in result_folders:
                    json_files = glob.glob(os.path.join(results_dir, folder, '*.json'))
                    if json_files:
                        try:
                            with open(json_files[0], 'r') as f:
                                data = json.load(f)
                                summaries.append({
                                    'folder': folder,
                                    'total_files': data.get('total_files', 0),
                                    'processed': data.get('processed', 0),
                                    'generated_at': data.get('generated_at', 'unknown')
                                })
                        except:
                            pass
                
                if summaries:
                    summary_file = os.path.join(temp_dir, 'validation_summaries.json')
                    with open(summary_file, 'w') as f:
                        json.dump(summaries, f, indent=2)
            
            # 7. README for support
            readme = f"""
Valido Diagnostics Package
==========================

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

This package contains diagnostic information to help Valido support 
troubleshoot any issues you're experiencing.

Contents:
---------
1. system_info.json - System hardware and OS information
2. license_info.json - Your license status
3. database_stats.json - Database usage statistics
4. recent_logs.txt - Last 1000 log lines from application
5. error_logs.txt - Recent error logs for quick scanning
6. validation_summaries.json - Summary of last 10 validation runs

Privacy:
--------
This package does NOT contain:
- Your PDF files
- PDF content or extracted text
- Personal identification information
- Business data

It only contains technical logs and system information needed 
for debugging.

Support:
--------
Please email this ZIP file to: support@valido.app
Include a brief description of the issue you're experiencing.

We aim to respond within 48 hours.

Thank you for using Valido!
"""
            readme_file = os.path.join(temp_dir, 'README.txt')
            with open(readme_file, 'w') as f:
                f.write(readme)
            
            # Create ZIP file
            zip_filename = f'valido_diagnostics_{timestamp}.zip'
            zip_path = os.path.join(temp_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for filename in os.listdir(temp_dir):
                    if filename != zip_filename:
                        file_path = os.path.join(temp_dir, filename)
                        zf.write(file_path, filename)
            
            logger.info(f"Diagnostics package created: {zip_filename}")
            
            # Return the ZIP file
            return FileResponse(
                zip_path,
                media_type='application/zip',
                filename=zip_filename,
                headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
            )
    
    except Exception as e:
        logger.error(f"Failed to export diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create diagnostics: {str(e)}")


# -- License --
@app.get("/api/v1/license/status")
async def license_status():
    """Get license status."""
    logger.info("License status request")
    try:
        license_info = LicenseManager.get_license_info()
        banner = get_license_banner()
        return {
            "license": license_info,
            "banner": banner,
        }
    except Exception as e:
        logger.error(f"License status error: {e}", exc_info=True)
        return {"error": str(e)}


# -- First-run wizard --
@app.get("/api/v1/setup/status")
async def setup_status():
    """Check if application has been set up."""
    logger.info("Setup status check")
    try:
        with get_session() as session:
            users_count = session.query(User).count()
            rulesets_count = session.query(Ruleset).count()

        is_configured = users_count > 0 and rulesets_count > 0

        return {
            "is_configured": is_configured,
            "users_count": users_count,
            "rulesets_count": rulesets_count,
            "needs_setup": not is_configured,
        }
    except Exception as e:
        logger.error(f"Setup status error: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/v1/setup/initialize")
async def setup_initialize():
    """Initialize the application with default settings."""
    logger.info("Initializing application")
    try:
        with get_session() as session:
            # Create default admin user if none exists
            existing_users = session.query(User).count()
            if existing_users == 0:
                admin_user = User(username="admin", total_processed=0)
                session.add(admin_user)
                session.commit()
                logger.info("Created default admin user")

            # Create default ruleset if none exists
            existing_rulesets = session.query(Ruleset).count()
            if existing_rulesets == 0:
                default_ruleset = Ruleset(
                    name="Default Ruleset",
                    rules={
                        "source_text": "Default validation rules",
                        "generated_rules": [
                            {"description": "Document must contain required fields", "hint": "required"},
                            {"description": "All signatures must be valid", "hint": "required"}
                        ]
                    },
                    is_active=True
                )
                session.add(default_ruleset)
                session.commit()
                logger.info("Created default ruleset")

        return {"message": "Application initialized successfully"}
    except Exception as e:
        logger.error(f"Setup initialization error: {e}")
        return {"error": str(e)}


# -- Upload single PDF synchronous validation endpoint (unchanged) --
@app.post("/api/v1/upload")
async def upload_pdf(file: UploadFile = File(...)):
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


# -- Task submission endpoint (replaces Celery send_task) --
@app.post("/api/v1/submit")
async def submit_files(
    files: List[UploadFile] = File(...),
    rules: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
):
    logger.info(f"Submit request with {len(files)} files, username: {username}")
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
            raise HTTPException(status_code=400, detail=f"Only PDF and ZIP files allowed: {f.filename}")
        
        # Read file to check size (limit to 50MB per file)
        content = await f.read()
        if len(content) > 50 * 1024 * 1024:
            logger.warning(f"File too large: {f.filename}, {len(content)} bytes")
            raise HTTPException(status_code=400, detail=f"File too large (max 50MB): {f.filename}")
        total_size += len(content)
        await f.seek(0)  # Reset for later read

    if total_size > 500 * 1024 * 1024:  # 500MB total
        logger.warning(f"Total upload too large: {total_size} bytes")
        raise HTTPException(status_code=400, detail="Total upload size exceeds 500MB")

    # parse rules (exact same defensive parsing you had)
    parsed_rules = None
    if rules:
        raw = rules
        if isinstance(raw, (bytes, bytearray)):
            try:
                raw = raw.decode('utf-8')
            except Exception:
                raw = raw.decode('latin-1')
        raw_str = raw.strip() if isinstance(raw, str) else str(raw)
        try:
            parsed_rules = json.loads(raw_str)
            logger.info("Rules parsed successfully")
        except Exception as exc_json:
            logger.warning(f"Failed to parse rules JSON: {exc_json}")
            try:
                import re
                normalized = re.sub(r"'{2,}", '"', raw_str)
                normalized = re.sub(r'([\{,\s])(\w[\w\d_]*)\s*:', r'\1"\2":', normalized)
                parsed_rules = json.loads(normalized)
                logger.info("Rules parsed with normalization")
            except Exception:
                try:
                    import ast
                    parsed_rules = ast.literal_eval(raw_str)
                    logger.info("Rules parsed with ast.literal_eval")
                except Exception:
                    try:
                        parsed_rules = json.loads(raw_str.replace("'", '"'))
                        logger.info("Rules parsed with quote replacement")
                    except Exception:
                        logger.error(f"Invalid rules payload: {raw_str[:100]}...")
                        raise HTTPException(status_code=400, detail=f"invalid rules JSON: {exc_json}")

    # Read file bytes
    payload = []
    for f in files:
        content = await f.read()
        payload.append({"filename": f.filename, "content": content})

    # Create a task id and schedule with local worker
    task_id = str(uuid.uuid4())
    results_dir = ensure_results_dir(task_id)
    logger.info(f"Task {task_id} created, results dir: {results_dir}")

    # Submit task to local worker with the same task_id
    try:
        from local_worker import submit_task
        worker_task_id = submit_task(
            "process_pdfs",
            files=payload,
            rules=parsed_rules,
            username=username,
            results_dir=results_dir,
            task_id=task_id  # Pass the task_id to use the same ID
        )
        logger.info(f"Task {task_id} submitted to local worker")
    except Exception as e:
        logger.error(f"Failed to submit task to local worker: {e}")
        return JSONResponse(content={"task_id": task_id, "error": "Failed to submit task"})

    return JSONResponse(content={"task_id": task_id})

    return JSONResponse(content={"task_id": task_id})


# -- Task status endpoint --
@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    logger.info(f"Task status request for {task_id}")
    # Validate task_id format (UUID)
    try:
        uuid.UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid task_id format: {task_id}")
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    # Check local worker for task status
    try:
        from local_worker import get_task_status as get_worker_status
        task_info = get_worker_status(task_id)
        if task_info:
            state = task_info.get("status")
            # Normalize info so frontend can access processed/total/current_file at top-level
            info = {}
            result = task_info.get("result")
            if isinstance(result, dict):
                # merge common progress keys to top-level info
                info.update(result)
            else:
                info["result"] = result
            # include error if present
            info["error"] = task_info.get("error")
            return JSONResponse(content={"task_id": task_id, "state": state, "info": info})
        else:
            return JSONResponse(content={"task_id": task_id, "state": "UNKNOWN", "info": None})
    except Exception as e:
        logger.error(f"Failed to get task status from worker: {e}")
        return JSONResponse(content={"task_id": task_id, "state": "UNKNOWN", "info": None})


# --- AI generation endpoint (wraps ai_stub.generate_ruleset_from_prompt) ---
@app.post("/api/v1/ai/generate")
async def ai_generate(payload: Dict[str, Any]):
    """Generate a structured ruleset from a natural language prompt using OpenAI.

    Expects JSON payload: { "prompt": "..." }
    The OpenAI API key must be set in the environment variable OPENAI_API_KEY or in a .env file.
    """
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    if not prompt or not isinstance(prompt, str):
        raise HTTPException(status_code=400, detail="Missing 'prompt' in request body")

    # Ensure ai_stub is available
    if generate_ruleset_from_prompt is None:
        raise HTTPException(status_code=500, detail="AI generation is not available (ai_stub import failed)")

    # Read API key from environment
    # Note: For production SaaS, this should be YOUR OpenAI API key (centralized)
    # Rule generation costs ~$0.0003 per request, negligible compared to subscription revenue
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not configured in environment")
        raise HTTPException(
            status_code=503, 
            detail="AI rule generation is temporarily unavailable. Please use Simple Checks or contact support."
        )

    # Create OpenAI client lazily so we don't require it at import time
    try:
        from openai import OpenAI
    except Exception as e:
        logger.error(f"OpenAI SDK not installed: {e}")
        raise HTTPException(status_code=500, detail="OpenAI SDK not installed on server")

    try:
        client = OpenAI(api_key=api_key)
        ruleset = generate_ruleset_from_prompt(prompt, client)
        return JSONResponse(content={"ok": True, "ruleset": ruleset})
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        return JSONResponse(content={"ok": False, "error": str(e)})


# Compatibility endpoint for frontend: accepts { text: '...' } and returns the ruleset JSON directly
@app.post("/api/v1/ai/convert")
async def ai_convert(payload: Dict[str, Any]):
    text = payload.get("text") if isinstance(payload, dict) else None
    if not text or not isinstance(text, str):
        raise HTTPException(status_code=400, detail="Missing 'text' in request body")

    if generate_ruleset_from_prompt is None:
        raise HTTPException(status_code=500, detail="AI generation is not available (ai_stub import failed)")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not configured in environment")
        raise HTTPException(
            status_code=503, 
            detail="AI rule generation is temporarily unavailable. Please use Simple Checks or contact support."
        )

    try:
        from openai import OpenAI
    except Exception as e:
        logger.error(f"OpenAI SDK not installed: {e}")
        raise HTTPException(status_code=500, detail="OpenAI SDK not installed on server")

    try:
        client = OpenAI(api_key=api_key)
        ruleset = generate_ruleset_from_prompt(text, client)
        # Return the ruleset directly (frontend expects raw ruleset)
        return JSONResponse(content=ruleset)
    except Exception as e:
        logger.error(f"AI convert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -- Download endpoints remain the same and rely on results folder layout --
@app.get("/api/v1/tasks/{task_id}/result.csv")
async def download_task_csv(task_id: str):
    logger.info(f"CSV download request for {task_id}")
    try:
        uuid.UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid task_id for CSV: {task_id}")
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))
    # Security: ensure results_dir is within RESULTS_ROOT
    if not results_dir.startswith(RESULTS_ROOT):
        logger.error(f"Path traversal attempt: {results_dir}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    csv_files = glob.glob(os.path.join(results_dir, 'valido_results_*.csv'))
    if not csv_files:
        csv_path = os.path.join(results_dir, 'results.csv')
        if not os.path.exists(csv_path):
            logger.warning(f"CSV not found for {task_id}")
            raise HTTPException(status_code=404, detail="CSV result not found")
        return FileResponse(csv_path, media_type='text/csv', filename=f"{task_id}-results.csv")
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
    logger.info(f"ZIP download request for {task_id}")
    try:
        uuid.UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid task_id for ZIP: {task_id}")
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    results_dir = os.path.abspath(os.path.join(os.getcwd(), 'results', task_id))
    if not results_dir.startswith(RESULTS_ROOT):
        logger.error(f"Path traversal attempt: {results_dir}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    zip_files = glob.glob(os.path.join(results_dir, 'valido_results_*.zip'))
    if not zip_files:
        zip_path = os.path.join(results_dir, 'results.zip')
        if not os.path.exists(zip_path):
            logger.warning(f"ZIP not found for {task_id}")
            raise HTTPException(status_code=404, detail="ZIP file not found")
        return FileResponse(zip_path, media_type='application/zip', filename=f"valido-results-{task_id}.zip")
    zip_path = max(zip_files, key=os.path.getctime)
    filename = os.path.basename(zip_path)
    return FileResponse(zip_path, media_type='application/zip', filename=filename)


# --- Route includes (unchanged) ---
try:
    from app.routes.ruleset_routes import router as ruleset_router
    app.include_router(ruleset_router)
    logger.info("Ruleset routes included successfully")
except Exception as e:
    logger.warning(f"Failed to include ruleset routes: {e}")

try:
    from app.routes.user_routes import router as user_router
    app.include_router(user_router)
    logger.info("User routes included successfully")
except Exception as e:
    logger.warning(f"Failed to include user routes: {e}")

try:
    from app.routes.watch_folder_routes import router as watch_folder_router
    app.include_router(watch_folder_router)
    logger.info("Watch folder routes included successfully")
except Exception as e:
    logger.warning(f"Failed to include watch folder routes: {e}")

# Agent download routes are no longer necessary in single-exe setup,
# but keep router include for compatibility if present.
try:
    from app.routes.agent_routes import router as agent_router
    app.include_router(agent_router)
    logger.info("Agent download routes included successfully")
except Exception as e:
    logger.warning(f"Failed to include agent routes: {e}")

# AI routes are defined directly in main.py (lines 586-657), no separate router needed
logger.info("AI routes configured successfully")

# Serve frontend static files (same logic)
try:
    # When running as PyInstaller executable, frontend is bundled
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        frontend_dir = os.path.join(sys._MEIPASS, 'frontend')
    else:
        # Running as script
        candidates = [
            os.path.abspath(os.path.join(os.getcwd(), '..', 'frontend')),
            os.path.abspath(os.path.join(os.getcwd(), 'frontend')),
            '/app/frontend',
            os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'frontend')),
        ]
        frontend_dir = None
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                frontend_dir = candidate
                break

    if frontend_dir and os.path.exists(frontend_dir):
        app.mount('/', StaticFiles(directory=frontend_dir, html=True), name='frontend')
        logger.info(f"Frontend served from {frontend_dir}")
    else:
        logger.warning("Frontend directory not found")
except Exception as e:
    logger.warning(f"Failed to mount frontend: {e}")

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    import sys
    
    # Redirect stdout/stderr for console=False mode
    if sys.stdout is None:
        sys.stdout = open('valido.log', 'w')
    if sys.stderr is None:
        sys.stderr = sys.stdout
    
    logger.info("Starting Valido server on http://0.0.0.0:8000")
    
    # Open browser after a short delay (let server start first)
    def open_browser():
        import time
        time.sleep(2)  # Wait for server to start
        webbrowser.open("http://localhost:8000")
    
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Use minimal logging config for GUI mode
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
