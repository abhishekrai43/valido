from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.db import get_session
from app.models import User

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserCreate(BaseModel):
    username: str


class UserRead(BaseModel):
    id: int
    username: str
    total_processed: int


@router.get("/", response_model=List[UserRead])
def list_users():
    with get_session() as session:
        stmt = select(User)
        results = session.exec(stmt).all()
        return results


@router.post("/", response_model=UserRead)
def create_user(payload: UserCreate):
    with get_session() as session:
        existing = session.exec(select(User).where(User.username == payload.username)).first()
        if existing:
            raise HTTPException(status_code=409, detail="user already exists")
        u = User(username=payload.username, total_processed=0)
        session.add(u)
        session.commit()
        session.refresh(u)
        return u


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int):
    with get_session() as session:
        u = session.get(User, user_id)
        if not u:
            raise HTTPException(status_code=404, detail="user not found")
        return u
