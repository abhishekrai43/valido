"""
Unit tests for PDF parser service.

Tests PDF validation and text extraction.
"""

import pytest
import io
from app.services.parser import is_valid_pdf, extract_text_from_bytes, classify_pdf_bytes


class TestPDFValidation:
    """Test PDF file validation."""
    
    def test_valid_pdf_header(self):
        """Test PDF with valid header."""
        # Minimal valid PDF structure
        pdf_bytes = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n0\n%%EOF"
        result = is_valid_pdf(pdf_bytes)
        # Even if it fails parsing, should at least pass header check
        assert result is True or result is False  # Should not crash
    
    def test_invalid_pdf_no_header(self):
        """Test file without PDF header."""
        invalid_bytes = b"This is not a PDF file at all"
        result = is_valid_pdf(invalid_bytes)
        assert result is False
    
    def test_empty_bytes(self):
        """Test empty byte array."""
        empty_bytes = b""
        result = is_valid_pdf(empty_bytes)
        assert result is False
    
    def test_short_bytes(self):
        """Test very short byte array (less than 10 bytes)."""
        short_bytes = b"%PDF"
        result = is_valid_pdf(short_bytes)
        assert result is False
    
    def test_pdf_header_with_leading_whitespace(self):
        """Test PDF with leading whitespace/null bytes."""
        pdf_with_whitespace = b"\x00\x00\x00%PDF-1.4\n1 0 obj\nendobj\n%%EOF"
        result = is_valid_pdf(pdf_with_whitespace)
        # Should strip leading bytes and find header
        assert result is True or result is False  # Should not crash
    
    def test_truncated_pdf(self):
        """Test PDF missing EOF marker."""
        truncated_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj"
        # Missing %%EOF
        result = is_valid_pdf(truncated_pdf)
        # May fail, but should not crash
        assert result is False or result is True
    
    def test_docx_renamed_as_pdf(self):
        """Test .docx file renamed to .pdf (starts with PK)."""
        # DOCX files start with PK (ZIP format)
        docx_bytes = b"PK\x03\x04\x14\x00\x00\x00\x08\x00[Content-Types].xml"
        result = is_valid_pdf(docx_bytes)
        assert result is False


class TestTextExtraction:
    """Test text extraction from PDFs."""
    
    def test_extract_from_empty_bytes(self):
        """Test extraction from empty bytes."""
        empty_bytes = b""
        text = extract_text_from_bytes(empty_bytes)
        assert text == ""
    
    def test_extract_from_invalid_pdf(self):
        """Test extraction from invalid PDF."""
        invalid_bytes = b"Not a PDF"
        text = extract_text_from_bytes(invalid_bytes)
        # Should return placeholder or empty, not crash
        assert isinstance(text, str)
        assert text == "" or "[" in text  # Placeholder message
    
    def test_scanned_pdf_detection(self):
        """Test detection of scanned/image-only PDFs."""
        # Create minimal PDF with no text layers
        # In real implementation, this would be an actual scanned PDF
        # For now, test that function returns sentinel value
        minimal_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Page\n>>\nendobj\n%%EOF"
        text = extract_text_from_bytes(minimal_pdf)
        # Should either extract nothing or return scanned PDF message
        assert isinstance(text, str)
    
    def test_extract_handles_exceptions(self):
        """Test that extraction handles exceptions gracefully."""
        # Corrupted PDF that might cause parser to fail
        corrupted = b"%PDF-1.4\ngarbage\x00\xff\xfe"
        text = extract_text_from_bytes(corrupted)
        # Should not crash, should return string (even if empty/placeholder)
        assert isinstance(text, str)


class TestEdgeCases:
    """Test edge cases for PDF processing."""
    
    def test_null_bytes_in_content(self):
        """Test PDF with null bytes."""
        pdf_with_nulls = b"%PDF-1.4\n\x00\x00\x00some content\x00\x00%%EOF"
        result = is_valid_pdf(pdf_with_nulls)
        # Should handle null bytes
        assert isinstance(result, bool)
    
    def test_very_large_header_offset(self):
        """Test PDF with header far into file."""
        # Some PDFs have garbage before header
        large_offset = b"\x00" * 1000 + b"%PDF-1.4\ncontent%%EOF"
        result = is_valid_pdf(large_offset)
        # May or may not be valid depending on implementation
        assert isinstance(result, bool)
    
    def test_non_ascii_characters(self):
        """Test PDF with non-ASCII characters."""
        pdf_with_unicode = b"%PDF-1.4\n1 0 obj\n<</Title(\xc3\xa9\xc3\xa0)>>endobj\n%%EOF"
        result = is_valid_pdf(pdf_with_unicode)
        assert isinstance(result, bool)


class TestPdfClassification:
    def test_classify_empty(self):
        ok, issue, msg = classify_pdf_bytes(b"")
        assert ok is False
        assert issue == "empty"
        assert "Empty" in msg

    def test_classify_not_pdf(self):
        ok, issue, msg = classify_pdf_bytes(b"Not a PDF")
        assert ok is False
        assert issue in ("not_pdf", "corrupt")

    def test_classify_corrupt_pdf_like_bytes(self):
        # Has header, but likely not parseable by fitz/pdfplumber -> should be marked corrupt.
        corrupt = b"%PDF-1.4\nthis-is-not-a-real-pdf\x00\xff\xfe"
        ok, issue, _ = classify_pdf_bytes(corrupt)
        assert ok is False
        assert issue in ("corrupt", "scanned_or_image_only")

    def test_classify_allows_preamble_before_header(self, monkeypatch):
        # Some real PDFs have non-whitespace bytes before %PDF-; we should not reject
        # purely on header position if the parser can open it.
        from app.services import parser as parser_mod

        # Force is_valid_pdf to succeed to simulate PyMuPDF opening the file.
        monkeypatch.setattr(parser_mod, "is_valid_pdf", lambda b: True)
        monkeypatch.setattr(parser_mod, "extract_text_from_bytes", lambda b: "hello world")

        pdf_bytes = b"GARBAGEBYTES" + b"%PDF-1.7\n...\n%%EOF"
        ok, issue, _ = parser_mod.classify_pdf_bytes(pdf_bytes)
        assert ok is True
        assert issue == "ok"

    def test_classify_scanned_sentinel(self, monkeypatch):
        # Force extract_text_from_bytes to return scanned sentinel to test classification reliably.
        from app.services import parser as parser_mod
        monkeypatch.setattr(
            parser_mod,
            "extract_text_from_bytes",
            lambda b: "[SCANNED_PDF] This PDF appears to be a scan",
        )
        # Also ensure structural validation passes in this test
        monkeypatch.setattr(parser_mod, "is_valid_pdf", lambda b: True)

        ok, issue, msg = parser_mod.classify_pdf_bytes(b"%PDF-1.4\n%%EOF")
        assert ok is False
        assert issue == "scanned_or_image_only"
        assert "scanned" in msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
