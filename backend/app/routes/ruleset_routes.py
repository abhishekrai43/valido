from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.db import get_session
from app.models import Ruleset

router = APIRouter(prefix="/api/v1/rulesets", tags=["rulesets"])


class RulesetCreate(BaseModel):
    name: str
    rules: Optional[dict] = {}


class RulesetRead(BaseModel):
    id: int
    name: str
    rules: Optional[dict]
    is_active: bool


@router.get("/", response_model=List[RulesetRead])
def list_rulesets():
    with get_session() as session:
        stmt = select(Ruleset)
        results = session.exec(stmt).all()
        return results


@router.post("/", response_model=RulesetRead)
def create_ruleset(payload: RulesetCreate):
    with get_session() as session:
        # simple duplicate-name guard
        existing = session.exec(select(Ruleset).where(Ruleset.name == payload.name)).first()
        if existing:
            raise HTTPException(status_code=409, detail="ruleset with this name already exists")

        r = Ruleset(name=payload.name, rules=payload.rules or {}, is_active=False)
        session.add(r)
        session.commit()
        session.refresh(r)
        return r


@router.get("/{ruleset_id}", response_model=RulesetRead)
def get_ruleset(ruleset_id: int):
    with get_session() as session:
        r = session.get(Ruleset, ruleset_id)
        if not r:
            raise HTTPException(status_code=404, detail="ruleset not found")
        return r


@router.put("/{ruleset_id}", response_model=RulesetRead)
def update_ruleset(ruleset_id: int, payload: RulesetCreate):
    with get_session() as session:
        r = session.get(Ruleset, ruleset_id)
        if not r:
            raise HTTPException(status_code=404, detail="ruleset not found")
        r.name = payload.name
        r.rules = payload.rules or {}
        session.add(r)
        session.commit()
        session.refresh(r)
        return r


@router.delete("/{ruleset_id}")
def delete_ruleset(ruleset_id: int):
    with get_session() as session:
        r = session.get(Ruleset, ruleset_id)
        if not r:
            raise HTTPException(status_code=404, detail="ruleset not found")
        session.delete(r)
        session.commit()
        return {"deleted": True}


@router.post("/{ruleset_id}/activate")
def activate_ruleset(ruleset_id: int):
    with get_session() as session:
        r = session.get(Ruleset, ruleset_id)
        if not r:
            raise HTTPException(status_code=404, detail="ruleset not found")

        # deactivate others
        stmt = select(Ruleset)
        all_rs = session.exec(stmt).all()
        for other in all_rs:
            if other.id != r.id and other.is_active:
                other.is_active = False
                session.add(other)

        r.is_active = True
        session.add(r)
        session.commit()
        session.refresh(r)
        return {"activated": ruleset_id}


@router.get("/active", response_model=Optional[RulesetRead])
def get_active_ruleset():
    with get_session() as session:
        stmt = select(Ruleset).where(Ruleset.is_active == True)
        r = session.exec(stmt).first()
        if not r:
            return None
        return r
