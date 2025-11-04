from typing import Optional, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.types import JSON


class Ruleset(SQLModel, table=True):
    """Stores a named ruleset. The `rules` column stores the JSON rules payload."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    # store rules as JSON in the DB
    rules: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    is_active: bool = Field(default=False)


class User(SQLModel, table=True):
    """Simple user tracking for counting processed files."""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, nullable=False)
    total_processed: int = Field(default=0)

