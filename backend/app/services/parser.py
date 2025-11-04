"""Parser with PDF validation and OCR fallback.

Behavior:
- `is_valid_pdf` performs lightweight PDF validation (header check + attempt to open with PyMuPDF if available).
- `extract_text_from_bytes` first attempts text extraction via PyMuPDF. If the extracted text is empty or very short,
  it falls back to rendering pages and running OCR via `pytesseract`.

Notes:
- This implementation prefers small, actionable comments. Do not add AI icons or long AI-comment blocks.
"""

from typing import Tuple
import io
import shutil
import os
import time


def _has_tesseract() -> bool:
    # Check whether the tesseract binary is available on PATH
    return shutil.which("tesseract") is not None


def is_valid_pdf(pdf_bytes: bytes) -> bool:
    """Quickly validate whether bytes likely represent a PDF.

    Returns True if the PDF header looks correct and (if PyMuPDF is installed)
    the document can be opened.
    """
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
        return False

    try:
        import fitz  # PyMuPDF

        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            return doc.page_count > 0
    except Exception:
        # If PyMuPDF is unavailable or opening fails, accept the header-based check only
        return True


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF; fall back to Tesseract OCR when needed.

    If neither PyMuPDF nor pytesseract are available, this function returns
    a conservative placeholder string so the pipeline remains stable.
    """
    if not pdf_bytes:
        return ""

    # Feature flags / limits (env-driven for local user control)
    OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() in ("1", "true", "yes")
    try:
        MAX_PAGES_PER_PDF = int(os.getenv("MAX_PAGES_PER_PDF", "10"))
    except Exception:
        MAX_PAGES_PER_PDF = 10
    try:
        PAGE_OCR_SLEEP_MS = int(os.getenv("PAGE_OCR_SLEEP_MS", "0"))
    except Exception:
        PAGE_OCR_SLEEP_MS = 0

    text_chunks = []

    # Try PyMuPDF extraction first
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        # Limit pages processed to avoid excessive CPU/memory use on user machines
        total_pages = min(len(doc), MAX_PAGES_PER_PDF if MAX_PAGES_PER_PDF > 0 else len(doc))
        for i in range(total_pages):
            page = doc[i]
            page_text = page.get_text("text") or ""
            text_chunks.append(page_text)

        combined = "\n".join(text_chunks).strip()
        if combined and len(combined) >= 20:
            return combined

        # If extracted text is empty or very short, fall back to OCR if available and enabled
        if OCR_ENABLED and _has_tesseract():
            try:
                from PIL import Image
                import pytesseract

                ocr_texts = []
                # Only OCR up to MAX_PAGES_PER_PDF pages to bound CPU and memory
                for i in range(total_pages):
                    page = doc[i]
                    pix = page.get_pixmap(dpi=200)
                    img_bytes = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_bytes))
                    ocr_page_text = pytesseract.image_to_string(img)
                    ocr_texts.append(ocr_page_text)
                    if PAGE_OCR_SLEEP_MS > 0:
                        time.sleep(PAGE_OCR_SLEEP_MS / 1000.0)

                ocr_combined = "\n".join(ocr_texts).strip()
                if ocr_combined:
                    return ocr_combined
            except Exception:
                # Keep comments short; do not include long AI notes.
                pass

        # If no OCR or OCR failed, return the (possibly short) combined text
        return combined

    except Exception:
        # PyMuPDF not available or failed — try pdfminer.six as a fallback
        try:
            from pdfminer.high_level import extract_text_to_fp
            from pdfminer.layout import LAParams

            output = io.StringIO()
            extract_text_to_fp(io.BytesIO(pdf_bytes), output, laparams=LAParams())
            text = output.getvalue().strip()
            if text:
                return text
        except Exception:
            pass

    # Last resort: return placeholder indicating binary PDF content
    return "[binary-pdf-content-no-text-extracted]"

