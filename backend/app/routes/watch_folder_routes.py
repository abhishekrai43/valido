from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime
import os
import sys
from pathlib import Path

# Add backend directory to path for local_worker import
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import local_worker

from app.db import engine
from app.models import WatchFolder, Ruleset, JobRun
from app.utils.logger import get_logger

logger = get_logger("WatchFolderRoutes")

router = APIRouter(prefix="/api/v1/watch-folders", tags=["watch-folders"])


def check_schedule_conflicts(session: Session, schedule_times: str, exclude_id: int = None) -> dict:
    """
    Check if schedule times conflict with existing watch folders.
    Returns {"has_conflict": bool, "conflicts": [{"id": int, "name": str, "times": [str]}]}
    """
    if not schedule_times or not schedule_times.strip():
        return {"has_conflict": False, "conflicts": []}
    
    # Parse new schedule times
    new_times = set(t.strip() for t in schedule_times.split(',') if t.strip())
    
    # Get all other enabled watch folders with schedules
    statement = select(WatchFolder).where(WatchFolder.enabled == True)
    if exclude_id:
        statement = statement.where(WatchFolder.id != exclude_id)
    
    existing_folders = session.exec(statement).all()
    
    conflicts = []
    for folder in existing_folders:
        if not folder.schedule_times:
            continue
        
        existing_times = set(t.strip() for t in folder.schedule_times.split(',') if t.strip())
        overlapping = new_times & existing_times  # Set intersection
        
        if overlapping:
            conflicts.append({
                "id": folder.id,
                "name": folder.name,
                "times": sorted(list(overlapping))
            })
    
    return {
        "has_conflict": len(conflicts) > 0,
        "conflicts": conflicts
    }


@router.get("/", response_model=List[WatchFolder])
def list_watch_folders():
    """List all watch folder configurations."""
    logger.info("Listing watch folders")
    with Session(engine) as session:
        statement = select(WatchFolder)
        watch_folders = session.exec(statement).all()
        logger.info(f"Found {len(watch_folders)} watch folders")
        return watch_folders


@router.get("/active-jobs")
def get_active_jobs():
    """Get currently running watch folder jobs across all folders."""
    logger.info("Getting active jobs")
    with Session(engine) as session:
        # Find all job runs with status='running'
        statement = (
            select(JobRun)
            .where(JobRun.status == "running")
            .order_by(JobRun.started_at.desc())
        )
        active_runs = session.exec(statement).all()
        
        # Format response with watch folder info
        active_jobs = []
        for run in active_runs:
            watch_folder = session.get(WatchFolder, run.watch_folder_id)
            if watch_folder:
                active_jobs.append({
                    "watch_folder_id": run.watch_folder_id,
                    "watch_folder_name": watch_folder.name,
                    "job_run_id": run.id,
                    "files_found": run.files_found,
                    "files_processed": run.files_processed,
                    "started_at": run.started_at.isoformat() if run.started_at else None
                })
        
        logger.info(f"Found {len(active_jobs)} active jobs")
        return {"active_jobs": active_jobs}


@router.get("/{watch_folder_id}", response_model=WatchFolder)
def get_watch_folder(watch_folder_id: int):
    """Get a specific watch folder configuration."""
    logger.info(f"Getting watch folder: {watch_folder_id}")
    if watch_folder_id <= 0:
        logger.warning(f"Invalid watch folder ID: {watch_folder_id}")
        raise HTTPException(status_code=400, detail="Invalid watch folder ID")
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            logger.warning(f"Watch folder not found: {watch_folder_id}")
            raise HTTPException(status_code=404, detail="Watch folder not found")
        return watch_folder


@router.post("/", response_model=WatchFolder)
def create_watch_folder(watch_folder: WatchFolder):
    """Create a new watch folder configuration."""
    logger.info(f"Creating watch folder: {watch_folder.name}")
    # Validate paths (skip validation for cloud storage paths)
    import os
    is_cloud_input = watch_folder.input_path.startswith('cloud://')
    
    if not is_cloud_input and not os.path.isabs(watch_folder.input_path):
        logger.warning(f"Input path not absolute: {watch_folder.input_path}")
        raise HTTPException(status_code=400, detail="Input path must be absolute")
    if not os.path.isabs(watch_folder.output_path):
        logger.warning(f"Output path not absolute: {watch_folder.output_path}")
        raise HTTPException(status_code=400, detail="Output path must be absolute")
    with Session(engine) as session:
        # Verify ruleset exists
        ruleset = session.get(Ruleset, watch_folder.ruleset_id)
        if not ruleset:
            logger.warning(f"Ruleset not found: {watch_folder.ruleset_id}")
            raise HTTPException(status_code=404, detail="Ruleset not found")
        
        # Check for schedule conflicts if enabled and has schedule
        if watch_folder.enabled and watch_folder.schedule_times:
            conflict_check = check_schedule_conflicts(session, watch_folder.schedule_times)
            if conflict_check["has_conflict"]:
                conflicts_msg = "; ".join([
                    f"{c['name']} at {', '.join(c['times'])}" 
                    for c in conflict_check["conflicts"]
                ])
                logger.warning(f"Schedule conflict detected: {conflicts_msg}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Schedule conflict detected with: {conflicts_msg}"
                )
        
        session.add(watch_folder)
        session.commit()
        session.refresh(watch_folder)
        logger.info(f"Watch folder created: {watch_folder.id}")
        
        # Schedule the job if enabled
        if watch_folder.enabled and watch_folder.schedule_times:
            try:
                from app.scheduler import get_scheduler
                scheduler = get_scheduler()
                scheduler.schedule_job(watch_folder.id, watch_folder.schedule_times)
                logger.info(f"Scheduled watch folder {watch_folder.id}")
            except Exception as e:
                logger.error(f"Failed to schedule watch folder {watch_folder.id}: {e}")
        
        return watch_folder


@router.put("/{watch_folder_id}", response_model=WatchFolder)
def update_watch_folder(watch_folder_id: int, updated: WatchFolder):
    """Update an existing watch folder configuration."""
    logger.info(f"Updating watch folder: {watch_folder_id}")
    if watch_folder_id <= 0:
        logger.warning(f"Invalid watch folder ID: {watch_folder_id}")
        raise HTTPException(status_code=400, detail="Invalid watch folder ID")
    # Validate paths (skip validation for cloud storage paths)
    import os
    is_cloud_input = updated.input_path.startswith('cloud://')
    
    if not is_cloud_input and not os.path.isabs(updated.input_path):
        logger.warning(f"Input path not absolute: {updated.input_path}")
        raise HTTPException(status_code=400, detail="Input path must be absolute")
    if not os.path.isabs(updated.output_path):
        logger.warning(f"Output path not absolute: {updated.output_path}")
        raise HTTPException(status_code=400, detail="Output path must be absolute")
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            logger.warning(f"Watch folder not found for update: {watch_folder_id}")
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        # Check for schedule conflicts if enabled and has schedule (exclude current watch folder)
        if updated.enabled and updated.schedule_times:
            conflict_check = check_schedule_conflicts(session, updated.schedule_times, exclude_id=watch_folder_id)
            if conflict_check["has_conflict"]:
                conflicts_msg = "; ".join([
                    f"{c['name']} at {', '.join(c['times'])}" 
                    for c in conflict_check["conflicts"]
                ])
                logger.warning(f"Schedule conflict detected: {conflicts_msg}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Schedule conflict detected with: {conflicts_msg}"
                )
        
        # Update fields
        watch_folder.name = updated.name
        watch_folder.input_path = updated.input_path
        watch_folder.output_path = updated.output_path
        watch_folder.ruleset_id = updated.ruleset_id
        watch_folder.schedule_times = updated.schedule_times
        watch_folder.move_processed = updated.move_processed
        watch_folder.processed_path = updated.processed_path
        watch_folder.delete_after = updated.delete_after
        watch_folder.enabled = updated.enabled
        
        session.add(watch_folder)
        session.commit()
        session.refresh(watch_folder)
        logger.info(f"Watch folder updated: {watch_folder_id}")
        
        # Update schedule
        try:
            from app.scheduler import get_scheduler
            scheduler = get_scheduler()
            if watch_folder.enabled and watch_folder.schedule_times:
                scheduler.schedule_job(watch_folder.id, watch_folder.schedule_times)
                logger.info(f"Updated schedule for watch folder {watch_folder.id}")
            else:
                scheduler.remove_job(watch_folder.id)
                logger.info(f"Removed schedule for watch folder {watch_folder.id}")
        except Exception as e:
            logger.error(f"Failed to update schedule for watch folder {watch_folder.id}: {e}")
        
        return watch_folder


@router.delete("/{watch_folder_id}")
def delete_watch_folder(watch_folder_id: int):
    """Delete a watch folder configuration."""
    logger.info(f"Deleting watch folder: {watch_folder_id}")
    if watch_folder_id <= 0:
        logger.warning(f"Invalid watch folder ID: {watch_folder_id}")
        raise HTTPException(status_code=400, detail="Invalid watch folder ID")
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            logger.warning(f"Watch folder not found for delete: {watch_folder_id}")
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        session.delete(watch_folder)
        session.commit()
        logger.info(f"Watch folder deleted: {watch_folder_id}")
        
        # Remove from scheduler
        try:
            from app.scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.remove_job(watch_folder_id)
            logger.info(f"Removed schedule for deleted watch folder {watch_folder_id}")
        except Exception as e:
            logger.error(f"Failed to remove schedule: {e}")
        
        return {"ok": True}


@router.post("/{watch_folder_id}/toggle")
def toggle_watch_folder(watch_folder_id: int):
    """Enable or disable a watch folder."""
    logger.info(f"Toggling watch folder: {watch_folder_id}")
    if watch_folder_id <= 0:
        logger.warning(f"Invalid watch folder ID: {watch_folder_id}")
        raise HTTPException(status_code=400, detail="Invalid watch folder ID")
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            logger.warning(f"Watch folder not found for toggle: {watch_folder_id}")
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        watch_folder.enabled = not watch_folder.enabled
        session.add(watch_folder)
        session.commit()
        session.refresh(watch_folder)
        logger.info(f"Watch folder {watch_folder_id} enabled: {watch_folder.enabled}")
        
        # Update schedule based on enabled status
        try:
            from app.scheduler import get_scheduler
            scheduler = get_scheduler()
            if watch_folder.enabled and watch_folder.schedule_times:
                scheduler.schedule_job(watch_folder.id, watch_folder.schedule_times)
                logger.info(f"Enabled schedule for watch folder {watch_folder.id}")
            else:
                scheduler.remove_job(watch_folder.id)
                logger.info(f"Disabled schedule for watch folder {watch_folder.id}")
        except Exception as e:
            logger.error(f"Failed to update schedule: {e}")
        
        return watch_folder


@router.post("/{watch_folder_id}/update-stats")
def update_stats(watch_folder_id: int, files_processed: int):
    """Update statistics after processing (called by agent)."""
    logger.info(f"Updating stats for watch folder {watch_folder_id}: +{files_processed} files")
    if watch_folder_id <= 0:
        logger.warning(f"Invalid watch folder ID: {watch_folder_id}")
        raise HTTPException(status_code=400, detail="Invalid watch folder ID")
    if files_processed < 0:
        logger.warning(f"Negative files_processed: {files_processed}")
        raise HTTPException(status_code=400, detail="Files processed cannot be negative")
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            logger.warning(f"Watch folder not found for stats update: {watch_folder_id}")
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        watch_folder.last_run = datetime.utcnow()
        watch_folder.files_processed_total += files_processed
        
        session.add(watch_folder)
        session.commit()
        session.refresh(watch_folder)
        logger.info(f"Stats updated for watch folder {watch_folder_id}")
        return watch_folder


@router.post("/{watch_folder_id}/run")
def run_watch_folder_now(watch_folder_id: int):
    """Trigger immediate execution of a watch folder job."""
    logger.info(f"Running watch folder now: {watch_folder_id}")
    
    if watch_folder_id <= 0:
        logger.warning(f"Invalid watch folder ID: {watch_folder_id}")
        raise HTTPException(status_code=400, detail="Invalid watch folder ID")
    
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            logger.warning(f"Watch folder not found: {watch_folder_id}")
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        # Get ruleset
        ruleset = session.get(Ruleset, watch_folder.ruleset_id)
        if not ruleset:
            logger.warning(f"Ruleset not found: {watch_folder.ruleset_id}")
            raise HTTPException(status_code=404, detail="Ruleset not found")
        
        # Detect if this is cloud storage or local folder
        is_cloud_storage = watch_folder.input_path.startswith('cloud://')
        cloud_temp_dir = None
        
        if is_cloud_storage:
            # Handle cloud storage input
            logger.info(f"Detected cloud storage input: {watch_folder.input_path}")
            
            # Get cloud config from watch folder
            cloud_config = watch_folder.cloud_config
            if not cloud_config:
                logger.error(f"Cloud storage path but no cloud_config found")
                raise HTTPException(status_code=400, detail="Cloud storage configuration missing")
            
            # Use CloudOrchestrator to download files
            from app.services.cloud.cloud_orchestrator import CloudOrchestrator
            
            provider = cloud_config.get('provider')
            config = cloud_config.get('config')
            
            logger.info(f"Downloading PDFs from {provider}...")
            download_result = CloudOrchestrator.download_pdfs_to_temp(provider, config)
            
            if not download_result['success']:
                logger.error(f"Failed to download from cloud: {download_result.get('message')}")
                raise HTTPException(status_code=500, detail=f"Cloud download failed: {download_result.get('message')}")
            
            cloud_temp_dir = download_result['temp_dir']
            pdf_files = [os.path.basename(f) for f in download_result['files']]
            
            logger.info(f"Downloaded {len(pdf_files)} PDF files from {provider} to {cloud_temp_dir}")
            
        else:
            # Handle local folder input (EXISTING LOGIC - NO CHANGES)
            # Check input folder exists and has files
            if not os.path.exists(watch_folder.input_path):
                logger.warning(f"Input folder does not exist: {watch_folder.input_path}")
                raise HTTPException(status_code=400, detail="Input folder does not exist")
            
            # Get list of PDF files
            pdf_files = [f for f in os.listdir(watch_folder.input_path) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            logger.info(f"No PDF files found")
            # Clean up cloud temp dir if used
            if cloud_temp_dir:
                from app.services.cloud.cloud_orchestrator import CloudOrchestrator
                CloudOrchestrator.cleanup_temp_directory(cloud_temp_dir)
            raise HTTPException(status_code=400, detail="No PDF files found in input source")
        
        # Create JobRun record to track execution
        import socket
        job_run = JobRun(
            watch_folder_id=watch_folder_id,
            status="running",
            files_found=len(pdf_files),
            files_processed=0,
            files_succeeded=0,
            files_failed=0,
            pc_name=socket.gethostname(),
            output_path=watch_folder.output_path
        )
        session.add(job_run)
        session.commit()
        session.refresh(job_run)
        logger.info(f"Created job run {job_run.id} for watch folder {watch_folder_id}")
        
        # 🚀 BROADCAST IMMEDIATELY - User sees badge within milliseconds
        try:
            from app.routes.websocket_routes import broadcast_job_status_sync
            broadcast_job_status_sync(
                watch_folder_id=watch_folder_id,
                status="started",
                data={
                    "job_run_id": job_run.id,
                    "files_count": len(pdf_files),
                    "files_found": len(pdf_files),
                    "files_processed": 0
                }
            )
            logger.info(f"✓ Broadcasted job start for watch folder {watch_folder_id}")
        except Exception as e:
            logger.warning(f"Failed to broadcast job start via WebSocket: {e}")
        
        # Read PDF files into memory for processing
        files_list = []
        
        # Determine the source folder (cloud temp dir or local folder)
        source_folder = cloud_temp_dir if (is_cloud_storage and cloud_temp_dir) else watch_folder.input_path
        
        for filename in pdf_files:
            filepath = os.path.join(source_folder, filename)
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                files_list.append({
                    'filename': filename,
                    'content': content
                })
            except Exception as e:
                logger.error(f"Failed to read {filepath}: {e}")
                # Update job run with error
                job_run.files_failed += 1
                session.add(job_run)
                session.commit()
                continue
        
        if not files_list:
            # Mark job as failed
            job_run.status = "failed"
            job_run.completed_at = datetime.utcnow()
            job_run.error_message = "Failed to read any PDF files"
            session.add(job_run)
            session.commit()
            
            # Clean up cloud temp dir if used
            if cloud_temp_dir:
                from app.services.cloud.cloud_orchestrator import CloudOrchestrator
                CloudOrchestrator.cleanup_temp_directory(cloud_temp_dir)
            
            logger.error(f"Failed to read any PDF files")
            raise HTTPException(status_code=500, detail="Failed to read PDF files")
        
        job_run.files_processed = len(files_list)
        session.add(job_run)
        session.commit()
        
        # Create a unique output folder for this task (use task ID as folder name)
        import uuid
        folder_id = str(uuid.uuid4())
        task_output_folder = os.path.join(watch_folder.output_path, folder_id)
        os.makedirs(task_output_folder, exist_ok=True)
        
        # Prepare job metadata for PDF report
        job_metadata = {
            'name': watch_folder.name,
            'input_path': watch_folder.input_path,
            'output_path': watch_folder.output_path,
            'execution_type': 'Manual Trigger',
            'schedule_times': watch_folder.schedule_times or 'Not scheduled',
            'ruleset_name': ruleset.name if ruleset else 'Unknown',
            'job_run_id': job_run.id,  # Pass job run ID so worker can update it
            'cloud_temp_dir': cloud_temp_dir  # For cleanup after processing
        }
        
        # Submit task to local worker
        task_id = local_worker.submit_task(
            task_type="process_pdfs",
            files=files_list,
            rules=ruleset.rules,
            results_dir=task_output_folder,
            job_metadata=job_metadata
        )
        
        logger.info(f"Submitted watch folder {watch_folder_id} as task {task_id} with {len(files_list)} files")
        
        # Note: cloud_temp_dir will be cleaned up by worker after processing completes
        
        # Update watch folder last_run
        watch_folder.last_run = datetime.utcnow()
        session.add(watch_folder)
        session.commit()
        
        return {
            "task_id": task_id,
            "watch_folder_id": watch_folder_id,
            "job_run_id": job_run.id,
            "files_count": len(files_list),
            "message": f"Processing {len(files_list)} PDF files"
        }


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    """Get status of a running task."""
    logger.info(f"Getting task status: {task_id}")
    
    task_status = local_worker.get_task_status(task_id)
    
    if not task_status:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Clean up the result to remove binary data that can't be JSON serialized
    clean_status = {
        "id": task_status.get("id"),
        "type": task_status.get("type"),
        "status": task_status.get("status"),
        "error": task_status.get("error"),
        "created_at": task_status.get("created_at"),
        "updated_at": task_status.get("updated_at"),
    }
    
    # Handle result - extract only serializable progress info
    result = task_status.get("result", {})
    if isinstance(result, dict):
        # For progress tracking
        if "processed" in result or "total" in result:
            clean_status["result"] = {
                "processed": result.get("processed", 0),
                "total": result.get("total", 0),
                "current_file": result.get("current_file", ""),
                "percent": result.get("percent", 0)
            }
        # For completed tasks, just include summary
        elif "reports" in result:
            clean_status["result"] = {
                "total": len(result.get("reports", [])),
                "task_id": result.get("task_id"),
                "output_folder": result.get("output_folder")
            }
        else:
            clean_status["result"] = {}
    else:
        clean_status["result"] = {}
    
    return clean_status


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    """Cancel a running task."""
    logger.info(f"Canceling task: {task_id}")
    
    task_status = local_worker.get_task_status(task_id)
    
    if not task_status:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if task is already completed
    if task_status["status"] in ["SUCCESS", "FAILURE", "REVOKED"]:
        logger.info(f"Task {task_id} already finished with status {task_status['status']}")
        return {"message": "Task already finished", "status": task_status["status"]}
    
    # Mark task as revoked (we can't actually stop the thread in ThreadPoolExecutor easily,
    # but we can mark it as cancelled and the worker can check this flag)
    task_status["status"] = "REVOKED"
    task_status["updated_at"] = datetime.utcnow().timestamp()
    
    logger.info(f"Task {task_id} marked as REVOKED")
    
    return {"message": "Task cancelled", "task_id": task_id}


@router.get("/{watch_folder_id}/runs", response_model=List[JobRun])
def get_job_runs(watch_folder_id: int, limit: int = 20):
    """Get execution history for a watch folder job."""
    logger.info(f"Getting job runs for watch folder {watch_folder_id}")
    if watch_folder_id <= 0:
        logger.warning(f"Invalid watch folder ID: {watch_folder_id}")
        raise HTTPException(status_code=400, detail="Invalid watch folder ID")
    
    with Session(engine) as session:
        # Verify watch folder exists
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            logger.warning(f"Watch folder not found: {watch_folder_id}")
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        # Get recent runs, ordered by most recent first
        statement = (
            select(JobRun)
            .where(JobRun.watch_folder_id == watch_folder_id)
            .order_by(JobRun.started_at.desc())
            .limit(limit)
        )
        runs = session.exec(statement).all()
        logger.info(f"Found {len(runs)} job runs for watch folder {watch_folder_id}")
        return runs
