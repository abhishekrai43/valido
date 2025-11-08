"""
Unit tests for Valido validator service.

Tests core validation logic: signature detection, date detection,
text matching, and field extraction.
"""

import pytest
from app.services.validator import (
    validate_text,
    _find_date,
    _find_all_dates,
    _find_signature_snippet,
    _match_text_rule,
    _match_not_contain_rule,
    _extract_field,
)


class TestDateDetection:
    """Test date detection across multiple formats."""
    
    def test_iso_format(self):
        """Test ISO 8601 date format (YYYY-MM-DD)."""
        text = "Document dated 2025-11-08 for reference."
        date = _find_date(text)
        assert date is not None
        assert "2025-11-08" in date
    
    def test_us_format(self):
        """Test US date format (MM/DD/YYYY)."""
        text = "Signed on 11/08/2025"
        date = _find_date(text)
        assert date is not None
        assert "11/08/2025" in date
    
    def test_uk_format(self):
        """Test UK date format (DD/MM/YYYY)."""
        text = "Effective from 08/11/2025"
        date = _find_date(text)
        assert date is not None
    
    def test_month_name_format(self):
        """Test full month name format."""
        text = "Executed on November 8, 2025"
        date = _find_date(text)
        assert date is not None
        assert "November" in date or "8" in date
    
    def test_month_abbrev_format(self):
        """Test abbreviated month format."""
        text = "Due date: Nov 8, 2025"
        date = _find_date(text)
        assert date is not None
    
    def test_no_date(self):
        """Test text without any date."""
        text = "This document has no dates whatsoever."
        date = _find_date(text)
        assert date is None
    
    def test_multiple_dates(self):
        """Test finding all dates in text."""
        text = "Signed on 2025-11-08 and effective from January 1, 2026"
        dates = _find_all_dates(text)
        assert len(dates) >= 2


class TestSignatureDetection:
    """Test signature snippet extraction."""
    
    def test_signed_by_pattern(self):
        """Test 'Signed by Name' pattern."""
        text = "This agreement is Signed by John Doe on behalf of company."
        snippet = _find_signature_snippet(text)
        assert snippet is not None
        assert "Signed by" in snippet or "John Doe" in snippet
    
    def test_signature_colon(self):
        """Test 'Signature: Name' pattern."""
        text = "Signature: Jane Smith\nDate: 2025-11-08"
        snippet = _find_signature_snippet(text)
        assert snippet is not None
    
    def test_slash_s_pattern(self):
        """Test '/s/' electronic signature pattern."""
        text = "Accepted and agreed: /s/ Robert Johnson"
        snippet = _find_signature_snippet(text)
        assert snippet is not None
        assert "/s/" in snippet
    
    def test_no_signature(self):
        """Test text without signature."""
        text = "This is a regular document designed by our team."
        snippet = _find_signature_snippet(text)
        # Should not detect "designed" as signature
        if snippet:
            assert "designed" not in snippet.lower() or "signature" in snippet.lower()
    
    def test_false_positive_designed(self):
        """Ensure 'designed' is not detected as 'signed'."""
        text = "This template was designed by our creative team."
        snippet = _find_signature_snippet(text)
        # Should not match "designed"
        assert snippet is None or "designed" not in snippet.lower()


class TestTextMatching:
    """Test custom text matching rules."""
    
    def test_must_contain_present(self):
        """Test must-contain rule when text is present."""
        text = "This is an Invoice for services rendered."
        rule = {"text": "Invoice", "case_sensitive": False}
        result, snippet = _match_text_rule(text, rule)
        assert result == "Yes"
        assert snippet is not None
        assert "Invoice" in snippet or "invoice" in snippet
    
    def test_must_contain_absent(self):
        """Test must-contain rule when text is absent."""
        text = "This is a receipt for payment."
        rule = {"text": "Invoice", "case_sensitive": False}
        result, snippet = _match_text_rule(text, rule)
        assert result == "No"
        assert snippet is None
    
    def test_case_sensitive_match(self):
        """Test case-sensitive matching."""
        text = "This document contains pdf information."
        rule = {"text": "PDF", "case_sensitive": True}
        result, snippet = _match_text_rule(text, rule)
        assert result == "No"  # "pdf" != "PDF"
    
    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        text = "This document contains PDF information."
        rule = {"text": "pdf", "case_sensitive": False}
        result, snippet = _match_text_rule(text, rule)
        assert result == "Yes"
    
    def test_must_not_contain_present(self):
        """Test must-NOT-contain when text is present (should fail)."""
        text = "DRAFT - This is a draft version"
        rule = {"text": "DRAFT", "case_sensitive": False}
        result, snippet = _match_not_contain_rule(text, rule)
        assert result == "Fail"
        assert snippet is not None
    
    def test_must_not_contain_absent(self):
        """Test must-NOT-contain when text is absent (should pass)."""
        text = "Final version of the document"
        rule = {"text": "DRAFT", "case_sensitive": False}
        result, snippet = _match_not_contain_rule(text, rule)
        assert result == "Pass"
        assert snippet is None


class TestFieldExtraction:
    """Test field extraction from text."""
    
    def test_extract_invoice_number(self):
        """Test extracting invoice number."""
        text = "Invoice Number: INV-2025-12345\nTotal: $500.00"
        value = _extract_field(text, "Invoice Number", strategy="first")
        assert value is not None
        assert "INV-2025-12345" in value
    
    def test_extract_amount(self):
        """Test extracting monetary amount."""
        text = "Total Amount: $1,234.56\nPaid in full."
        value = _extract_field(text, "Total Amount", strategy="first")
        assert value is not None
        # Should contain the amount
        assert "1,234.56" in value or "1234.56" in value or "$" in value
    
    def test_extract_po_number(self):
        """Test extracting PO number."""
        text = "PO Number: PO-98765\nShip to: Customer"
        value = _extract_field(text, "PO Number", strategy="first")
        assert value is not None
        assert "PO-98765" in value or "98765" in value
    
    def test_extract_field_not_found(self):
        """Test extraction when field doesn't exist."""
        text = "This is a simple document without the field we're looking for."
        value = _extract_field(text, "Nonexistent Field", strategy="first")
        assert value == ""
    
    def test_extract_last_occurrence(self):
        """Test extracting last occurrence when multiple exist."""
        text = "Amount: $100\nSubtotal: $200\nAmount: $300"
        value = _extract_field(text, "Amount", strategy="last")
        assert value is not None
        # Should get the last occurrence
        assert "300" in value or "$300" in value
    
    def test_extract_all_occurrences(self):
        """Test extracting all occurrences."""
        text = "Item: Apple\nItem: Banana\nItem: Cherry"
        value = _extract_field(text, "Item", strategy="all")
        assert value is not None
        assert " | " in value  # Multiple values separated by |
        assert "Apple" in value
        assert "Banana" in value


class TestValidateTextFunction:
    """Test main validate_text function with various rule combinations."""
    
    def test_signed_validation(self):
        """Test signed validation."""
        text = "This agreement is signed by John Doe on 2025-11-08"
        rules = {"validate_signed": True}
        report = validate_text(text, rules)
        
        assert report is not None
        assert "validations" in report
        # Check that signed was validated
    
    def test_dated_validation(self):
        """Test dated validation."""
        text = "Document executed on November 8, 2025"
        rules = {"validate_dated": True}
        report = validate_text(text, rules)
        
        assert report is not None
        assert "validations" in report
    
    def test_signed_and_dated(self):
        """Test both signed and dated validation."""
        text = "Signed by Jane Smith on 11/08/2025"
        rules = {"validate_signed_and_dated": True}
        report = validate_text(text, rules)
        
        assert report is not None
        assert "validations" in report
    
    def test_custom_fields_extraction(self):
        """Test custom field extraction."""
        text = "Invoice Number: INV-123\nAmount: $500.00\nDate: 2025-11-08"
        rules = {
            "fields": [
                {"name": "Invoice Number", "strategy": "first"},
                {"name": "Amount", "strategy": "first"}
            ]
        }
        report = validate_text(text, rules)
        
        assert report is not None
        assert "extractions" in report
    
    def test_empty_text(self):
        """Test validation with empty text."""
        text = ""
        rules = {"validate_signed": True}
        report = validate_text(text, rules)
        
        # Should not crash, should return report
        assert report is not None
    
    def test_none_rules(self):
        """Test validation with no rules."""
        text = "Some document text"
        rules = None
        report = validate_text(text, rules)
        
        # Should return basic report
        assert report is not None
        assert "summary" in report


class TestEdgeCases:
    """Test edge cases and unusual inputs."""
    
    def test_very_long_text(self):
        """Test with very long text (10000+ characters)."""
        text = "Document content. " * 1000  # ~18000 characters
        date = _find_date(text)
        # Should not crash or timeout
        assert date is None or isinstance(date, str)
    
    def test_special_characters(self):
        """Test with special characters."""
        text = "Amount: $1,234.56 € £ ¥ ₹"
        value = _extract_field(text, "Amount")
        # Should handle currency symbols
        assert value is not None
    
    def test_unicode_text(self):
        """Test with Unicode characters."""
        text = "Café de Paris - Invoice für Herr Müller - Montréal"
        snippet = _find_signature_snippet(text)
        # Should not crash on Unicode
    
    def test_newlines_and_tabs(self):
        """Test with various whitespace."""
        text = "Invoice Number:\t\tINV-123\n\nAmount:\n$500.00"
        value = _extract_field(text, "Invoice Number")
        assert value is not None
    
    def test_malformed_date(self):
        """Test with malformed date."""
        text = "Date: 99/99/9999"
        date = _find_date(text)
        # Should either return None or the malformed date, but not crash
        assert date is None or isinstance(date, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
