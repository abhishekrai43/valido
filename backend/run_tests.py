#!/usr/bin/env python3
"""
Quick start script to run Valido tests
Place your test PDF in the test_docs folder and run this script
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def main():
    print("="*80)
    print(" VALIDO TEST RUNNER")
    print("="*80)
    
    # Check if test PDF exists
    test_docs = backend_dir.parent / "test_docs"
    pdf_path = test_docs / "PSTI_Letter of Intent - Abhishek Rai(verified) (1).pdf"
    
    if not test_docs.exists():
        test_docs.mkdir()
        print(f"\n📁 Created test_docs folder: {test_docs}")
        print(f"   Please place your test PDF there")
        return
    
    if not pdf_path.exists():
        print(f"\n❌ Test PDF not found!")
        print(f"   Expected location: {pdf_path}")
        print(f"\n   Please:")
        print(f"   1. Copy your test PDF to: {test_docs}")
        print(f"   2. Rename it to: PSTI_Letter of Intent - Abhishek Rai(verified) (1).pdf")
        print(f"   OR")
        print(f"   3. Edit the PDF_PATH in test_extraction_scenarios.py")
        return
    
    print(f"\n✓ Test PDF found: {pdf_path.name}")
    print(f"\n🚀 Running test scenarios...\n")
    
    # Run the test scenarios
    from scripts.test_extraction_scenarios import main as run_tests
    run_tests()

if __name__ == "__main__":
    main()
