import PyPDF2
import re

pdf_path = r"D:\Valido\CLass XI Humanities (3).pdf"

with open(pdf_path, 'rb') as f:
    reader = PyPDF2.PdfReader(f)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text()

search_term = "Chapter"
escaped_term = re.escape(search_term)

patterns = [
    (1, rf"{escaped_term}[.\s]*[:]\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
    (2, rf"{escaped_term}\s+([A-Z][^\n\r]+?)(?:\s+(?:within|at|in the|on the|by the|with the|from the|to the|as the|is|are)\s|\s{{2,}}|\n|$)"),
    (3, rf"{escaped_term}\s*\([A-Za-z0-9]\)\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
    (4, rf"\([+\-]\)\s*{escaped_term}\s+([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
    (5, rf"{escaped_term}\s+([+\-₹$€£¥₨]?[\w₹$€£¥₨,.\/\-\(\)@–]+(?:\s+[\w₹$€£¥₨,.\/\-\(\)@–]+)*?)(?:\s{{2,}}|\n|\.\s+[A-Z]|$)"),
    (6, rf"{escaped_term}\s*\n+\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)"),
    (7, rf"{escaped_term}\s+(.+?)(?:\n|$)"),  # CATCH-ALL
]

print("=" * 80)
print(f"Testing extraction patterns for 'Chapter'")
print("=" * 80)

all_extracted = []
for idx, pat in patterns:
    matches = list(re.finditer(pat, full_text, flags=re.IGNORECASE))
    if matches:
        print(f"\nPattern {idx}: Found {len(matches)} matches")
        for m in matches:
            value = m.group(1).strip()[:60]
            if m.start() not in [pos for pos, _ in all_extracted]:
                all_extracted.append((m.start(), value))
                print(f"  NEW at {m.start()}: {repr(value)}")

print(f"\n{'=' * 80}")
print(f"TOTAL UNIQUE EXTRACTIONS: {len(all_extracted)}")
print(f"Expected: 5 (all Chapter occurrences)")
print(f"{'=' * 80}")
