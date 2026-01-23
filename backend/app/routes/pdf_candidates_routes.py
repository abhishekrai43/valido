"""PDF anchor candidate endpoint.

Used to eliminate ambiguity when the same anchor text appears multiple times
(e.g., "Basic" vs "BASIC INFORMATION").

Returns ranked candidates with contextual snippet + right-cell preview.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.pdf_layout.candidate_finder import find_anchor_candidates
from app.services.pdf_layout.models import BBox
from app.utils.logger import get_logger

logger = get_logger("PdfCandidates")

router = APIRouter(prefix="/api/v1", tags=["pdf-candidates"])
@router.post("/pdf-anchor-candidates")
async def pdf_anchor_candidates(
    file: UploadFile = File(...),
    anchor_text: str = Form(""),
    case_sensitive: bool = Form(False),
    max_pages: Optional[int] = Form(None),
    value_hint: Optional[str] = Form(None),
    selection_page: Optional[int] = Form(None),
    selection_occurrence_index_on_page: Optional[int] = Form(None),
    selection_bbox_x0: Optional[float] = Form(None),
    selection_bbox_top: Optional[float] = Form(None),
    selection_bbox_x1: Optional[float] = Form(None),
    selection_bbox_bottom: Optional[float] = Form(None),
    selection_bbox_tol: float = Form(2.0),
    limit: int = Form(25),
):
    """Return ranked candidates for an anchor text.

    Notes:
      - This endpoint is intentionally geometry-first: it returns occurrence
        metadata so the UI can let users pick the correct one.
      - It also returns a preview of the right-side value extracted using the
        border-aware cell extractor.
    """

    if not anchor_text or not str(anchor_text).strip():
        raise HTTPException(status_code=400, detail="anchor_text is required (form field)")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    selection_bbox: Optional[BBox] = None
    if (
        selection_bbox_x0 is not None
        and selection_bbox_top is not None
        and selection_bbox_x1 is not None
        and selection_bbox_bottom is not None
    ):
        try:
            selection_bbox = BBox(
                x0=float(selection_bbox_x0),
                top=float(selection_bbox_top),
                x1=float(selection_bbox_x1),
                bottom=float(selection_bbox_bottom),
            )
        except Exception:
            selection_bbox = None

    try:
        candidates = find_anchor_candidates(
            pdf_bytes=pdf_bytes,
            anchor_text=anchor_text.strip(),
            case_sensitive=case_sensitive,
            max_pages=max_pages,
            value_hint=value_hint,
            selection_page=selection_page,
            selection_occurrence_index_on_page=selection_occurrence_index_on_page,
            selection_bbox=selection_bbox,
            selection_bbox_tol=selection_bbox_tol,
            limit=limit,
        )

        out = []
        for c in candidates:
            out.append(
                {
                    "page": c.page_num,
                    "occurrenceIndexOnPage": c.occurrence_index_on_page,
                    "anchorText": c.anchor_text,
                    "anchorBBox": {
                        "x0": c.anchor_bbox.x0,
                        "top": c.anchor_bbox.top,
                        "x1": c.anchor_bbox.x1,
                        "bottom": c.anchor_bbox.bottom,
                    },
                    "previewValueRight": c.extracted_value,
                    "context": c.context,
                    "score": c.score,
                    "reasons": c.reasons,
                }
            )

        logger.info(
            f"Candidates: anchor='{anchor_text}' count={len(out)} file='{file.filename}'"
        )

        return {"success": True, "anchor": anchor_text, "candidates": out}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Candidate generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate candidates: {e}")
