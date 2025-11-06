from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime

from app.db import engine
from app.models import WatchFolder, Ruleset

router = APIRouter(prefix="/api/v1/watch-folders", tags=["watch-folders"])


@router.get("/", response_model=List[WatchFolder])
def list_watch_folders():
    """List all watch folder configurations."""
    with Session(engine) as session:
        statement = select(WatchFolder)
        watch_folders = session.exec(statement).all()
        return watch_folders


@router.get("/{watch_folder_id}", response_model=WatchFolder)
def get_watch_folder(watch_folder_id: int):
    """Get a specific watch folder configuration."""
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            raise HTTPException(status_code=404, detail="Watch folder not found")
        return watch_folder


@router.post("/", response_model=WatchFolder)
def create_watch_folder(watch_folder: WatchFolder):
    """Create a new watch folder configuration."""
    with Session(engine) as session:
        # Verify ruleset exists
        ruleset = session.get(Ruleset, watch_folder.ruleset_id)
        if not ruleset:
            raise HTTPException(status_code=404, detail="Ruleset not found")
        
        session.add(watch_folder)
        session.commit()
        session.refresh(watch_folder)
        return watch_folder


@router.put("/{watch_folder_id}", response_model=WatchFolder)
def update_watch_folder(watch_folder_id: int, updated: WatchFolder):
    """Update an existing watch folder configuration."""
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
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
        return watch_folder


@router.delete("/{watch_folder_id}")
def delete_watch_folder(watch_folder_id: int):
    """Delete a watch folder configuration."""
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        session.delete(watch_folder)
        session.commit()
        return {"ok": True}


@router.post("/{watch_folder_id}/toggle")
def toggle_watch_folder(watch_folder_id: int):
    """Enable or disable a watch folder."""
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        watch_folder.enabled = not watch_folder.enabled
        session.add(watch_folder)
        session.commit()
        session.refresh(watch_folder)
        return watch_folder


@router.post("/{watch_folder_id}/update-stats")
def update_stats(watch_folder_id: int, files_processed: int):
    """Update statistics after processing (called by agent)."""
    with Session(engine) as session:
        watch_folder = session.get(WatchFolder, watch_folder_id)
        if not watch_folder:
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        watch_folder.last_run = datetime.utcnow()
        watch_folder.files_processed_total += files_processed
        
        session.add(watch_folder)
        session.commit()
        session.refresh(watch_folder)
        return watch_folder
