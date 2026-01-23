from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .models import BBox, HorizontalLine, VerticalLine, Word


@dataclass(frozen=True)
class CellExtractionResult:
    value: str
    bbox: Optional[BBox]


def _line_overlaps_y(v: VerticalLine, y: float, tol: float) -> bool:
    return (v.top - tol) <= y <= (v.bottom + tol)


def _line_overlaps_x(h: HorizontalLine, x: float, tol: float) -> bool:
    return (h.x0 - tol) <= x <= (h.x1 + tol)


def _find_nearest_vertical_boundary(
    v_lines: List[VerticalLine],
    *,
    y: float,
    x_ref: float,
    direction: str,
    y_tol: float,
    x_tol: float,
) -> Optional[float]:
    """Find nearest vertical line to the left or right of x_ref that overlaps y."""

    candidates: List[float] = []
    for v in v_lines:
        if not _line_overlaps_y(v, y, y_tol):
            continue
        if direction == "left":
            if v.x <= x_ref - x_tol:
                candidates.append(v.x)
        else:
            if v.x >= x_ref + x_tol:
                candidates.append(v.x)

    if not candidates:
        return None

    return max(candidates) if direction == "left" else min(candidates)


def _estimate_row_band(words: List[Word], anchor_idx: int, y_pad: float) -> BBox:
    """Estimate a row band using anchor's bbox and nearby word heights."""

    a = words[anchor_idx].bbox

    # Use anchor height as baseline, with padding.
    top = a.top - y_pad
    bottom = a.bottom + y_pad

    # Expand a bit with nearby words on same line, if any.
    a_cy = a.cy
    for w in words:
        if abs(w.bbox.cy - a_cy) <= max(1.5, a.height * 0.6):
            top = min(top, w.bbox.top - (y_pad * 0.5))
            bottom = max(bottom, w.bbox.bottom + (y_pad * 0.5))

    return BBox(x0=0.0, top=top, x1=1e9, bottom=bottom)


def _words_in_bbox(words: List[Word], bbox: BBox) -> List[Word]:
    out: List[Word] = []
    for w in words:
        if w.bbox.x1 <= bbox.x0:
            continue
        if w.bbox.x0 >= bbox.x1:
            continue
        if w.bbox.bottom <= bbox.top:
            continue
        if w.bbox.top >= bbox.bottom:
            continue
        out.append(w)
    return out


def _assemble_text_left_to_right(words: List[Word]) -> str:
    if not words:
        return ""

    # Sort by x; keep original order for ties.
    words_sorted = sorted(words, key=lambda w: (w.bbox.x0, w.bbox.top))

    parts: List[str] = []
    last_x1: Optional[float] = None
    for w in words_sorted:
        if not w.text:
            continue
        if last_x1 is not None and w.bbox.x0 - last_x1 > 2.0:
            parts.append(" ")
        parts.append(w.text)
        last_x1 = w.bbox.x1

    return "".join(parts).strip()


def extract_value_cell_right_of_anchor(
    *,
    words: List[Word],
    v_lines: List[VerticalLine],
    h_lines: List[HorizontalLine],
    anchor_idx: int,
    max_cell_width: Optional[float] = None,
    y_pad: float = 2.0,
    boundary_tol: float = 1.0,
) -> CellExtractionResult:
    """Extract the cell immediately to the right of an anchor word.

    Strategy:
      1) Estimate the anchor's row band (top..bottom around the anchor line).
      2) Find nearest vertical border to the right that overlaps that row.
      3) Find a left boundary: if there's a vertical line between anchor and
         value, use it; otherwise use anchor's right edge.
      4) Collect words whose boxes fall inside the cell and assemble text.

    Notes:
      - Horizontal lines are currently not used to bound the row; we keep them
        for future enhancement.
    """

    if anchor_idx < 0 or anchor_idx >= len(words):
        return CellExtractionResult(value="", bbox=None)

    anchor = words[anchor_idx]
    band = _estimate_row_band(words, anchor_idx, y_pad=y_pad)
    y_ref = anchor.bbox.cy

    left_border = _find_nearest_vertical_boundary(
        v_lines,
        y=y_ref,
        x_ref=anchor.bbox.x0,
        direction="left",
        y_tol=max(2.0, anchor.bbox.height * 0.8),
        x_tol=boundary_tol,
    )

    split_border = _find_nearest_vertical_boundary(
        v_lines,
        y=y_ref,
        x_ref=anchor.bbox.x1,
        direction="right",
        y_tol=max(2.0, anchor.bbox.height * 0.8),
        x_tol=boundary_tol,
    )

    if split_border is None:
        # No visible column border; fall back to whitespace-ish behavior (row band
        # only, start after anchor).
        cell_left = anchor.bbox.x1 + 1.0
        cell_right = anchor.bbox.x1 + (max_cell_width or 500.0)
    else:
        # The value cell begins at the split border.
        cell_left = split_border + boundary_tol
        next_border = _find_nearest_vertical_boundary(
            v_lines,
            y=y_ref,
            x_ref=split_border,
            direction="right",
            y_tol=max(2.0, anchor.bbox.height * 0.8),
            x_tol=boundary_tol,
        )
        if next_border is None:
            cell_right = cell_left + (max_cell_width or 500.0)
        else:
            # If next_border==split_border (can happen) ignore.
            cell_right = (next_border - boundary_tol) if next_border > cell_left else cell_left + (max_cell_width or 500.0)

    if max_cell_width is not None:
        cell_right = min(cell_right, cell_left + max_cell_width)

    cell_bbox = BBox(x0=cell_left, top=band.top, x1=cell_right, bottom=band.bottom)

    cell_words = _words_in_bbox(words, cell_bbox)

    # Remove the anchor itself (if included by bbox overlap)
    cell_words = [w for w in cell_words if w is not anchor]

    value = _assemble_text_left_to_right(cell_words)

    # Some PDFs have the label split across multiple words (e.g., "PAN" "No"),
    # so the caller may pass a different anchor selection approach later.
    return CellExtractionResult(value=value, bbox=cell_bbox)
