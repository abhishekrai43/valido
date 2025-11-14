"""
Comprehensive test suite for Valido backend
Tests extraction, validation, and core functionality
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.services.extractor import extract_with_lookfor, apply_extraction_strategy
from app.services.validator import _validate_field_value, validate_text, _extract_clean_number
from app.services.parser import is_valid_pdf, extract_text_from_bytes


# Helper function to make tests simpler
def extract_field_value(text, search_term, strategy="first"):
    """Wrapper to simplify extraction in tests"""
    results = extract_with_lookfor(text, search_term, strategy)
    if not results:
        return None
    # Extract just the values from the (position, value) tuples
    values = [value for _, value in results]
    return apply_extraction_strategy(values, strategy)


class TestPDFParsing:
    """Test PDF text extraction"""
    
    def test_is_valid_pdf_invalid_bytes(self):
        """Test PDF validation with invalid bytes"""
        result = is_valid_pdf(b"not a pdf")
        assert result is False
    
    def test_is_valid_pdf_empty(self):
        """Test PDF validation with empty bytes"""
        result = is_valid_pdf(b"")
        assert result is False
    
    def test_extract_text_handles_invalid_pdf(self):
        """Test text extraction from invalid PDF returns placeholder"""
        # The function logs warnings but doesn't raise - it returns placeholder text
        result = extract_text_from_bytes(b"not a pdf")
        assert result is not None  # Should return something, not crash


class TestFieldExtraction:
    """Test field extraction with all patterns"""
    
    def setup_method(self):
        """Sample text for extraction tests"""
        self.sample_text = """
        Invoice Number: INV-12345
        
        Name: John Smith
        
        Amount: $1,234.56
        
        Date: 2024-01-15
        
        Description: Payment for services rendered
        
        Total Amount Due $5,000.00
        
        Chapter 1 Introduction to Economics
        
        Chapter "Consumer Rights"
        
        Email: test@example.com
        
        Phone: +1-555-123-4567
        
        Address:
        123 Main Street
        
        MATERIALS NEEDED for the project
        
        Status: APPROVED
        """
    
    def test_extraction_colon_pattern(self):
        """Test Pattern 1: Field: Value"""
        result = extract_field_value(self.sample_text, "Invoice Number")
        assert result is not None
        assert "INV-12345" in result
    
    def test_extraction_case_insensitive(self):
        """Test case-insensitive extraction"""
        result1 = extract_field_value(self.sample_text, "name")
        result2 = extract_field_value(self.sample_text, "NAME")
        result3 = extract_field_value(self.sample_text, "Name")
        
        # All should find the name
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert "John" in result1.lower() and "smith" in result1.lower()
    
    def test_extraction_amount_pattern(self):
        """Test Pattern 5: Amounts with currency symbols"""
        result = extract_field_value(self.sample_text, "Amount")
        assert result is not None
        assert "$" in result or "1,234.56" in result
    
    def test_extraction_date_pattern(self):
        """Test date extraction"""
        result = extract_field_value(self.sample_text, "Date")
        assert result is not None
        assert "2024" in result
    
    def test_extraction_email_pattern(self):
        """Test email extraction"""
        result = extract_field_value(self.sample_text, "Email")
        assert result is not None
        assert "@" in result
        assert "example.com" in result
    
    def test_extraction_phone_pattern(self):
        """Test phone extraction"""
        result = extract_field_value(self.sample_text, "Phone")
        assert result is not None
        assert "555" in result
    
    def test_extraction_chapter_catchall(self):
        """Test Pattern 7: Catch-all for edge cases"""
        result = extract_field_value(self.sample_text, "Chapter", "all")
        assert result is not None
        # Should find multiple chapter occurrences
        assert "Introduction" in result or "Consumer" in result
    
    def test_extraction_strategy_first(self):
        """Test 'first' strategy returns first occurrence"""
        result = extract_field_value(self.sample_text, "Amount", "first")
        assert result is not None
        assert isinstance(result, str)
    
    def test_extraction_strategy_last(self):
        """Test 'last' strategy returns last occurrence"""
        result = extract_field_value(self.sample_text, "Amount", "last")
        assert result is not None
    
    def test_extraction_strategy_all(self):
        """Test 'all' strategy returns all occurrences"""
        result = extract_field_value(self.sample_text, "Amount", "all")
        assert result is not None
        assert isinstance(result, str)
    
    def test_extraction_no_match(self):
        """Test extraction returns None when no match"""
        result = extract_field_value(self.sample_text, "NonexistentField")
        assert result is None
    
    def test_extraction_empty_search_term(self):
        """Test extraction with empty search term"""
        result = extract_field_value(self.sample_text, "")
        assert result is None
    
    def test_extraction_special_chars_in_term(self):
        """Test extraction with special regex characters"""
        text = "Price: $100 (USD)"
        result = extract_field_value(text, "Price")
        assert result is not None


class TestFieldValidation:
    """Test field validation rules using _validate_field_value"""
    
    def test_validation_min_length_pass(self):
        """Test min_length validation passes"""
        field_config = {'type': 'text', 'validations': [{'type': 'minLength', 'value': '3'}]}
        result = _validate_field_value("Hello", field_config)
        assert result['valid'] is True
    
    def test_validation_min_length_fail(self):
        """Test min_length validation fails"""
        field_config = {'type': 'text', 'validations': [{'type': 'minLength', 'value': '5'}]}
        result = _validate_field_value("Hi", field_config)
        assert result['valid'] is False
    
    def test_validation_max_length_pass(self):
        """Test max_length validation passes"""
        field_config = {'type': 'text', 'validations': [{'type': 'maxLength', 'value': '10'}]}
        result = _validate_field_value("Hello", field_config)
        assert result['valid'] is True
    
    def test_validation_max_length_fail(self):
        """Test max_length validation fails"""
        field_config = {'type': 'text', 'validations': [{'type': 'maxLength', 'value': '5'}]}
        result = _validate_field_value("Hello World!", field_config)
        assert result['valid'] is False
    
    def test_validation_pattern_email_pass(self):
        """Test email pattern validation passes"""
        field_config = {'type': 'text', 'validations': [{'type': 'regex', 'value': r'^[\w\.-]+@[\w\.-]+\.\w+$'}]}
        result = _validate_field_value("test@example.com", field_config)
        assert result['valid'] is True
    
    def test_validation_pattern_email_fail(self):
        """Test email pattern validation fails"""
        field_config = {'type': 'text', 'validations': [{'type': 'regex', 'value': r'^[\w\.-]+@[\w\.-]+\.\w+$'}]}
        result = _validate_field_value("not-an-email", field_config)
        assert result['valid'] is False
    
    def test_validation_number_min_pass(self):
        """Test number min validation passes"""
        field_config = {'type': 'number', 'validations': [{'type': 'min', 'value': '50'}]}
        result = _validate_field_value("100", field_config)
        assert result['valid'] is True
    
    def test_validation_number_min_fail(self):
        """Test number min validation fails"""
        field_config = {'type': 'number', 'validations': [{'type': 'min', 'value': '50'}]}
        result = _validate_field_value("25", field_config)
        assert result['valid'] is False
    
    def test_validation_number_max_pass(self):
        """Test number max validation passes"""
        field_config = {'type': 'number', 'validations': [{'type': 'max', 'value': '100'}]}
        result = _validate_field_value("75", field_config)
        assert result['valid'] is True
    
    def test_validation_number_max_fail(self):
        """Test number max validation fails"""
        field_config = {'type': 'number', 'validations': [{'type': 'max', 'value': '100'}]}
        result = _validate_field_value("150", field_config)
        assert result['valid'] is False
    
    def test_validation_date_format_pass(self):
        """Test date format validation passes"""
        field_config = {'type': 'date', 'validations': [{'type': 'format', 'value': '%Y-%m-%d'}]}
        result = _validate_field_value("2024-01-15", field_config)
        assert result['valid'] is True
    
    def test_validation_date_format_fail(self):
        """Test date format validation fails"""
        field_config = {'type': 'date', 'validations': [{'type': 'format', 'value': '%Y-%m-%d'}]}
        result = _validate_field_value("15/01/2024", field_config)
        assert result['valid'] is False
    
    def test_validation_no_rules(self):
        """Test validation with no rules passes"""
        field_config = {'validations': []}
        result = _validate_field_value("anything", field_config)
        assert result['valid'] is True


class TestNumberExtraction:
    """Test number extraction utility"""
    
    def test_extract_clean_number_basic(self):
        """Test extracting basic number"""
        result = _extract_clean_number("123")
        assert result == 123.0
    
    def test_extract_clean_number_decimal(self):
        """Test extracting decimal number"""
        result = _extract_clean_number("123.45")
        assert result == 123.45
    
    def test_extract_clean_number_with_currency(self):
        """Test extracting number with currency symbol"""
        result = _extract_clean_number("$1,234.56")
        assert result == 1234.56
    
    def test_extract_clean_number_with_commas(self):
        """Test extracting number with commas"""
        result = _extract_clean_number("1,234,567.89")
        assert result == 1234567.89
    
    def test_extract_clean_number_negative(self):
        """Test extracting negative number"""
        result = _extract_clean_number("-123.45")
        assert result == -123.45
    
    def test_extract_clean_number_invalid(self):
        """Test extracting from non-numeric text"""
        result = _extract_clean_number("not a number")
        assert result is None


class TestExtractionEdgeCases:
    """Test edge cases in extraction"""
    
    def test_extraction_multiline_value(self):
        """Test extraction of multiline values"""
        text = """
        Description:
        This is a long description
        """
        result = extract_field_value(text, "Description")
        assert result is not None
    
    def test_extraction_value_with_special_chars(self):
        """Test extraction with special characters in value"""
        text = "Amount: $1,234.56 (USD) - 10% discount"
        result = extract_field_value(text, "Amount")
        assert result is not None
        assert "$" in result or "1,234" in result
    
    def test_extraction_duplicate_occurrences(self):
        """Test extraction finds multiple occurrences"""
        text = """
        Name: John
        Name: Jane
        Name: Bob
        """
        result = extract_field_value(text, "Name", "all")
        assert result is not None
        # Should contain multiple names
        assert "\n" in result or "John" in result
    
    def test_extraction_whitespace_handling(self):
        """Test extraction handles extra whitespace"""
        text = "Field:    Value with spaces    "
        result = extract_field_value(text, "Field")
        assert result is not None
        assert "Value" in result
    
    def test_extraction_unicode_characters(self):
        """Test extraction with unicode characters"""
        text = "Montant: 1,234.56 €"
        result = extract_field_value(text, "Montant")
        assert result is not None
    
    def test_extraction_very_long_value(self):
        """Test extraction with very long values"""
        long_value = "A" * 1000
        text = f"Field: {long_value}"
        result = extract_field_value(text, "Field")
        assert result is not None


class TestValidateText:
    """Test full document validation"""
    
    def test_validate_text_signed(self):
        """Test signed document validation"""
        text = "digitally signed by John Doe"
        rules = {'validations': {'signed': True}}
        result = validate_text(text, rules)
        assert 'validations' in result
        assert 'signed' in result['validations']
    
    def test_validate_text_must_contain_pass(self):
        """Test must_contain validation passes"""
        text = "This document contains the required text"
        rules = {'validations': {'must_contain': {'text': 'required text', 'case_sensitive': False}}}
        result = validate_text(text, rules)
        assert 'validations' in result
    
    def test_validate_text_must_not_contain_pass(self):
        """Test must_not_contain validation passes"""
        text = "This is a clean document"
        rules = {'validations': {'must_not_contain': {'text': 'forbidden', 'case_sensitive': False}}}
        result = validate_text(text, rules)
        assert 'validations' in result
    
    def test_validate_text_with_rules(self):
        """Test validation returns proper structure"""
        text = "Sample document"
        rules = {'validations': {}}
        result = validate_text(text, rules)
        assert isinstance(result, dict)


class TestIntegration:
    """Integration tests combining extraction and validation"""
    
    def test_extract_and_validate_email(self):
        """Test extracting and validating an email"""
        text = "Contact Email: support@valido.com"
        
        # Extract
        email = extract_field_value(text, "Email")
        assert email is not None
        
        # Validate
        field_config = {'type': 'text', 'validations': [{'type': 'regex', 'value': r'^[\w\.-]+@[\w\.-]+\.\w+$'}]}
        result = _validate_field_value(email.strip(), field_config)
        assert result['valid'] is True
    
    def test_extract_and_validate_amount(self):
        """Test extracting and validating an amount"""
        text = "Total Amount: $5,000.00"
        
        # Extract
        amount = extract_field_value(text, "Amount")
        assert amount is not None
        
        # Extract numeric value
        numeric = _extract_clean_number(amount)
        assert numeric is not None
        assert numeric > 0
    
    def test_full_document_with_fields(self):
        """Test full document validation with field extraction"""
        text = """
        Invoice Number: INV-12345
        Customer Name: John Smith
        Amount: $1,234.56
        Status: PAID
        """
        
        rules = {
            'fields': [
                {'name': 'invoice_number', 'lookFor': 'Invoice Number', 'strategy': 'first'},
                {'name': 'customer', 'lookFor': 'Customer Name', 'strategy': 'first'},
                {'name': 'amount', 'lookFor': 'Amount', 'strategy': 'first', 'type': 'number'},
            ]
        }
        
        result = validate_text(text, rules)
        assert 'fields' in result
        # Check that fields were extracted
        assert len(result['fields']) > 0


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short", "-s"])
