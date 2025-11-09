# app/routes/diagnostics_routes.py
"""
Diagnostics and Health Check Routes
Handles system diagnostics, health checks, and diagnostic exports.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse
import os
import time
import platform
import zipfile
import json
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger("DiagnosticsRoutes")

router = APIRouter(prefix="/api/v1", tags=["diagnostics"])

# Import RESULTS_ROOT from main (will be set during router registration)
RESULTS_ROOT = None

def set_results_root(path: str):
    """Set the results root path."""
    global RESULTS_ROOT
    RESULTS_ROOT = path


@router.get("/healthz")
async def healthz():
    """Basic health check endpoint."""
    return {"status": "ok"}


@router.get("/diagnostics")
async def diagnostics():
    """Get comprehensive system diagnostics information."""
    logger.info("Diagnostics request")
    
    try:
        import psutil  # type: ignore
    except ImportError:
        psutil = None  # type: ignore
    
    from app.db import get_session
    from app.models import User, Ruleset, WatchFolder

    try:
        # System info
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count() if psutil else "N/A",  # type: ignore
            "memory_total": psutil.virtual_memory().total if psutil else "N/A",  # type: ignore
            "memory_available": psutil.virtual_memory().available if psutil else "N/A",  # type: ignore
            "disk_free": (psutil.disk_usage('/').free if os.name == 'posix' else psutil.disk_usage('C:\\').free) if psutil else "N/A",  # type: ignore
        }

        # Database stats
        with get_session() as session:
            db_stats = {
                "users_count": session.query(User).count(),
                "rulesets_count": session.query(Ruleset).count(),
                "watch_folders_count": session.query(WatchFolder).count(),
            }

        # Application stats
        results_dir = RESULTS_ROOT
        app_stats = {
            "results_dir_exists": os.path.exists(results_dir) if results_dir else False,
            "results_files_count": len(os.listdir(results_dir)) if results_dir and os.path.exists(results_dir) else 0,
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


@router.get("/diagnostics/export")
async def export_diagnostics():
    """
    Export comprehensive diagnostics package for support.
    Returns a ZIP file containing:
    - System information
    - Database statistics
    - Recent logs (if available)
    - Configuration files
    """
    logger.info("Diagnostic export request")
    
    try:
        # Create temporary diagnostics package
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        diag_filename = f'valido_diagnostics_{timestamp}.zip'
        
        if not RESULTS_ROOT:
            return JSONResponse(
                status_code=500,
                content={"error": "Results directory not configured"}
            )
        
        diag_path = os.path.join(RESULTS_ROOT, diag_filename)
        
        with zipfile.ZipFile(diag_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add system info
            diag_data = await diagnostics()
            system_json = json.dumps(diag_data, indent=2)
            zipf.writestr('system_info.json', system_json)
            
            # Add database schema info
            try:
                from app.db import get_session
                from app.models import User, Ruleset, WatchFolder
                
                with get_session() as session:
                    # Get sample data (sanitized)
                    users = session.query(User).all()
                    rulesets = session.query(Ruleset).all()
                    watch_folders = session.query(WatchFolder).all()
                    
                    db_info = {
                        "users": [{"username": u.username, "total_processed": u.total_processed} for u in users],
                        "rulesets": [{"id": r.id, "name": r.name} for r in rulesets],
                        "watch_folders": [{"id": w.id, "path": w.folder_path, "active": w.active} for w in watch_folders],
                    }
                    
                    zipf.writestr('database_info.json', json.dumps(db_info, indent=2))
            except Exception as e:
                zipf.writestr('database_error.txt', f"Error reading database: {str(e)}")
            
            # Add recent logs if available
            log_dir = os.path.join(os.path.dirname(RESULTS_ROOT), 'backend', 'logs')
            if os.path.exists(log_dir):
                for log_file in os.listdir(log_dir):
                    if log_file.endswith('.log'):
                        log_path = os.path.join(log_dir, log_file)
                        if os.path.exists(log_path):
                            # Only add recent logs (last 1000 lines)
                            try:
                                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    lines = f.readlines()
                                    recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                                    zipf.writestr(f'logs/{log_file}', ''.join(recent_lines))
                            except:
                                pass
            
            # Add Python environment info
            import sys
            env_info = {
                "python_executable": sys.executable,
                "python_version": sys.version,
                "python_path": sys.path,
                "installed_packages": []
            }
            
            try:
                import pkg_resources
                env_info["installed_packages"] = [
                    f"{pkg.key}=={pkg.version}" 
                    for pkg in pkg_resources.working_set
                ]
            except:
                pass
            
            zipf.writestr('environment.json', json.dumps(env_info, indent=2))
        
        return FileResponse(
            diag_path,
            media_type='application/zip',
            filename=diag_filename,
            headers={"Content-Disposition": f"attachment; filename={diag_filename}"}
        )
        
    except Exception as e:
        logger.error(f"Diagnostic export error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to create diagnostic package: {str(e)}"}
        )


@router.get("/network-info")
def get_network_info():
    """Get network access information for the application."""
    def get_local_ip():
        """Get the local IP address for network access."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "192.168.1.100"  # Fallback
    
    local_ip = get_local_ip()
    return {
        "localhost": "http://localhost:8000",
        "network": f"http://{local_ip}:8000"
    }


@router.get("/results-path")
def get_results_path():
    """Get the local path where results are stored."""
    return {
        "results_directory": RESULTS_ROOT,
        "exists": os.path.exists(RESULTS_ROOT) if RESULTS_ROOT else False
    }
