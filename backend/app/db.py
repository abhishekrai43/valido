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
    from app.models import Ruleset, User, WatchFolder, JobRun, UsageRecord, DeviceActivation, CloudSource  # noqa: F401
    
    # Now create all tables
    SQLModel.metadata.create_all(engine)
    
    # Handle migrations for existing databases
    _migrate_database()
    
    # Verify tables were created by checking the database file
    if SQLITE_URL.startswith("sqlite:///"):
        db_path = SQLITE_URL.replace("sqlite:///", "")
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"✓ Database file created: {db_path} ({size} bytes)")


def _migrate_database() -> None:
    """Handle database schema migrations for existing databases."""
    try:
        from sqlalchemy import text
        with Session(engine) as session:
            # Check if User table needs migration (add trial columns if missing)
            result = session.execute(text("PRAGMA table_info(user)"))
            columns = {row[1] for row in result.fetchall()}
            
            if 'trial_start_date' not in columns:
                print("📦 Migrating User table: adding trial_start_date column")
                session.execute(text("ALTER TABLE user ADD COLUMN trial_start_date TIMESTAMP"))
                session.commit()
            
            if 'trial_expired' not in columns:
                print("📦 Migrating User table: adding trial_expired column")
                session.execute(text("ALTER TABLE user ADD COLUMN trial_expired BOOLEAN DEFAULT 0"))
                session.commit()
            
            if 'license_type' not in columns:
                print("📦 Migrating User table: adding license_type column")
                session.execute(text("ALTER TABLE user ADD COLUMN license_type VARCHAR"))
                session.commit()
            
            if 'license_activated_at' not in columns:
                print("📦 Migrating User table: adding license_activated_at column")
                session.execute(text("ALTER TABLE user ADD COLUMN license_activated_at TIMESTAMP"))
                session.commit()
            
            # Check if WatchFolder table needs migration (add cloud_config column if missing)
            result = session.execute(text("PRAGMA table_info(watchfolder)"))
            watchfolder_columns = {row[1] for row in result.fetchall()}
            
            if 'cloud_config' not in watchfolder_columns:
                print("📦 Migrating WatchFolder table: adding cloud_config column")
                session.execute(text("ALTER TABLE watchfolder ADD COLUMN cloud_config JSON"))
                session.commit()
            
            print("✓ Database migration completed successfully")
    except Exception as e:
        print(f"⚠️  Database migration check failed (this is okay for new databases): {e}")


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
