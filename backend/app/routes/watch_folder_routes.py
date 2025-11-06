from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime

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
