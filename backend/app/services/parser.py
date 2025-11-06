"""Parser with PDF validation and text extraction.

Behavior:
- `is_valid_pdf` performs lightweight PDF validation (header check + attempt to open with PyMuPDF if available).
- `extract_text_from_bytes` extracts text via PyMuPDF. If the extracted text is empty or very short,
  it returns a message indicating the PDF is likely a scanned image.

Notes:
- OCR is disabled by default due to reliability and performance concerns.
- This implementation prefers small, actionable comments. Do not add AI icons or long AI-comment blocks.
"""


from typing import Tuple
import io
import os
from app.utils.logger import get_logger

logger = get_logger("ValidoParser")


def is_valid_pdf(pdf_bytes: bytes) -> bool:
    """Quickly validate whether bytes likely represent a PDF.

    Returns True if the PDF header looks correct and (if PyMuPDF is installed)
    the document can be opened.
    """
    if not pdf_bytes or len(pdf_bytes) < 10:
        logger.warning("PDF validation failed: empty or too short bytes")
        return False

    # Strip leading whitespace/newlines and check for PDF header
    stripped = pdf_bytes.lstrip(b'\x00\x09\x0a\x0c\x0d\x20')
    if not stripped.startswith(b"%PDF-"):
        logger.warning("PDF validation failed: missing %PDF- header")
        return False

    try:
        import fitz  # PyMuPDF
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if doc.page_count > 0:
                return True
            else:
                logger.warning("PDF validation failed: zero pages")
                return False
    except ImportError:
        logger.info("PyMuPDF not installed, using header-based PDF validation")
        return True
    except Exception as e:
        logger.error(f"PDF validation exception: {type(e).__name__}: {e}")
        return True


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF.

    If no extractable text is found (scanned PDFs), returns a message indicating
    the PDF is likely a scanned image.
    """
    if not pdf_bytes:
        logger.warning("extract_text_from_bytes: empty input bytes")
        return ""

    try:
        MAX_PAGES_PER_PDF = int(os.getenv("MAX_PAGES_PER_PDF", "10"))
    except Exception:
        MAX_PAGES_PER_PDF = 10

    text_chunks = []

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = min(len(doc), MAX_PAGES_PER_PDF if MAX_PAGES_PER_PDF > 0 else len(doc))
        for i in range(total_pages):
            page = doc[i]
            page_text = page.get_text("text") or ""
            text_chunks.append(page_text)
        combined = "\n".join(text_chunks).strip()
        if combined and len(combined) >= 20:
            return combined
        if not combined or len(combined) < 20:
            logger.info("PDF appears to be a scan or image (no extractable text)")
            return "[SCANNED_PDF] This PDF appears to be a scan or image. Please use digitally-generated PDFs with selectable text."
        return combined
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {type(e).__name__}: {e}")
        try:
            from pdfminer.high_level import extract_text_to_fp
            from pdfminer.layout import LAParams
            output = io.StringIO()
            extract_text_to_fp(io.BytesIO(pdf_bytes), output, laparams=LAParams())
            text = output.getvalue().strip()
            if text:
                return text
        except Exception as e2:
            logger.error(f"pdfminer.six extraction failed: {type(e2).__name__}: {e2}")
    logger.warning("No text extracted from PDF; returning placeholder")
    return "[binary-pdf-content-no-text-extracted]"

