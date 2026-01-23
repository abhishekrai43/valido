from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .cell_extractor import extract_value_cell_right_of_anchor
from .models import BBox
from .pdfplumber_layout import extract_page_layouts
from .text_index import find_text_anchors


@dataclass(frozen=True)
class AnchorCandidate:
    page_num: int  # 1-based
    occurrence_index_on_page: int  # 0-based
    anchor_text: str
    anchor_bbox: BBox
    extracted_value: str
    context: str
    score: float
    reasons: List[str]


def _bbox_close(b: BBox, *, x0: float, top: float, x1: float, bottom: float, tol: float) -> bool:
    return (
        abs(b.x0 - x0) <= tol
        and abs(b.top - top) <= tol
        and abs(b.x1 - x1) <= tol
        and abs(b.bottom - bottom) <= tol
    )


def _build_context_snippet(*, words, anchor_i: int, window: int = 6) -> str:
    start = max(0, anchor_i - window)
    end = min(len(words), anchor_i + window + 1)
    parts: List[str] = []
    for w in words[start:end]:
        if not w.text:
            continue
        parts.append(w.text)
    return " ".join(parts).strip()


def _score_candidate(*, extracted_value: str, has_split_border: bool, has_next_border: bool, value_hint: Optional[str]) -> tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []

    if extracted_value:
        score += 2.0
        reasons.append("extracted-nonempty")
    else:
        reasons.append("extracted-empty")

    if has_split_border:
        score += 1.5
        reasons.append("has-right-border")

    if has_next_border:
        score += 0.5
        reasons.append("has-next-border")

    # Hint matching: keep this logic self-contained so the candidate endpoint
    # is fast and doesn't need to fully extract all values first.
    if value_hint:
        vh = value_hint.strip().lower()
        if vh in {"amount", "currency", "money"}:
            import re

            if re.search(r"[₹$€£]|\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b", extracted_value):
                score += 1.0
                reasons.append("hint-match")
            else:
                score -= 0.5
                reasons.append("hint-miss")
        elif vh in {"number", "numeric"}:
            import re

            if re.search(r"\b\d+(?:\.\d+)?\b", extracted_value):
                score += 0.7
                reasons.append("hint-match")
            else:
                score -= 0.3
                reasons.append("hint-miss")
        elif vh.startswith("re:"):
            import re

            try:
                if re.search(value_hint[3:], extracted_value):
                    score += 0.8
                    reasons.append("hint-match")
                else:
                    score -= 0.4
                    reasons.append("hint-miss")
            except re.error:
                reasons.append("hint-invalid-regex")
        else:
            if vh in extracted_value.lower():
                score += 0.4
                reasons.append("hint-match")
            else:
                score -= 0.2
                reasons.append("hint-miss")

    return score, reasons


def find_anchor_candidates(
    *,
    pdf_bytes: bytes,
    anchor_text: str,
    case_sensitive: bool = False,
    max_pages: Optional[int] = None,
    value_hint: Optional[str] = None,
    selection_page: Optional[int] = None,
    selection_occurrence_index_on_page: Optional[int] = None,
    selection_bbox: Optional[BBox] = None,
    selection_bbox_tol: float = 2.0,
    limit: int = 25,
) -> List[AnchorCandidate]:
    """Return ranked candidates for an anchor_text.

    selection_* fields are optional and are used to boost the intended candidate
    (when the UI already picked one previously).

    page_num is 1-based.
    """

    if not pdf_bytes or not anchor_text:
        return []

    layouts = extract_page_layouts(pdf_bytes, max_pages=max_pages)

    candidates: List[AnchorCandidate] = []

    for page_i, layout in enumerate(layouts, start=1):
        anchors = find_text_anchors(layout.words, anchor_text, case_sensitive=case_sensitive)
        if not anchors:
            continue

        for occ_idx, a_idx in enumerate(anchors):
            anchor_word = layout.words[a_idx]
            res = extract_value_cell_right_of_anchor(
                words=layout.words,
                v_lines=layout.v_lines,
                h_lines=layout.h_lines,
                anchor_idx=a_idx,
            )

            # Determine border features by checking if we actually bounded by a split border.
            # Heuristic: if bbox exists and its x0 is close to anchor.x1, then we likely fell back.
            has_split_border = False
            has_next_border = False
            if res.bbox is not None:
                # If bounded, the left edge should typically be to the right of anchor.x1 by > 1px.
                if res.bbox.x0 > (anchor_word.bbox.x1 + 1.0):
                    has_split_border = True
                # Next border is implied if cell width isn't huge (bounded on right).
                if (res.bbox.x1 - res.bbox.x0) < 450.0:
                    has_next_border = True

            score, reasons = _score_candidate(
                extracted_value=res.value,
                has_split_border=has_split_border,
                has_next_border=has_next_border,
                value_hint=value_hint,
            )

            # Boost if matches selection.
            if selection_page is not None and selection_page == page_i:
                score += 1.0
                reasons.append("selection-page-match")

            if selection_occurrence_index_on_page is not None and selection_occurrence_index_on_page == occ_idx:
                score += 2.0
                reasons.append("selection-occurrence-match")

            if selection_bbox is not None and _bbox_close(
                anchor_word.bbox,
                x0=selection_bbox.x0,
                top=selection_bbox.top,
                x1=selection_bbox.x1,
                bottom=selection_bbox.bottom,
                tol=selection_bbox_tol,
            ):
                score += 3.0
                reasons.append("selection-bbox-match")

            context = _build_context_snippet(words=layout.words, anchor_i=a_idx, window=6)

            candidates.append(
                AnchorCandidate(
                    page_num=page_i,
                    occurrence_index_on_page=occ_idx,
                    anchor_text=anchor_text,
                    anchor_bbox=anchor_word.bbox,
                    extracted_value=res.value,
                    context=context,
                    score=score,
                    reasons=reasons,
                )
            )

    # Rank: score desc, then page asc, then earliest occurrence.
    candidates_sorted = sorted(candidates, key=lambda c: (-c.score, c.page_num, c.occurrence_index_on_page))

    return candidates_sorted[: max(1, min(limit, 200))]
