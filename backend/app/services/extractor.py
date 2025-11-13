"""
Field Extraction Strategies Module

Handles different extraction strategies for pulling data from PDF text:
- Standard pattern matching (look_for)
- Between markers extraction
- Multi-column table handling
"""

import re
from typing import List, Optional, Tuple


def extract_between_markers(
    text: str,
    start_marker: str,
    end_marker: str,
    strategy: str = "first"
) -> str:
    """
    Extract text found between two markers.
    
    Args:
        text: Full document text
        start_marker: Starting marker text (e.g., "Total Amount:", "Invoice #")
        end_marker: Ending marker text (e.g., "USD", "Tax:", "[newline]")
        strategy: "first", "last", or "all" for multiple matches
    
    Returns:
        Extracted text between markers as string.
        For "all" strategy, returns multiple matches joined by " | "
    
    Examples:
        Text: "Invoice #12345 Date: 2024-01-15"
        start_marker="Invoice #", end_marker=" Date" → "12345"
        
        Text: "Total: $1,500.00 USD Payment due"
        start_marker="Total:", end_marker="USD" → "$1,500.00"
        
        Text: "Name: John Doe\nAddress: 123 Main St"
        start_marker="Name:", end_marker="[newline]" → "John Doe"
    """
    if not text or not start_marker or not end_marker:
        return ""
    
    # Handle special marker [newline]
    end_marker_pattern = r'\n' if end_marker == '[newline]' else re.escape(end_marker)
    start_marker_pattern = re.escape(start_marker)
    
    # Build regex pattern to capture text between markers
    # Pattern: start_marker + optional whitespace + (captured text) + optional whitespace + end_marker
    pattern = rf"{start_marker_pattern}\s*(.*?)\s*{end_marker_pattern}"
    
    # Debug logging
    from app.utils.logger import get_logger
    logger = get_logger('extractor')
    logger.debug(f"Between extraction - start_marker: '{start_marker}', end_marker: '{end_marker}'")
    logger.debug(f"Pattern: {pattern}")
    
    # Check if markers exist in text
    start_found = start_marker in text
    end_found = end_marker in text
    logger.debug(f"Start marker found in text: {start_found}")
    logger.debug(f"End marker found in text: {end_found}")
    
    if not start_found:
        logger.warning(f"Start marker '{start_marker}' not found in text")
    if not end_found:
        logger.warning(f"End marker '{end_marker}' not found in text")
    
    logger.debug(f"Text sample (first 500 chars): {text[:500]}")
    
    try:
        matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        
        logger.debug(f"Raw matches found: {len(matches)}")
        if matches:
            logger.debug(f"First match: '{matches[0][:100] if matches[0] else 'empty'}'")
        
        if not matches:
            return ""
        
        # Clean up matches (strip extra whitespace, normalize line breaks)
        cleaned_matches = []
        for match in matches:
            cleaned = match.strip()
            # Replace multiple whitespaces/newlines with single space
            cleaned = re.sub(r'\s+', ' ', cleaned)
            if cleaned:
                cleaned_matches.append(cleaned)
        
        if not cleaned_matches:
            return ""
        
        # Apply strategy
        if strategy == "last":
            return cleaned_matches[-1]
        elif strategy == "all":
            # Use newline separator for Excel-friendly display
            return "\n".join(cleaned_matches)
        else:  # "first"
            return cleaned_matches[0]
            
    except re.error as e:
        # Log regex error but don't crash
        return ""


def extract_with_lookfor(
    text: str,
    search_term: str,
    strategy: str = "first"
) -> List[Tuple[int, str]]:
    """
    Extract field values using look_for patterns.
    Returns list of (position, value) tuples sorted by position.
    
    Args:
        text: Full document text
        search_term: Text to search for
        strategy: Extraction strategy (used by caller for filtering)
    
    Returns:
        List of (position, value) tuples
    """
    if not text or not search_term:
        return []
    
    # Escape special regex characters in the search term
    escaped_term = re.escape(search_term)
    
    # Check if search_term already ends with colon
    has_colon = search_term.rstrip().endswith(':')
    
    patterns = [
        # Pattern 1a: "SearchTerm: value" or "SearchTerm value" - UNIVERSAL colon-separated pattern
        rf"{escaped_term}\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)" if has_colon else rf"{escaped_term}[.\s]*[:]\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)",
        
        # Pattern 1b: "SearchTerm value" - for descriptive phrases (no colon)
        rf"{escaped_term}\s+([A-Z][^\n\r]+?)(?:\s+(?:within|at|in the|on the|by the|with the|from the|to the|as the|is|are)\s|\s{{2,}}|\n|$)",
        
        # Pattern 2: "SearchTerm (X) value" - handles parenthetical markers
        rf"{escaped_term}\s*\([A-Za-z0-9]\)\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)",
        
        # Pattern 3: "(-) SearchTerm value" or "(+) SearchTerm value" - prefix operators
        rf"\([+\-]\)\s*{escaped_term}\s+([^\n\r]+?)(?:\s{{2,}}|\n|$)",
        
        # Pattern 4: "SearchTerm value" - UNIVERSAL number/word capture
        rf"{escaped_term}\s+([+\-₹$€£¥₨]?[\w₹$€£¥₨,.\/\-\(\)@–]+(?:\s+[\w₹$€£¥₨,.\/\-\(\)@–]+)*?)(?:\s{{2,}}|\n|\.\s+[A-Z]|$)",
        
        # Pattern 5: "SearchTerm" on one line, value on next line
        rf"{escaped_term}\s*\n+\s*([^\n\r]+?)(?:\s{{2,}}|\n|$)",
    ]
    
    # Collect all matches with their positions
    match_list: List[Tuple[int, str]] = []
    seen_positions = set()  # Track positions to avoid same match from multiple patterns
    
    for pat in patterns:
        try:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                # Skip if we already captured this position
                if m.start() in seen_positions:
                    continue
                    
                v = m.group(1).strip()
                # Clean up extra whitespace
                v = re.sub(r"\s{2,}", " ", v)
                # Remove ONLY trailing colons/semicolons (not commas)
                v = re.sub(r'[;:]+$', '', v).strip()
                if v and len(v) > 0:
                    # Store position and value - keep all occurrences including duplicates
                    match_list.append((m.start(), v))
                    seen_positions.add(m.start())
        except re.error:
            continue
    
    # Sort by position to get document order
    match_list.sort(key=lambda x: x[0])
    return match_list


def apply_extraction_strategy(
    matches: List[str],
    strategy: str = "first"
) -> str:
    """
    Apply extraction strategy to list of matches.
    
    Args:
        matches: List of extracted values
        strategy: "first", "last", or "all"
    
    Returns:
        Selected value(s) as string. For "all", returns newline-separated values for Excel compatibility.
    """
    if not matches:
        return ""
    
    if strategy == "last":
        return matches[-1]
    elif strategy == "all":
        # Use newline separator for Excel-friendly display
        return "\n".join(matches)
    else:  # "first"
        return matches[0]


def extract_column_from_value(
    value: str,
    column: Optional[str] = None
) -> str:
    """
    Extract specific column from multi-column table value.
    
    Args:
        value: Value string potentially containing multiple columns
        column: Column selector:
            - "first", "last", "all": Position-based selection
            - "1", "2", "3": 1-based index
            - Column name: Match by header (not yet implemented)
            - None: Return all columns
    
    Returns:
        Selected column value(s)
    
    Examples:
        value="₹ 1,800  ₹ 21,600", column="first" → "₹ 1,800"
        value="₹ 1,800  ₹ 21,600", column="2" → "₹ 21,600"
        value="₹ 1,800  ₹ 21,600", column="all" → "₹ 1,800 | ₹ 21,600"
    """
    if not column or not value:
        return value
    
    # Split by multiple spaces (table column separator)
    columns = re.split(r'\s{2,}', value.strip())
    
    if len(columns) <= 1:
        # Not a multi-column value, return as-is
        return value
    
    # Handle column selection
    if column == "first":
        return columns[0]
    elif column == "last":
        return columns[-1]
    elif column == "all":
        return " | ".join(columns)
    elif column.isdigit():
        # 1-based index
        idx = int(column) - 1
        if 0 <= idx < len(columns):
            return columns[idx]
        return columns[0]  # Fallback to first
    else:
        # Column name matching (not yet implemented)
        # TODO: Implement header detection
        return columns[0]
