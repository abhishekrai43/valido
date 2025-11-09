import re

# Test Email ID pattern
text = "Email ID: abhishek.rai8992@gmail.com\nContact"
look_for = "Email ID:"
escaped = re.escape(look_for)

# Pattern 1a from validator.py
pattern = rf"{escaped}[.\s]*[:]\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)"

print(f"Testing: '{look_for}'")
print(f"Escaped: '{escaped}'")
print(f"Pattern: {pattern}")
print(f"Text: '{text}'")

match = re.search(pattern, text)
if match:
    print(f"✓ MATCHED: '{match.group(1)}'")
else:
    print("✗ NO MATCH")
    
# Try without the [.\s]* part
pattern2 = rf"{escaped}\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)"
match2 = re.search(pattern2, text)
if match2:
    print(f"✓ Pattern2 MATCHED: '{match2.group(1)}'")
