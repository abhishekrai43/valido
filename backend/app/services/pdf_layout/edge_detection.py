from __future__ import annotations

from typing import Iterable, List, Mapping, Tuple

from .models import HorizontalLine, VerticalLine


def _as_float(v) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _norm_segment(a: float, b: float) -> Tuple[float, float]:
    return (a, b) if a <= b else (b, a)


def extract_lines_from_page_edges(
    edges: Iterable[Mapping],
    *,
    angle_tolerance_deg: float = 2.0,
    min_length: float = 3.0,
) -> Tuple[List[VerticalLine], List[HorizontalLine]]:
    """Convert pdfplumber page.edges into vertical/horizontal line segments.

    pdfplumber supplies edge dicts with keys like x0,x1,top,bottom,width,height.
    We classify a segment as vertical if its x-span is tiny compared to y-span,
    and horizontal if its y-span is tiny compared to x-span.

    Returns:
        (vertical_lines, horizontal_lines)
    """

    v_lines: List[VerticalLine] = []
    h_lines: List[HorizontalLine] = []

    # We'll avoid depending on the 'angle' field (not always present) and use
    # geometric heuristics.
    for e in edges or []:
        x0 = _as_float(e.get("x0"))
        x1 = _as_float(e.get("x1"))
        top = _as_float(e.get("top"))
        bottom = _as_float(e.get("bottom"))

        x0, x1 = _norm_segment(x0, x1)
        top, bottom = _norm_segment(top, bottom)

        dx = abs(x1 - x0)
        dy = abs(bottom - top)

        # Some edges are represented as very thin rectangles.
        if dx < 0.5 and dy >= min_length:
            v_lines.append(VerticalLine(x=(x0 + x1) / 2.0, top=top, bottom=bottom))
            continue

        if dy < 0.5 and dx >= min_length:
            h_lines.append(HorizontalLine(y=(top + bottom) / 2.0, x0=x0, x1=x1))
            continue

        # Fallback: compare aspect ratio
        if dy >= min_length and dy > dx * 5:
            v_lines.append(VerticalLine(x=(x0 + x1) / 2.0, top=top, bottom=bottom))
        elif dx >= min_length and dx > dy * 5:
            h_lines.append(HorizontalLine(y=(top + bottom) / 2.0, x0=x0, x1=x1))

    return v_lines, h_lines
