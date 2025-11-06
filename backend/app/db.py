import os
from sqlmodel import SQLModel, create_engine, Session


def _sqlite_url() -> str:
    """Return a sqlite URL for the DB file.
    Uses local config file if present, otherwise falls back to local backend/data folder.
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'agent', 'agent_config.json')
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
    # Fallback for local development
    this_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(this_dir, '..'))
    data_dir = os.path.join(backend_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'valido.db')
    return f"sqlite:///{db_path}"


SQLITE_URL = _sqlite_url()
engine = create_engine(SQLITE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    # Ensure the parent directory exists and create tables
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
