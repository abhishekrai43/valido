from __future__ import annotations

from typing import Iterable, List

from .models import BBox, Word


def _safe_text(s) -> str:
    return "" if s is None else str(s)


def words_from_pdfplumber(words: Iterable[dict]) -> List[Word]:
    """Convert pdfplumber extracted-words into our Word model."""

    out: List[Word] = []
    for w in words or []:
        text = _safe_text(w.get("text")).strip()
        if not text:
            continue

        # pdfplumber word dict commonly has: x0, x1, top, bottom
        try:
            bbox = BBox(
                x0=float(w.get("x0", 0.0)),
                top=float(w.get("top", 0.0)),
                x1=float(w.get("x1", 0.0)),
                bottom=float(w.get("bottom", 0.0)),
            )
        except Exception:
            continue

        out.append(Word(text=text, bbox=bbox))

    return out


def find_text_anchors(words: List[Word], anchor_text: str, *, case_sensitive: bool = False) -> List[int]:
    """Return indices of words that match anchor_text.

    Matching rules (in order):
      1) Exact single-word match
      2) Multi-word phrase match across contiguous words
      3) Substring match within any single word token (last resort)

    This makes the system resilient to PDF tokenization quirks where what the
    user highlights (e.g., "BASIC INFORMATION" or "Basic") may be extracted as
    multiple words or slightly merged tokens.
    """

    if not anchor_text:
        return []

    raw = anchor_text.strip()
    needle = raw if case_sensitive else raw.lower()

    # Tokenize (collapse whitespace) for phrase matching.
    parts = [p for p in (raw.split() if raw else []) if p]
    parts_cmp = parts if case_sensitive else [p.lower() for p in parts]

    hits: List[int] = []

    # 1) Exact single word match.
    if len(parts_cmp) <= 1:
        for i, w in enumerate(words):
            hay = w.text if case_sensitive else w.text.lower()
            if hay == needle:
                hits.append(i)

        # 3) Substring fallback (handles merged tokens like 'BASICINFORMATION').
        if not hits and needle:
            for i, w in enumerate(words):
                hay = w.text if case_sensitive else w.text.lower()
                if needle in hay:
                    hits.append(i)

        return hits

    # 2) Phrase match across contiguous words.
    n = len(parts_cmp)
    for i in range(0, max(0, len(words) - n + 1)):
        ok = True
        for j in range(n):
            wj = words[i + j].text
            hay = wj if case_sensitive else wj.lower()
            if hay != parts_cmp[j]:
                ok = False
                break
        if ok:
            hits.append(i)

    return hits
