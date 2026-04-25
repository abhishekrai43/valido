from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import io

try:
    import pdfplumber
except ImportError:  # pragma: no cover - optional dependency
    pdfplumber = None

import fitz  # PyMuPDF

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

    if pdfplumber is not None:
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

    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        pages = list(pdf)
        if max_pages is not None:
            pages = pages[:max_pages]

        for idx, page in enumerate(pages, start=1):
            raw_words = []
            for word in page.get_text("words"):
                x0, y0, x1, y1, text, *_ = word
                raw_words.append(
                    {
                        "text": text,
                        "x0": x0,
                        "x1": x1,
                        "top": y0,
                        "bottom": y1,
                    }
                )

            words = words_from_pdfplumber(raw_words)
            layouts.append(
                PageLayout(
                    page_number=idx,
                    words=words,
                    v_lines=[],
                    h_lines=[],
                )
            )

    return layouts
