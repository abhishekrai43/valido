"""Parser with PDF validation and text extraction.

Behavior:
- is_valid_pdf: header check + attempt to open with PyMuPDF (if installed).
- extract_text_from_bytes: extracts text via PyMuPDF; detects image-only PDFs and
  returns a clear sentinel. Falls back to pdfminer.six if PyMuPDF extraction fails.
- extract_tables: modular table extraction using TableExtractor service

Small, actionable comments only.
"""

from typing import Tuple, List, Dict, Any, Optional
import io
import os
from app.utils.logger import get_logger
from app.services.table_extractor import TableExtractor

logger = get_logger("ValidoParser")


def is_valid_pdf(pdf_bytes: bytes) -> bool:
    """Return True if bytes look like a PDF and (if PyMuPDF installed) can be opened."""
    if not pdf_bytes or len(pdf_bytes) < 10:
        logger.warning("PDF validation failed: empty or too-short bytes")
        return False

    stripped = pdf_bytes.lstrip(b'\x00\x09\x0a\x0c\x0d\x20')
    if not stripped.startswith(b"%PDF-"):
        logger.warning("PDF validation failed: missing %PDF- header")
        return False

    # optional EOF quick check (helps catch truncated files)
    if b"%%EOF" not in pdf_bytes[-1024:]:
        logger.debug("PDF EOF marker not found within last 1024 bytes; continuing validation")

    try:
        import fitz  # PyMuPDF
        # opening will validate basic structure
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if getattr(doc, "page_count", len(doc)) > 0:
                return True
            logger.warning("PDF validation failed: zero pages")
            return False
    except ImportError:
        logger.info("PyMuPDF not installed — falling back to header-based validation")
        return True
    except Exception as e:
        # unexpected parsing errors -> invalid PDF
        logger.error(f"PDF validation exception: {type(e).__name__}: {e}")
        return False


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract text using hybrid approach: pdfplumber (table-aware) first, then PyMuPDF fallback.
    
    This handles table-structured PDFs better by preserving row/column layout.
    Falls back to PyMuPDF for simple text-only PDFs.
    """
    if not pdf_bytes:
        logger.warning("extract_text_from_bytes: empty input bytes")
        return ""

    # Try pdfplumber first (better for table-structured PDFs)
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            text_chunks = []
            low_text_pages = 0
            
            for i in range(total_pages):
                page = pdf.pages[i]
                
                # Check if page has tables
                tables = page.extract_tables()
                
                if tables:
                    # Table-structured content: convert tables to text format
                    page_text = page.extract_text() or ""
                    
                    # Enhance with structured table data
                    for table_idx, table in enumerate(tables):
                        if table:
                            table_text = f"\n[TABLE_{table_idx + 1}]\n"
                            for row in table:
                                if row:
                                    # Join cells with tab separator for better parsing
                                    table_text += "\t".join([str(cell or "").strip() for cell in row]) + "\n"
                            page_text += table_text
                    
                    text_chunks.append(page_text.strip())
                    if len(page_text.strip()) < 20:
                        low_text_pages += 1
                else:
                    # No tables: use regular text extraction
                    page_text = page.extract_text() or ""
                    text_chunks.append(page_text.strip())
                    if len(page_text.strip()) < 20:
                        low_text_pages += 1
            
            combined = "\n".join([t for t in text_chunks if t]).strip()
            
            # Heuristic: if most pages are low-text, treat as scanned
            low_ratio = (low_text_pages / total_pages) if total_pages > 0 else 1.0
            if not combined or low_ratio > 0.6:
                logger.info("PDF appears to be a scan/image-only (no extractable text)")
                return "[SCANNED_PDF] This PDF appears to be a scan or image. Please use digitally-generated PDFs with selectable text."
            
            if len(combined) >= 20:
                logger.info(f"pdfplumber extraction successful ({len(combined)} chars, {len(tables) if tables else 0} tables detected)")
                return combined
                
    except Exception as e:
        logger.info(f"pdfplumber extraction failed, falling back to PyMuPDF: {type(e).__name__}: {e}")

    # Fallback to PyMuPDF (original extraction method)
    try:
        import fitz  # PyMuPDF
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            total_pages = len(doc)
            # Process all pages - no arbitrary limit for local desktop app
            pages_to_scan = total_pages

            text_chunks = []
            low_text_pages = 0
            for i in range(pages_to_scan):
                page = doc[i]
                raw_text = page.get_text("text")
                if isinstance(raw_text, str):
                    page_text = raw_text.strip()
                else:
                    page_text = str(raw_text).strip() if raw_text is not None else ""
                text_chunks.append(page_text)
                if len(page_text) < 20:
                    low_text_pages += 1

            combined = "\n".join([t for t in text_chunks if t]).strip()

            # Heuristic: if most scanned pages are low-text, treat as scanned
            low_ratio = (low_text_pages / pages_to_scan) if pages_to_scan > 0 else 1.0
            if not combined or low_ratio > 0.6:
                logger.info("PDF appears to be a scan/image-only (no extractable text)")
                return "[SCANNED_PDF] This PDF appears to be a scan or image. Please use digitally-generated PDFs with selectable text."

            # Return combined text (ensure it's long enough)
            if len(combined) >= 20:
                return combined

    except Exception as e:
        logger.warning(f"PyMuPDF extraction failed: {type(e).__name__}: {e}")

    # Fallback to pdfminer.six
    try:
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams

        output = io.StringIO()
        laparams = LAParams()
        extract_text_to_fp(io.BytesIO(pdf_bytes), output, laparams=laparams)
        text = output.getvalue().strip()
        if text and len(text) >= 20:
            return text
        if not text:
            logger.info("pdfminer extracted no text")
    except Exception as e2:
        logger.warning(f"pdfminer extraction failed: {type(e2).__name__}: {e2}")

    logger.warning("No text extracted from PDF; returning placeholder")
    return "[binary-pdf-content-no-text-extracted]"


def extract_table_by_index(pdf_path: str, page_num: int, table_index: int) -> Optional[Dict[str, Any]]:
    """
    Extract a specific table by index from a PDF page.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-based)
        table_index: Table index (1-based, or -1 for last table)
    
    Returns:
        Dictionary with table data and metadata, or None if not found
    """
    try:
        return TableExtractor.extract_single_table(pdf_path, page_num, table_index)
    except Exception as e:
        logger.error(f"Failed to extract table {table_index} from page {page_num}: {str(e)}")
        return None


def extract_all_tables(pdf_path: str, page_num: int) -> List[Dict[str, Any]]:
    """
    Extract all tables from a PDF page.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-based)
    
    Returns:
        List of table dictionaries
    """
    try:
        return TableExtractor.extract_all_tables(pdf_path, page_num)
    except Exception as e:
        logger.error(f"Failed to extract all tables from page {page_num}: {str(e)}")
        return []


def get_table_summary(pdf_path: str) -> Dict[int, int]:
    """
    Get summary of all tables in a PDF.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Dictionary mapping page numbers to table counts
    """
    try:
        return TableExtractor.get_pdf_table_summary(pdf_path)
    except Exception as e:
        logger.error(f"Failed to get table summary: {str(e)}")
        return {}
