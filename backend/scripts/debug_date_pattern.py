import sys
import os
import re

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pdfplumber

# Load the actual PDF
pdf_path = "D:/Valido/PSTI_Letter of Intent - Abhishek Rai(verified) (1).pdf"
with pdfplumber.open(pdf_path) as pdf:
    all_text = ""
    for page in pdf.pages:
        page_text = page.extract_text() or ""
        all_text += page_text + "\n"

# Test "Date:" specifically
look_for = "Date:"
escaped_term = re.escape(look_for)

patterns = [
    ("1a", rf"{escaped_term}[.\s]*[:]\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
    ("1b", rf"{escaped_term}\s+([A-Z][^\n\r]+?)(?:\s+(?:within|at|in the|on the|by the|with the|from the|to the|as the)\s|\s{{2,}}|\n|$)"),
    ("2", rf"{escaped_term}\s*\([A-Z]\)\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
    ("3", rf"\([+\-]\)\s*{escaped_term}\s+([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
    ("4", rf"{escaped_term}\s+([+\-₹$€£¥₨]?[A-Za-z0-9₹$€£¥₨,.\/\-\(\)–]+(?:\s+[A-Za-z0-9₹$€£¥₨,.\/\-\(\)–]+)*?)(?:\s{{2,}}|\n|$)"),
    ("5", rf"{escaped_term}\s*\n+\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
]

print("=" * 80)
print(f"DETAILED PATTERN MATCHING DEBUG FOR: '{look_for}'")
print("=" * 80)

all_matches = []

for name, pattern in patterns:
    matches = list(re.finditer(pattern, all_text, flags=0))  # No IGNORECASE
    if matches:
        print(f"\nPattern {name}: Found {len(matches)} match(es)")
        for idx, match in enumerate(matches[:3], 1):
            value = match.group(1).strip()
            # Clean up
            value = re.sub(r"\s{2,}", " ", value)
            value = re.sub(r'[;:]+$', '', value).strip()
            
            # Get context
            start = max(0, match.start() - 30)
            end = min(len(all_text), match.end() + 30)
            context = all_text[start:end].replace('\n', '\\n')
            
            print(f"   Match {idx} at index {match.start()}: '{value[:60]}'")
            print(f"   Context: ...{context}...")
            
            all_matches.append((match.start(), name, value))

# Sort by position
all_matches.sort(key=lambda x: x[0])

print("\n" + "=" * 80)
print("ALL MATCHES SORTED BY POSITION:")
print("=" * 80)
for pos, pattern_name, value in all_matches[:10]:
    print(f"Index {pos:5d} | Pattern {pattern_name:3s} | Value: {value[:60]}")

print("\n" + "=" * 80)
print(f"FIRST MATCH (strategy='first'): {all_matches[0][2] if all_matches else 'NONE'}")
print("=" * 80)
