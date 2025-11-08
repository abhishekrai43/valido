"""
Test script for AI rule generation feature.
Tests the OpenAI integration with actual API calls.
"""
import os
import sys
import json
from pathlib import Path

# Add parent directory to path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from app.routes.ai_stub import generate_ruleset_from_prompt


def test_simple_validation():
    """Test a simple validation prompt."""
    print("=" * 80)
    print("TEST 1: Simple Document Validation")
    print("=" * 80)
    
    prompt = "Check if the document is signed and contains a date"
    print(f"\nPrompt: {prompt}\n")
    
    # Load API key from .env
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Try loading from .env file
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith("OPENAI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
    
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found in environment or .env file")
        return False
    
    print(f"[OK] API key loaded (first 10 chars): {api_key[:10]}...\n")
    
    try:
        client = OpenAI(api_key=api_key)
        result = generate_ruleset_from_prompt(prompt, client)
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            print(f"   Detail: {result.get('detail', 'N/A')}")
            return False
        
        print("✅ SUCCESS! Generated ruleset:")
        print(json.dumps(result, indent=2))
        
        # Validate structure
        assert "name" in result, "Missing 'name' field"
        assert "source_text" in result, "Missing 'source_text' field"
        assert "extractions" in result, "Missing 'extractions' field"
        assert "validations" in result, "Missing 'validations' field"
        
        print("\n✅ Structure validation passed")
        return True
        
    except Exception as e:
        print(f"❌ EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complex_extraction():
    """Test a complex extraction and validation prompt."""
    print("\n" + "=" * 80)
    print("TEST 2: Complex Extraction and Numeric Validation")
    print("=" * 80)
    
    prompt = """
    Extract student name, GPA, and graduation date from a report card.
    Validate that:
    1. GPA must be greater than 3.0
    2. Document must contain the word "Accredited"
    3. Must be dated in 2024
    """
    print(f"\nPrompt: {prompt}\n")
    
    # Load API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith("OPENAI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
    
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        result = generate_ruleset_from_prompt(prompt, client)
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            print(f"   Detail: {result.get('detail', 'N/A')}")
            return False
        
        print("✅ SUCCESS! Generated ruleset:")
        print(json.dumps(result, indent=2))
        
        # Validate structure
        assert len(result["extractions"]) >= 3, f"Expected at least 3 extractions, got {len(result['extractions'])}"
        assert len(result["validations"]) >= 3, f"Expected at least 3 validations, got {len(result['validations'])}"
        
        # Check for numeric aggregation
        has_numeric = any(v.get("type") == "numeric_aggregation" for v in result["validations"])
        assert has_numeric, "Expected at least one numeric_aggregation validation"
        
        print("\n✅ Structure validation passed")
        print(f"   - {len(result['extractions'])} extraction rules")
        print(f"   - {len(result['validations'])} validation rules")
        return True
        
    except Exception as e:
        print(f"❌ EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_invoice_validation():
    """Test invoice validation use case."""
    print("\n" + "=" * 80)
    print("TEST 3: Invoice Validation Use Case")
    print("=" * 80)
    
    prompt = """
    Validate an invoice document:
    - Extract invoice number, date, total amount
    - Check that invoice is marked as "PAID"
    - Verify total amount is present and greater than $0
    """
    print(f"\nPrompt: {prompt}\n")
    
    # Load API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith("OPENAI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
    
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        result = generate_ruleset_from_prompt(prompt, client)
        
        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            print(f"   Detail: {result.get('detail', 'N/A')}")
            return False
        
        print("✅ SUCCESS! Generated ruleset:")
        print(json.dumps(result, indent=2))
        
        # Check for "PAID" text validation
        has_paid_check = any(
            v.get("type") in ["contains_text", "not_contains_text"] 
            and "PAID" in str(v.get("text", "")).upper()
            for v in result["validations"]
        )
        print(f"\n{'✅' if has_paid_check else '⚠️'} Found PAID status check: {has_paid_check}")
        
        return True
        
    except Exception as e:
        print(f"❌ EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("AI RULE GENERATION FEATURE TEST SUITE")
    print("=" * 80)
    print("Testing OpenAI integration for natural language → JSON rules conversion")
    print("=" * 80)
    
    results = []
    
    # Test 1: Simple validation
    results.append(("Simple Validation", test_simple_validation()))
    
    # Test 2: Complex extraction
    results.append(("Complex Extraction", test_complex_extraction()))
    
    # Test 3: Invoice use case
    results.append(("Invoice Validation", test_invoice_validation()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed*100//total}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! AI feature is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
