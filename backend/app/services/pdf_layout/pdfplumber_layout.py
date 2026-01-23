from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import io
import pdfplumber

from .edge_detection import extract_lines_from_page_edges
from .models import HorizontalLine, VerticalLine, Word
from .text_index import words_from_pdfplumber


@dataclass(frozen=True)
class PageLayout:
    page_number: int
    words: List[Word]
    v_lines: List[VerticalLine]
    h_lines: List[HorizontalLine]


def extract_page_layouts(
    pdf_bytes: bytes,
    *,
    max_pages: Optional[int] = None,
) -> List[PageLayout]:
    """Extract layout primitives (words + border lines) from a PDF."""

    layouts: List[PageLayout] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = list(pdf.pages)
        if max_pages is not None:
            pages = pages[:max_pages]

        for idx, page in enumerate(pages, start=1):
            raw_words = page.extract_words(
                keep_blank_chars=False,
                use_text_flow=True,
            )
            words = words_from_pdfplumber(raw_words)

            # page.edges is populated when lines/rects are present
            v_lines, h_lines = extract_lines_from_page_edges(getattr(page, "edges", []))

            layouts.append(
                PageLayout(
                    page_number=idx,
                    words=words,
                    v_lines=v_lines,
                    h_lines=h_lines,
                )
            )

    return layouts
