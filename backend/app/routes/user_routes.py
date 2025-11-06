from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.db import get_session
from app.models import User
from app.utils.logger import get_logger

logger = get_logger("UserRoutes")

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserCreate(BaseModel):
    username: str


class UserRead(BaseModel):
    id: int
    username: str
    total_processed: int


@router.get("/", response_model=List[UserRead])
def list_users():
    logger.info("Listing users")
    with get_session() as session:
        stmt = select(User)
        results = session.exec(stmt).all()
        logger.info(f"Found {len(results)} users")
        return results


@router.post("/", response_model=UserRead)
def create_user(payload: UserCreate):
    logger.info(f"Creating user: {payload.username}")
    if not payload.username or len(payload.username.strip()) == 0:
        logger.warning("Empty username")
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    with get_session() as session:
        existing = session.exec(select(User).where(User.username == payload.username)).first()
        if existing:
            logger.warning(f"Duplicate username: {payload.username}")
            raise HTTPException(status_code=409, detail="user already exists")
        u = User(username=payload.username, total_processed=0)
        session.add(u)
        session.commit()
        session.refresh(u)
        logger.info(f"User created: {u.id}")
        return u


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int):
    logger.info(f"Getting user: {user_id}")
    if user_id <= 0:
        logger.warning(f"Invalid user ID: {user_id}")
        raise HTTPException(status_code=400, detail="Invalid user ID")
    with get_session() as session:
        u = session.get(User, user_id)
        if not u:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="user not found")
        return u
