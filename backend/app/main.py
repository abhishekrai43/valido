# main.py
"""
Valido - PDF Validation Service
Main application entry point. Registers routes and configures FastAPI app.
"""

import sys
import io

# Fix for PyInstaller executable without console: redirect stdout/stderr to avoid AttributeError
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from app.utils.logger import get_logger
from app.license import get_license_banner

# Optional: load .env for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logger = get_logger("ValidoMain")

# Create FastAPI app
app = FastAPI(
    title="Valido PDF Validator",
    description="Professional PDF validation and data extraction service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Results directory configuration
RESULTS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "results"))
os.makedirs(RESULTS_ROOT, exist_ok=True)


# --- Startup Event ---
@app.on_event("startup")
async def _on_startup():
    """Initialize database and display startup banner."""
    try:
        logger.info("Starting Valido PDF Validator...")
        logger.info(f"Results directory: {RESULTS_ROOT}")
        
        # Initialize database
        from app import models  # noqa: F401
        from app.db import create_db_and_tables, SQLITE_URL
        logger.info(f"Database URL: {SQLITE_URL}")
        create_db_and_tables()
        logger.info("Database initialized successfully")
        
        # Initialize and start job scheduler
        from app.scheduler import get_scheduler
        scheduler = get_scheduler()
        scheduler.reload_schedules()
        logger.info("Job scheduler initialized and schedules loaded")
        
        # Display license banner (if any)
        banner = get_license_banner()
        if banner:
            print("\n" + banner + "\n")
        logger.info("Startup complete")
        
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)


@app.on_event("shutdown")
async def _on_shutdown():
    """Cleanup on application shutdown."""
    try:
        from app.scheduler import shutdown_scheduler
        shutdown_scheduler()
        logger.info("Job scheduler stopped")
    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)


# --- Debug: List all routes ---
@app.get("/debug/routes")
def list_routes():
    """Debug endpoint to list all registered routes."""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {"routes": routes}


# --- Register Route Modules ---

# Validation routes (upload, submit, task status, downloads)
from app.routes.validation_routes import router as validation_router, set_results_root as set_validation_results
set_validation_results(RESULTS_ROOT)
app.include_router(validation_router)

# Diagnostics routes (health, system info, diagnostics export)
from app.routes.diagnostics_routes import router as diagnostics_router, set_results_root as set_diagnostics_results
set_diagnostics_results(RESULTS_ROOT)
app.include_router(diagnostics_router)

# User routes
from app.routes.user_routes import router as user_router
app.include_router(user_router)

# Ruleset routes
try:
    from app.routes.ruleset_routes import router as ruleset_router
    app.include_router(ruleset_router)
    logger.info("✓ Ruleset routes registered")
except Exception as e:
    logger.error(f"✗ Failed to register ruleset routes: {e}", exc_info=True)

# Watch folder routes
from app.routes.watch_folder_routes import router as watch_folder_router
app.include_router(watch_folder_router)

# Agent routes
from app.routes.agent_routes import router as agent_router
app.include_router(agent_router)

# Rules routes (if exists)
try:
    from app.routes.rules import router as rules_router
    app.include_router(rules_router)
except ImportError:
    pass


# --- Static Files (Frontend) ---
# Handle both development and PyInstaller exe modes
if getattr(sys, 'frozen', False):
    # Running as compiled exe - frontend is in _MEIPASS temp directory
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    frontend_dir = os.path.join(base_path, "frontend")
    logger.info(f"Running as exe. Base path: {base_path}")
else:
    # Running as script - frontend is relative to this file
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
    logger.info(f"Running as script. Frontend dir: {frontend_dir}")

if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    logger.info(f"✓ Serving frontend from: {frontend_dir}")
else:
    logger.error(f"✗ Frontend directory not found: {frontend_dir}")
    logger.error(f"  Checked path exists: {os.path.exists(frontend_dir)}")
    logger.error(f"  sys.frozen: {getattr(sys, 'frozen', False)}")
    logger.error(f"  sys._MEIPASS: {getattr(sys, '_MEIPASS', 'NOT FOUND')}")
    logger.error(f"  sys.executable: {sys.executable}")
    logger.error(f"  __file__: {__file__}")


# --- Main Entry Point ---
# For PyInstaller, __name__ is not "__main__", so check frozen or __main__
if __name__ == "__main__" or getattr(sys, 'frozen', False):
    import uvicorn
    import socket
    import webbrowser
    import threading
    import time
    
    logger.info("=== Starting Valido application ===")
    logger.info(f"__name__ = {__name__}")
    logger.info(f"sys.frozen = {getattr(sys, 'frozen', False)}")
    
    # Get network info
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "localhost"
    
    local_ip = get_local_ip()
    port = 8000
    
    print("\n" + "="*60)
    print("🚀 Valido PDF Validator Starting...")
    print("="*60)
    print(f"📍 Local:   http://localhost:{port}")
    print(f"🌐 Network: http://{local_ip}:{port}")
    print(f"📁 Results: {RESULTS_ROOT}")
    print("="*60 + "\n")
    
    # Auto-open browser after server starts (only when running as exe)
    def open_browser():
        try:
            time.sleep(3)  # Wait for server to start
            logger.info(f"Opening browser to http://localhost:{port}")
            webbrowser.open(f"http://localhost:{port}")
            logger.info("Browser open command sent")
        except Exception as e:
            logger.error(f"Browser open failed: {e}")
    
    logger.info(f"Checking frozen status: {getattr(sys, 'frozen', False)}")
    
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - auto-open browser
        logger.info("Detected exe mode - will auto-open browser in 3 seconds")
        try:
            threading.Thread(target=open_browser, daemon=True).start()
            logger.info("Browser thread started")
        except Exception as e:
            logger.error(f"Failed to start browser thread: {e}")
    else:
        logger.info("Running as script - not auto-opening browser")
    
    try:
        logger.info(f"About to start uvicorn on port {port}")
        uvicorn.run(
            app,  # Pass the app object directly, not the string (for PyInstaller)
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="info"
        )
        logger.info("Uvicorn started successfully")
    except Exception as e:
        logger.error(f"Failed to start uvicorn: {e}")
        import traceback
        logger.error(traceback.format_exc())
