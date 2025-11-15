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
    """User account with trial and license information."""
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, nullable=False)
    
    # Trial tracking
    trial_start_date: Optional[datetime] = Field(default=None)  # When trial started
    trial_expired: bool = Field(default=False)  # Whether trial has expired
    
    # License information
    license_key: Optional[str] = Field(default=None)  # Activation key from payment platform
    license_active: bool = Field(default=False)  # Whether license is currently active
    license_type: Optional[str] = Field(default=None)  # "monthly" or "annual"
    license_activated_at: Optional[datetime] = Field(default=None)  # When license was activated


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


class UsageRecord(SQLModel, table=True):
    """Tracks PDF processing for free tier limits."""
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    pdf_count: int = Field(default=0)  # Number of PDFs processed in this batch
    processed_at: datetime = Field(default_factory=datetime.now, index=True)  # When processed


class DeviceActivation(SQLModel, table=True):
    """Tracks device activations to prevent license abuse across multiple devices/networks."""
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    purchase_email: str = Field(index=True)  # Email used to purchase license
    hardware_id: str = Field(index=True)  # Unique device identifier
    network_id: str = Field(index=True)  # Network fingerprint to prevent LAN abuse
    license_type: str  # "monthly" or "annual"
    
    # Activation details
    activated_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # Device info (for user reference)
    computer_name: Optional[str] = Field(default=None)
    network_info: Optional[str] = Field(default=None)  # Human-readable network description

