from typing import Optional, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.types import JSON


class Ruleset(SQLModel, table=True):
    """Stores a named ruleset. The `rules` column stores the JSON rules payload."""
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    # store rules as JSON in the DB
    rules: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    is_active: bool = Field(default=False)


class User(SQLModel, table=True):
    """Simple user tracking for counting processed files."""
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, nullable=False)
    total_processed: int = Field(default=0)


class WatchFolder(SQLModel, table=True):
    """Stores automated folder processing configuration."""
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # User-friendly name
    input_path: str  # Folder to watch
    output_path: str  # Where to save results
    ruleset_id: int  # Which ruleset to apply
    
    # Schedule configuration
    schedule_times: Optional[str] = Field(default=None)  # JSON array of times e.g. ["18:00", "12:00"]
    
    # Post-processing
    move_processed: bool = Field(default=True)
    processed_path: Optional[str] = Field(default=None)
    delete_after: bool = Field(default=False)
    
    # Status
    enabled: bool = Field(default=True)
    last_run: Optional[datetime] = Field(default=None)
    files_processed_total: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JobRun(SQLModel, table=True):
    """Stores execution history for automation jobs."""
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    watch_folder_id: int = Field(foreign_key="watchfolder.id", index=True)
    
    # Execution details
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="running")  # running, success, failed, partial
    
    # Results location
    pc_name: Optional[str] = Field(default=None)
    output_path: Optional[str] = Field(default=None)
    
    # Results
    files_found: int = Field(default=0)
    files_processed: int = Field(default=0)
    files_succeeded: int = Field(default=0)
    files_failed: int = Field(default=0)
    
    # Error tracking
    error_message: Optional[str] = Field(default=None)
    details: Optional[Any] = Field(default=None, sa_column=Column(JSON))  # Stores file-level results
