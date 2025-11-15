"""
Field Extraction Strategies Module

Handles different extraction strategies for pulling data from PDF text:
- Standard pattern matching (look_for)
- Between markers extraction
- Multi-column table handling
"""

import re
from typing import List, Optional, Tuple
from app.utils.logger import get_logger

logger = get_logger("ValidoExtractor")


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
        
        # Pattern 6: CATCH-ALL - "SearchTerm" followed by ANY non-empty content (more permissive)
        # This catches edge cases like: 'Chapter "Something"', 'Chapter 2 Text', etc.
        rf"{escaped_term}\s+(.+?)(?:\n|$)",
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
    column: Optional[str] = None,
    full_text: Optional[str] = None
) -> str:
    """
    Extract specific column from multi-column table value.
    
    Args:
        value: Value string potentially containing multiple columns  
        column: Column selector:
            - "first", "last", "all": Position-based selection
            - "1", "2", "3": 1-based index
            - Column name: Searches for column in table headers to determine position
            - None: Return all columns
        full_text: Full document text to search for table headers (optional but recommended)
    
    Returns:
        Selected column value(s)
    
    Examples:
        value="Basic  ₹ 1,800  ₹ 21,600", column="first" → "Basic"
        value="Basic  ₹ 1,800  ₹ 21,600", column="2" → "₹ 1,800"
        value="Basic  ₹ 1,800  ₹ 21,600", column="Per Month", full_text="..." → "₹ 1,800" (searches headers)
    """
    logger.info(f"DEBUG extract_column_from_value: value='{value}', column='{column}'")
    
    if not column or not value:
        logger.info(f"DEBUG extract_column_from_value: Returning original value (no column/value)")
        return value
    
    # Split by multiple spaces (table column separator)
    # Try different splitting strategies in order of preference:
    
    # Strategy 1: Split by 2+ spaces (standard table format)
    columns = re.split(r'\s{2,}', value.strip())
    logger.info(f"DEBUG extract_column_from_value: Strategy 1 (2+ spaces) - columns: {columns}")
    
    # Strategy 2: If only 1 column, try splitting by single space between distinct values
    # (handles cases where values are separated by just one space)
    if len(columns) <= 1:
        # Split by single space but merge currency symbols with their values
        parts = value.strip().split()
        columns = []
        i = 0
        while i < len(parts):
            # If this part is a currency symbol, merge it with the next part
            if parts[i] in ['₹', '$', '€', '£', '¥', '₨'] and i + 1 < len(parts):
                columns.append(parts[i] + ' ' + parts[i + 1])
                i += 2
            else:
                columns.append(parts[i])
                i += 1
        logger.info(f"DEBUG extract_column_from_value: Strategy 2 (single space with currency merge) - columns: {columns}")
    
    if len(columns) <= 1:
        # Not a multi-column value, return as-is
        logger.info(f"DEBUG extract_column_from_value: Only 1 column, returning as-is")
        return value
    
    # Handle column selection
    column_lower = column.lower().strip()
    
    logger.info(f"DEBUG extract_column_from_value: column_lower='{column_lower}'")
    
    if column_lower == "first":
        logger.info(f"DEBUG extract_column_from_value: Returning first column: {columns[0]}")
        return columns[0]
    elif column_lower == "last":
        logger.info(f"DEBUG extract_column_from_value: Returning last column: {columns[-1]}")
        return columns[-1]
    elif column_lower == "all":
        result = " | ".join(columns)
        logger.info(f"DEBUG extract_column_from_value: Returning all columns: {result}")
        return result
    elif column.isdigit():
        # 1-based index
        idx = int(column) - 1
        logger.info(f"DEBUG extract_column_from_value: Numeric column '{column}', using index {idx}")
        if 0 <= idx < len(columns):
            logger.info(f"DEBUG extract_column_from_value: Returning column at index {idx}: {columns[idx]}")
            return columns[idx]
        logger.info(f"DEBUG extract_column_from_value: Index out of range, returning first column: {columns[0]}")
        return columns[0]  # Fallback to first
    else:
        # Column name matching - try to find actual column position from table headers
        logger.info(f"DEBUG extract_column_from_value: Column name specified, len(columns)={len(columns)}")
        
        # First, try to find the column in structured table headers if full_text is provided
        column_index = None
        if full_text and '[TABLE_' in full_text:
            logger.info(f"DEBUG extract_column_from_value: Searching for column '{column}' in table headers")
            # Find table sections
            table_pattern = r'\[TABLE_\d+\](.*?)(?=\[TABLE_\d+\]|$)'
            tables = re.findall(table_pattern, full_text, re.DOTALL)
            
            for table in tables:
                lines = table.strip().split('\n')
                if lines:
                    # First line is usually the header
                    header = lines[0]
                    # Split by tab (pdfplumber uses tabs to separate columns)
                    header_cols = header.split('\t')
                    logger.info(f"DEBUG extract_column_from_value: Found table header: {header_cols}")
                    
                    # Search for the column name in headers (case-insensitive)
                    for idx, header_col in enumerate(header_cols):
                        if header_col.strip().lower() == column.lower().strip():
                            column_index = idx
                            logger.info(f"DEBUG extract_column_from_value: Found column '{column}' at index {idx}")
                            break
                    
                    if column_index is not None:
                        break
        
        # If we found the column index from table headers, use it
        if column_index is not None and 0 <= column_index < len(columns):
            logger.info(f"DEBUG extract_column_from_value: Using column index {column_index} from table header: {columns[column_index]}")
            return columns[column_index]
        
        # Fallback to keyword-based heuristics if header search didn't work
        column_keywords_lower = column_lower.replace(' ', '')
        
        if 'annum' in column_keywords_lower or 'annual' in column_keywords_lower or 'yearly' in column_keywords_lower or 'year' in column_keywords_lower:
            # Likely the last/annual column
            logger.info(f"Column name '{column}' contains annual/year keyword - using last column: {columns[-1]}")
            return columns[-1]
        elif 'month' in column_keywords_lower or 'monthly' in column_keywords_lower:
            # Likely the Per Month column (usually 2nd column, index 1)
            if len(columns) >= 2:
                logger.info(f"Column name '{column}' contains month keyword - using 2nd column (index 1): {columns[1]}")
                return columns[1]
            else:
                logger.info(f"Column name '{column}' contains month keyword but only 1 column - returning first: {columns[0]}")
                return columns[0]
        else:
            # Generic column name - default to second column (first value column)
            # if there are 3+ columns, since first column is typically the row label.
            if len(columns) >= 3:
                # Multi-column table with row labels
                # Default to second column (first value column)
                logger.info(f"Column name '{column}' specified - defaulting to second column (first value column): {columns[1]}")
                return columns[1]
            else:
                # Only 2 columns, use first
                logger.info(f"Column name '{column}' specified - using first column: {columns[0]}")
            return columns[0]

