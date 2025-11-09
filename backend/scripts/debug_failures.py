import sys
import os
import re

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pdfplumber

# Load the PDF
pdf_path = "D:/Valido/PSTI_Letter of Intent - Abhishek Rai(verified) (1).pdf"
with pdfplumber.open(pdf_path) as pdf:
    all_text = ""
    for page in pdf.pages:
        page_text = page.extract_text() or ""
        all_text += page_text + "\n"

# Test the 3 failing extractions
tests = [
    ("INR", "21,06,228/-"),
    ("PF Employee", "₹ 1,800"),
    ("Email ID:", "abhishek.rai8992@gmail.com"),
]

print("=" * 80)
print("DEBUGGING FAILED EXTRACTIONS")
print("=" * 80)

for look_for, expected in tests:
    print(f"\n🔍 Looking for: '{look_for}' → Expected: '{expected}'")
    
    # Find context
    idx = all_text.find(look_for)
    if idx >= 0:
        context = all_text[max(0, idx-50):idx+150]
        print(f"   Context: ...{context.replace(chr(10), '\\n')[:200]}...")
    else:
        print(f"   ❌ NOT FOUND IN TEXT!")
    
    # Test each pattern
    escaped_term = re.escape(look_for)
    patterns = [
        ("1a", rf"{escaped_term}[.\s]*[:]\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
        ("3", rf"\([+\-]\)\s*{escaped_term}\s+([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
        ("4", rf"{escaped_term}\s+([+\-₹$€£¥₨]?[A-Za-z0-9₹$€£¥₨,.\/\-\(\)–]+(?:\s+[A-Za-z0-9₹$€£¥₨,.\/\-\(\)–]+)*?)(?:\s{{2,}}|\n|$)"),
    ]
    
    found = False
    for name, pattern in patterns:
        matches = list(re.finditer(pattern, all_text, flags=0))
        if matches:
            print(f"   ✓ Pattern {name}: {len(matches)} match(es)")
            m = matches[0]
            value = m.group(1).strip()
            value = re.sub(r"\s{2,}", " ", value)
            value = re.sub(r'[;:]+$', '', value).strip()
            print(f"      First: '{value[:60]}'")
            found = True
            break
    
    if not found:
        print(f"   ❌ NO PATTERNS MATCHED!")

print("\n" + "=" * 80)
print("SPECIFIC CHECKS")
print("=" * 80)

# Check INR specifically
print("\n📍 INR occurrences:")
for m in re.finditer(r'INR[.\s]*', all_text):
    start = m.start()
    context = all_text[start:start+100].replace('\n', '\\n')
    print(f"   Position {start}: {context[:80]}")

# Check Email ID specifically  
print("\n📍 Email ID occurrences:")
for m in re.finditer(r'Email ID[.\s]*[:]\s*', all_text, re.IGNORECASE):
    start = m.start()
    context = all_text[start:start+80].replace('\n', '\\n')
    print(f"   Position {start}: {context}")

# Check PF Employee
print("\n📍 PF Employee occurrences:")
for m in re.finditer(r'PF Employee', all_text, re.IGNORECASE):
    start = max(0, m.start() - 10)
    end = m.end() + 50
    context = all_text[start:end].replace('\n', '\\n')
    print(f"   Position {m.start()}: ...{context}")
