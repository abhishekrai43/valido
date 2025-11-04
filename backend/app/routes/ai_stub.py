from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_session
from app.models import Ruleset

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
    text = payload.text or ""
    name = payload.name or f"ruleset-{hash(text) & 0xFFFF:X}"

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
            return {
                'id': r.id,
                'name': r.name,
                'rules': r.rules,
                'is_active': r.is_active,
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to persist ruleset: {exc}")
