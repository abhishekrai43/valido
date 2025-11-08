"""
__init__.py for tests package.

This file makes the tests directory a Python package.
Add test fixtures and utilities here that are shared across test modules.
"""

import pytest
import os
import sys

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def sample_pdf_text():
    """Sample PDF text for testing."""
    return """
    INVOICE
    
    Invoice Number: INV-2025-12345
    Date: November 8, 2025
    
    Bill To:
    Acme Corporation
    123 Main Street
    Anytown, ST 12345
    
    Description                 Amount
    Professional Services       $1,500.00
    Consulting                  $2,500.00
    
    Subtotal:                   $4,000.00
    Tax (10%):                  $400.00
    Total Amount:               $4,400.00
    
    Payment Terms: Net 30
    Due Date: December 8, 2025
    
    Authorized Signature
    Signed by: John Smith
    Date: 11/08/2025
    
    Thank you for your business!
    """


@pytest.fixture
def sample_contract_text():
    """Sample contract text for testing."""
    return """
    SERVICE AGREEMENT
    
    This Agreement is entered into on the 8th day of November, 2025
    
    BETWEEN:
    Company A ("Provider")
    AND:
    Company B ("Client")
    
    1. TERMS OF SERVICE
    The Provider agrees to provide consulting services to the Client
    for a period of 12 months starting January 1, 2026.
    
    2. COMPENSATION
    The Client shall pay $10,000 per month for services rendered.
    
    3. TERMINATION
    Either party may terminate this agreement with 30 days written notice.
    
    4. SIGNATURES
    
    Provider:
    /s/ Jane Doe
    Jane Doe, CEO
    Date: November 8, 2025
    
    Client:
    Signed by: Robert Johnson
    Title: CFO
    Date: 11/08/2025
    
    This agreement is binding upon both parties.
    """


@pytest.fixture
def sample_unsigned_text():
    """Sample unsigned document text."""
    return """
    DRAFT PROPOSAL
    
    Project: Website Redesign
    Estimated Cost: $25,000
    Timeline: 3 months
    
    This is a preliminary proposal and is not yet finalized.
    Please review and provide feedback.
    
    Prepared by: Design Team
    Date: November 2025
    
    NOT FOR SIGNATURE - DRAFT ONLY
    """


@pytest.fixture
def sample_rules_signed_dated():
    """Sample rules requiring signature and date."""
    return {
        "validate_signed": True,
        "validate_dated": True
    }


@pytest.fixture
def sample_rules_custom_fields():
    """Sample rules with custom field extraction."""
    return {
        "fields": [
            {"name": "Invoice Number", "strategy": "first"},
            {"name": "Total Amount", "strategy": "first"},
            {"name": "Date", "strategy": "first"}
        ]
    }


@pytest.fixture
def sample_rules_must_contain():
    """Sample rules with must-contain validation."""
    return {
        "validations": {
            "must_contain": {
                "text": "Invoice",
                "case_sensitive": False
            }
        }
    }


@pytest.fixture
def sample_rules_must_not_contain():
    """Sample rules with must-NOT-contain validation."""
    return {
        "validations": {
            "must_not_contain": {
                "text": "DRAFT",
                "case_sensitive": False
            }
        }
    }


# Test data helpers
def get_test_data_path():
    """Get path to test data directory."""
    return os.path.join(os.path.dirname(__file__), 'test_data')


def ensure_test_data_dir():
    """Ensure test data directory exists."""
    path = get_test_data_path()
    os.makedirs(path, exist_ok=True)
    return path
