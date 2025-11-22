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
    input_path: str  # Folder to watch (or cloud:// URL for cloud storage)
    output_path: str  # Where to save results
    ruleset_id: int  # Which ruleset to apply
    
    # Schedule configuration
    schedule_times: Optional[str] = Field(default=None)  # Comma-separated times e.g. "18:00, 12:00"
    
    # Post-processing
    move_processed: bool = Field(default=True)
    processed_path: Optional[str] = Field(default=None)
    delete_after: bool = Field(default=False)
    
    # Status
    enabled: bool = Field(default=True)
    last_run: Optional[datetime] = Field(default=None)
    files_processed_total: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Cloud storage configuration (Enterprise feature)
    cloud_config: Optional[Any] = Field(default=None, sa_column=Column(JSON))  # Stores cloud provider config


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


class CloudSource(SQLModel, table=True):
    """Stores saved cloud storage configurations for reuse."""
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # User-friendly name (e.g., "Production Azure", "Dev S3")
    provider: str = Field(index=True)  # 'azure', 'aws', or 'gcp'
    config: Any = Field(sa_column=Column(JSON))  # Provider-specific configuration (credentials, etc.)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = Field(default=None)  # Track usage for sorting


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


# ============================================================================
# CLOUD MODELS (Supabase) - For centralized license management
# ============================================================================

class CloudLicense(SQLModel, table=True):
    """Cloud-stored license information for device tracking and validation.
    Stored in Supabase to prevent license abuse across multiple devices.
    """
    __tablename__ = "licenses"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    license_key: str = Field(index=True, unique=True)  # Unique license key from Gumroad
    purchase_email: str = Field(index=True)  # Email used for purchase
    
    # Device tracking (JSON array of hardware IDs)
    device_ids: Optional[str] = Field(default=None)  # JSON array: ["device1", "device2"]
    max_devices: int = Field(default=1)  # How many devices allowed (1, 3, or 5)
    
    # License details
    license_type: str  # "monthly" or "annual"
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)


class AppVersion(SQLModel, table=True):
    """Tracks app versions for update notifications.
    Stored in Supabase so all users can check for updates.
    """
    __tablename__ = "app_versions"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    version: str = Field(index=True, unique=True)  # e.g. "1.0.1"
    release_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Update details
    download_url: Optional[str] = Field(default=None)  # Where to download
    changelog: Optional[str] = Field(default=None)  # What's new
    is_latest: bool = Field(default=False)  # Mark the current latest version
    is_required: bool = Field(default=False)  # Force update if True


class LicenseUsage(SQLModel, table=True):
    """Tracks when licenses are validated (optional analytics).
    Helps understand usage patterns and detect suspicious activity.
    """
    __tablename__ = "license_usage"
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    license_key: str = Field(index=True)
    device_id: str = Field(index=True)
    
    # Usage tracking
    last_validated: datetime = Field(default_factory=datetime.utcnow)
    app_version: Optional[str] = Field(default=None)  # Which version user is on
    validation_count: int = Field(default=1)  # How many times validated
