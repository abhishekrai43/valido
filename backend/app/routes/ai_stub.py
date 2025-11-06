from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_session
from app.models import Ruleset
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class AIConvertRequest(BaseModel):
    text: str
    name: Optional[str] = None


class GeneratedRule(BaseModel):
    description: str
    hint: Optional[str] = None


@router.post("/convert")
def convert_text_to_ruleset(payload: AIConvertRequest):
    """A lightweight stub that converts free-text into a stored ruleset JSON.

    This is intentionally conservative: it stores the original text and a small
    list of generated heuristic rules derived from lines. The real AI conversion
    should be implemented in a separate service or via a controlled model.
    """
    logger.info("Converting text to ruleset")
    text = payload.text or ""
    
    # Validation: Check text length
    if len(text) > 10000:  # Reasonable limit
        logger.warning(f"Text too long: {len(text)} characters")
        raise HTTPException(status_code=400, detail="Text too long (max 10000 characters)")
    
    if not text.strip():
        logger.warning("Empty text provided")
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    name = payload.name or f"ruleset-{hash(text) & 0xFFFF:X}"
    
    # Validation: Check name
    if len(name) > 100:
        logger.warning(f"Name too long: {name}")
        raise HTTPException(status_code=400, detail="Name too long (max 100 characters)")
    
    logger.info(f"Processing text of length {len(text)} with name '{name}'")

    # Simple heuristic: treat each non-empty line as a suggested rule description.
    generated: List[dict] = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        # Heuristic hinting: detect presence of 'must' / 'should' / 'not'
        hint = None
        ls = s.lower()
        if 'must' in ls or 'required' in ls or 'required to' in ls:
            hint = 'required'
        elif 'should' in ls or 'recommend' in ls:
            hint = 'recommended'
        elif 'not' in ls or 'never' in ls:
            hint = 'forbidden'

        generated.append({
            'description': s,
            'hint': hint,
        })

    ruleset_payload = {
        'source_text': text,
        'generated_rules': generated,
    }

    # Persist as a Ruleset
    try:
        with get_session() as session:
            r = Ruleset(name=name, rules=ruleset_payload, is_active=False)
            session.add(r)
            session.commit()
            session.refresh(r)
            logger.info(f"Ruleset created: {r.id}")
            return {
                'id': r.id,
                'name': r.name,
                'rules': r.rules,
                'is_active': r.is_active,
            }
    except Exception as exc:
        logger.error(f"Failed to persist ruleset: {exc}")
        raise HTTPException(status_code=500, detail=f"failed to persist ruleset: {exc}")
