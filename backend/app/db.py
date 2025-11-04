import os
from sqlmodel import SQLModel, create_engine, Session


def _sqlite_url() -> str:
    """Return a sqlite URL for the DB file placed in the repository's backend folder.

    This computes the path relative to this module's location so callers don't need
    to run commands from a specific working directory.
    """
    # this file: backend/app/db.py -> parent is backend/app -> parent is backend
    this_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(this_dir, '..'))
    os.makedirs(backend_dir, exist_ok=True)
    db_path = os.path.join(backend_dir, 'valido.db')
    return f"sqlite:///{db_path}"


SQLITE_URL = _sqlite_url()
engine = create_engine(SQLITE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    # Ensure the parent directory exists and create tables
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
