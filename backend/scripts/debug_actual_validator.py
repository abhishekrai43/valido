import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Force reload to get latest code
import importlib
if 'app.services.validator' in sys.modules:
    importlib.reload(sys.modules['app.services.validator'])

from app.services.validator import _extract_field
import pdfplumber

# Load the actual PDF
pdf_path = "D:/Valido/PSTI_Letter of Intent - Abhishek Rai(verified) (1).pdf"
with pdfplumber.open(pdf_path) as pdf:
    all_text = ""
    for page in pdf.pages:
        page_text = page.extract_text() or ""
        all_text += page_text + "\n"

# Test each failing extraction
tests = [
    ("Annual CTC", "INR", "21,06,228/-"),
    ("Letter Date", "Date:", "21st August 2024"),
    ("PF Employee", "PF Employee", "₹ 1,800"),
    ("Email", "Email ID:", "abhishek.rai8992@gmail.com"),
]

print("=" * 80)
print("ACTUAL VALIDATOR DEBUG")
print("=" * 80)

for field_name, look_for, expected in tests:
    result = _extract_field(all_text, field_name, look_for, "first")
    status = "✓" if result == expected else "✗"
    print(f"\n{status} {field_name}:")
    print(f"   Look for: '{look_for}'")
    print(f"   Expected: '{expected}'")
    print(f"   Got:      '{result}'")
    
    if result != expected:
        # Show context around the lookFor text
        import re
        escaped = re.escape(look_for)
        match = re.search(rf".{{0,50}}{escaped}.{{0,100}}", all_text, re.IGNORECASE)
        if match:
            context = match.group(0).replace('\n', '\\n')
            print(f"   Context:  '...{context}...'")
        else:
            print(f"   Context:  '{look_for}' not found in text!")
