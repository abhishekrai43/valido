import re

# Test text from the PDF
text = """Date: 21st August 2024
To,
Mr. Abhishek Rai,
Email ID: abhishek.rai8992@gmail.com
Contact No.: +91-9818084139
INR. 21,06,228/- (INR Twenty-One Lakhs
(-) PF Employee ₹ 1,800"""

# Test each pattern
tests = [
    ("Date:", "21st August 2024"),
    ("Email ID:", "abhishek.rai8992@gmail.com"),
    ("INR", "21,06,228/-"),
    ("PF Employee", "₹ 1,800"),
]

patterns = [
    r"{term}[.\s]*[:]\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)",  # Pattern 1a
    r"{term}\s+([A-Z][^\n\r]+?)(?:\s+(?:within|at|in the|on the|by the|with the|from the|to the|as the)\s|\s{{2,}}|\n|$)",  # Pattern 1b
    r"{term}\s*\([A-Z]\)\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)",  # Pattern 2
    r"\([+\-]\)\s*{term}\s+([^\n\r]+?)(?:\s{{2,}}|\n|$)",  # Pattern 3
    r"{term}\s+([+\-₹$€£¥₨]?[A-Za-z0-9₹$€£¥₨,.\/\-\(\)–]+(?:\s+[A-Za-z0-9₹$€£¥₨,.\/\-\(\)–]+)*?)(?:\s{{2,}}|\n|$)",  # Pattern 4
    r"{term}\s*\n+\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)",  # Pattern 5
]

print("=" * 80)
print("PATTERN DEBUG")
print("=" * 80)

for term, expected in tests:
    print(f"\n🔍 Looking for: '{term}' → Expected: '{expected}'")
    escaped_term = re.escape(term)
    found_match = False
    
    for idx, pattern_template in enumerate(patterns, 1):
        pattern = pattern_template.format(term=escaped_term)
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if matches:
            print(f"   ✓ Pattern {idx}: {matches[0]}")
            found_match = True
            break
    
    if not found_match:
        print(f"   ✗ NO MATCH FOUND")
        print(f"   Trying all patterns:")
        for idx, pattern_template in enumerate(patterns, 1):
            pattern = pattern_template.format(term=escaped_term)
            matches = re.findall(pattern, text, re.IGNORECASE)
            print(f"      Pattern {idx}: {matches if matches else 'No match'}")
