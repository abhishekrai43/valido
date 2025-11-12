import os
import sys
from sqlmodel import SQLModel, create_engine, Session


def _sqlite_url() -> str:
    """Return a sqlite URL for the DB file.
    Uses local config file if present, otherwise falls back to local backend/data folder.
    Handles PyInstaller frozen apps correctly.
    """
    # Handle PyInstaller frozen app
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        base_dir = os.getcwd()
    
    # Try agent config first
    config_path = os.path.join(base_dir, 'agent', 'agent_config.json')
    db_url = None
    if os.path.exists(config_path):
        try:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
                db_url = config.get('database_url')
        except Exception:
            db_url = None
    
    if db_url:
        return db_url
    
    # Fallback: create data directory next to executable or in current directory
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'valido.db')
    return f"sqlite:///{db_path}"


SQLITE_URL = _sqlite_url()
engine = create_engine(SQLITE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    """Create all database tables. Models must be imported before calling this."""
    # Import all models to register them with SQLModel metadata
    from app.models import Ruleset, User, WatchFolder, JobRun, UsageRecord  # noqa: F401
    
    # Now create all tables
    SQLModel.metadata.create_all(engine)
    
    # Verify tables were created by checking the database file
    if SQLITE_URL.startswith("sqlite:///"):
        db_path = SQLITE_URL.replace("sqlite:///", "")
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"✓ Database file created: {db_path} ({size} bytes)")


def get_session() -> Session:
    return Session(engine)


# !! IMPORTANT: Auto-initialize database when this module is imported
# This ensures tables exist even if startup events don't fire in frozen apps
try:
    print(f"🔧 Auto-initializing database on import: {SQLITE_URL}")
    create_db_and_tables()
    print("✓ Database tables created successfully on import")
except Exception as e:
    print(f"✗ Failed to auto-initialize database: {e}")
    import traceback
    traceback.print_exc()
