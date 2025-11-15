"""
Cloud database connection for Supabase (PostgreSQL)
Used for:
- License validation and device tracking
- Version checking and updates
- Centralized license management
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session, text
from typing import Optional

# Load environment variables from .env file
# Find the .env file in the project root
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    env_path = Path(sys.executable).parent / '.env'
else:
    # Running as script - cloud_db.py is in backend/app/, so go up 2 levels
    env_path = Path(__file__).parent.parent.parent / '.env'

# Also try loading from current working directory
if not env_path.exists():
    env_path = Path.cwd() / '.env'

load_dotenv(env_path)

# Get Supabase connection parameters from environment
DB_USER = os.getenv('user')
DB_PASSWORD = os.getenv('password')
DB_HOST = os.getenv('host')
DB_PORT = os.getenv('port')
DB_NAME = os.getenv('dbname')

# Build connection URL
SUPABASE_URL = None
if all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    # Use urllib.parse to properly encode the password
    from urllib.parse import quote_plus
    encoded_password = quote_plus(DB_PASSWORD)
    SUPABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create cloud engine (only if URL is provided)
cloud_engine = None
if SUPABASE_URL:
    cloud_engine = create_engine(
        SUPABASE_URL,
        echo=False,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10
    )


def get_cloud_session() -> Optional[Session]:
    """Get a session to the cloud database (Supabase)"""
    if cloud_engine is None:
        return None
    return Session(cloud_engine)


def create_cloud_tables() -> None:
    """Create tables in cloud database (Supabase)
    Run this once to initialize your cloud schema
    """
    if cloud_engine is None:
        raise ValueError("SUPABASE_URL not configured in .env file")
    
    # Import cloud models
    from app.models import CloudLicense, AppVersion, LicenseUsage  # noqa: F401
    
    # Create all tables
    SQLModel.metadata.create_all(cloud_engine)


def test_cloud_connection() -> bool:
    """Test if cloud database connection is working"""
    if cloud_engine is None:
        return False
    
    try:
        with Session(cloud_engine) as session:
            # Simple query to test connection
            session.exec(text("SELECT 1")).first()
        return True
    except Exception as e:
        print(f"Cloud DB connection failed: {e}")
        return False
