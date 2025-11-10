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
from app.models import WatchFolder, Ruleset
from app.utils.logger import get_logger

logger = get_logger("WatchFolderRoutes")

router = APIRouter(prefix="/api/v1/watch-folders", tags=["watch-folders"])


@router.get("/", response_model=List[WatchFolder])
def list_watch_folders():
    """List all watch folder configurations."""
    logger.info("Listing watch folders")
    with Session(engine) as session:
        statement = select(WatchFolder)
        watch_folders = session.exec(statement).all()
        logger.info(f"Found {len(watch_folders)} watch folders")
        return watch_folders


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
    # Validate paths
    import os
    if not os.path.isabs(watch_folder.input_path):
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
        
        session.add(watch_folder)
        session.commit()
        session.refresh(watch_folder)
        logger.info(f"Watch folder created: {watch_folder.id}")
        return watch_folder


@router.put("/{watch_folder_id}", response_model=WatchFolder)
def update_watch_folder(watch_folder_id: int, updated: WatchFolder):
    """Update an existing watch folder configuration."""
    logger.info(f"Updating watch folder: {watch_folder_id}")
    if watch_folder_id <= 0:
        logger.warning(f"Invalid watch folder ID: {watch_folder_id}")
        raise HTTPException(status_code=400, detail="Invalid watch folder ID")
    # Validate paths
    import os
    if not os.path.isabs(updated.input_path):
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
        
        # Check input folder exists and has files
        if not os.path.exists(watch_folder.input_path):
            logger.warning(f"Input folder does not exist: {watch_folder.input_path}")
            raise HTTPException(status_code=400, detail="Input folder does not exist")
        
        # Get list of PDF files
        pdf_files = [f for f in os.listdir(watch_folder.input_path) if f.lower().endswith('.pdf')]
        if not pdf_files:
            logger.info(f"No PDF files found in {watch_folder.input_path}")
            raise HTTPException(status_code=400, detail="No PDF files found in input folder")
        
        # Read PDF files into memory for processing
        files_list = []
        for filename in pdf_files:
            filepath = os.path.join(watch_folder.input_path, filename)
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                files_list.append({
                    'filename': filename,
                    'content': content
                })
            except Exception as e:
                logger.error(f"Failed to read {filepath}: {e}")
                continue
        
        if not files_list:
            logger.error(f"Failed to read any PDF files from {watch_folder.input_path}")
            raise HTTPException(status_code=500, detail="Failed to read PDF files")
        
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
            'ruleset_name': ruleset.name if ruleset else 'Unknown'
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
        
        return {
            "task_id": task_id,
            "watch_folder_id": watch_folder_id,
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
