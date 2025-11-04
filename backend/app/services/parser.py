"""Parser stub: responsible for extracting text and metadata from PDF bytes.

This file intentionally contains a small, safe stub implementation. Replace
with real extraction (pdfminer / PyMuPDF / Tesseract) in a later phase.
"""

def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Return extracted text from PDF bytes.

    Current stub returns a placeholder when empty and attempts a naive
    decode fallback to preserve structure of the pipeline.
    """
    if not pdf_bytes:
        return ""

    # Naive heuristic: try utf-8 decode for embedded text, otherwise return placeholder
    try:
        text = pdf_bytes.decode("utf-8")
        # If decoded text is short, return placeholder indicating binary PDF content.
        if len(text.strip()) < 20:
            return "[binary-pdf-content]"
        return text
    except Exception:
        return "[binary-pdf-content]"
