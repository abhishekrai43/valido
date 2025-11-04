from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.get("/")
async def list_rules():
    """Stub: return empty rule list. Replace with DB-backed list in Phase 2."""
    return {"rules": []}
