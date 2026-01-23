from __future__ import annotations

import re
from typing import List, Optional

from .cell_extractor import extract_value_cell_right_of_anchor
from .pdfplumber_layout import extract_page_layouts
from .text_index import find_text_anchors


def extract_border_aware_values(
    *,
    pdf_bytes: bytes,
    anchor_text: str,
    occurrence: str = "first",
    case_sensitive: bool = False,
    max_pages: Optional[int] = None,
    value_hint: Optional[str] = None,
) -> str:
    """Extract value(s) for a label inside a bordered table-like layout.

    This is used when the UI marks a field as "in table" and provides a column.
    In the border-aware mode, the "column" is interpreted as "cell to the right
    of the anchor" (i.e., key/value table).

    occurrence: "first" | "last" | "all"

    Returns:
        For "all": newline-separated values (Excel-friendly).
        Otherwise: single string.
    """

    layouts = extract_page_layouts(pdf_bytes, max_pages=max_pages)

    def _matches_hint(val: str) -> bool:
        if not value_hint:
            return True

        hint = value_hint.strip().lower()
        if not hint:
            return True

        # Common hint: currency/amount
        if hint in {"amount", "currency", "money"}:
            return bool(re.search(r"[₹$€£]|\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b", val))

        if hint in {"number", "numeric"}:
            return bool(re.search(r"\b\d+(?:\.\d+)?\b", val))

        # Regex hint: 're:<pattern>'
        if hint.startswith("re:"):
            try:
                return bool(re.search(value_hint[3:], val))
            except re.error:
                return True

        # Generic contains
        return hint in val.lower()

    collected: List[str] = []
    for layout in layouts:
        anchors = find_text_anchors(layout.words, anchor_text, case_sensitive=case_sensitive)
        if not anchors:
            continue

        for a_idx in anchors:
            res = extract_value_cell_right_of_anchor(
                words=layout.words,
                v_lines=layout.v_lines,
                h_lines=layout.h_lines,
                anchor_idx=a_idx,
            )
            if res.value and _matches_hint(res.value):
                collected.append(res.value)

    if not collected:
        return ""

    if occurrence == "last":
        return collected[-1]

    if occurrence == "all":
        # Keep order, lightly de-dup adjacent duplicates.
        deduped: List[str] = []
        for v in collected:
            if not deduped or deduped[-1] != v:
                deduped.append(v)
        return "\n".join(deduped)

    return collected[0]
