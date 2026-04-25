"""
Table Extraction Service
Modular service for extracting tables from PDFs with structured output.
Supports extraction by index, range, and all tables.
"""
from typing import List, Dict, Any, Optional
import logging

try:
    import pdfplumber
except ImportError:  # pragma: no cover - optional dependency
    pdfplumber = None

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - PyMuPDF is a core dependency, but keep the import safe
    fitz = None

logger = logging.getLogger(__name__)


class TableExtractor:
    """Handles structured table extraction from PDF pages."""
    
    def __init__(self, pdf_path: str):
        """
        Initialize table extractor with PDF path.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path
        self.pdf = None
        self.doc = None
        self.backend = None
    
    def __enter__(self):
        """Context manager entry."""
        if pdfplumber is not None:
            self.pdf = pdfplumber.open(self.pdf_path)
            self.backend = "pdfplumber"
        elif fitz is not None:
            self.doc = fitz.open(self.pdf_path)
            self.backend = "fitz"
        else:
            raise ImportError("Neither pdfplumber nor PyMuPDF is available for table extraction")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.pdf:
            self.pdf.close()
        if self.doc:
            self.doc.close()

    def _page_count(self) -> int:
        if self.backend == "pdfplumber" and self.pdf is not None:
            return len(self.pdf.pages)
        if self.backend == "fitz" and self.doc is not None:
            return len(self.doc)
        return 0

    def _extract_tables_from_page(self, page_num: int) -> List[List[List[str]]]:
        if self.backend == "pdfplumber" and self.pdf is not None:
            page = self.pdf.pages[page_num - 1]
            return page.extract_tables() or []

        if self.backend == "fitz" and self.doc is not None:
            page = self.doc[page_num - 1]
            try:
                table_finder = page.find_tables()
                tables = []
                for table in getattr(table_finder, "tables", []) or []:
                    extracted = table.extract()
                    if extracted:
                        tables.append(extracted)
                return tables
            except Exception as e:
                logger.info(f"PyMuPDF table extraction failed on page {page_num}: {type(e).__name__}: {e}")
                return []

        return []
    
    def extract_by_index(self, page_num: int, table_index: int) -> Optional[Dict[str, Any]]:
        """
        Extract a specific table by index from a page.
        
        Args:
            page_num: Page number (1-based)
            table_index: Table index (1-based, or -1 for last table)
        
        Returns:
            Dictionary with table data and metadata, or None if not found
            {
                "table_index": int,
                "page": int,
                "rows": int,
                "columns": int,
                "headers": List[str],
                "data": List[List[str]],
                "raw": List[List[str]]  # includes headers
            }
        """
        try:
            if page_num < 1 or page_num > self._page_count():
                logger.warning(f"Invalid page number: {page_num}")
                return None
            tables = self._extract_tables_from_page(page_num)
            
            if not tables:
                logger.info(f"No tables found on page {page_num}")
                return None
            
            # Handle negative index (last table)
            if table_index == -1:
                table_index = len(tables)
            
            if table_index < 1 or table_index > len(tables):
                logger.warning(f"Invalid table index {table_index} on page {page_num} (found {len(tables)} tables)")
                return None
            
            table = tables[table_index - 1]
            return self._format_table(table, page_num, table_index)
        
        except Exception as e:
            logger.error(f"Error extracting table {table_index} from page {page_num}: {str(e)}")
            return None
    
    def extract_all(self, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract all tables from a page.
        
        Args:
            page_num: Page number (1-based)
        
        Returns:
            List of table dictionaries, empty list if none found
        """
        try:
            if page_num < 1 or page_num > self._page_count():
                logger.warning(f"Invalid page number: {page_num}")
                return []
            tables = self._extract_tables_from_page(page_num)
            
            if not tables:
                logger.info(f"No tables found on page {page_num}")
                return []
            
            return [
                self._format_table(table, page_num, idx + 1)
                for idx, table in enumerate(tables)
            ]
        
        except Exception as e:
            logger.error(f"Error extracting all tables from page {page_num}: {str(e)}")
            return []
    
    def extract_range(self, page_num: int, start_index: int, end_index: int) -> List[Dict[str, Any]]:
        """
        Extract a range of tables from a page.
        
        Args:
            page_num: Page number (1-based)
            start_index: Starting table index (1-based, inclusive)
            end_index: Ending table index (1-based, inclusive, or -1 for last)
        
        Returns:
            List of table dictionaries
        """
        try:
            if page_num < 1 or page_num > self._page_count():
                logger.warning(f"Invalid page number: {page_num}")
                return []
            tables = self._extract_tables_from_page(page_num)
            
            if not tables:
                logger.info(f"No tables found on page {page_num}")
                return []
            
            # Handle negative end_index (last table)
            if end_index == -1:
                end_index = len(tables)
            
            # Validate range
            if start_index < 1 or start_index > len(tables):
                logger.warning(f"Invalid start index {start_index}")
                return []
            
            if end_index < start_index or end_index > len(tables):
                logger.warning(f"Invalid end index {end_index}")
                return []
            
            # Extract range (convert to 0-based indexing)
            selected_tables = tables[start_index - 1:end_index]
            
            return [
                self._format_table(table, page_num, start_index + idx)
                for idx, table in enumerate(selected_tables)
            ]
        
        except Exception as e:
            logger.error(f"Error extracting tables {start_index}-{end_index} from page {page_num}: {str(e)}")
            return []
    
    def count_tables(self, page_num: int) -> int:
        """
        Count tables on a specific page.
        
        Args:
            page_num: Page number (1-based)
        
        Returns:
            Number of tables found
        """
        try:
            if page_num < 1 or page_num > self._page_count():
                return 0
            tables = self._extract_tables_from_page(page_num)
            return len(tables) if tables else 0
        
        except Exception as e:
            logger.error(f"Error counting tables on page {page_num}: {str(e)}")
            return 0
    
    def get_table_summary(self) -> Dict[int, int]:
        """
        Get summary of tables across all pages.
        
        Returns:
            Dictionary mapping page numbers to table counts
            {1: 2, 3: 1, 5: 3}  # Page 1 has 2 tables, page 3 has 1, etc.
        """
        summary = {}
        try:
            for page_num in range(1, self._page_count() + 1):
                count = self.count_tables(page_num)
                if count > 0:
                    summary[page_num] = count
        except Exception as e:
            logger.error(f"Error generating table summary: {str(e)}")
        
        return summary
    
    def _format_table(self, table: List[List[str]], page_num: int, table_index: int) -> Dict[str, Any]:
        """
        Format raw table data into structured dictionary.
        
        Args:
            table: Raw table data from pdfplumber
            page_num: Page number
            table_index: Table index on page
        
        Returns:
            Formatted table dictionary
        """
        if not table or len(table) == 0:
            return {
                "table_index": table_index,
                "page": page_num,
                "rows": 0,
                "columns": 0,
                "headers": [],
                "data": [],
                "raw": []
            }
        
        # Clean table data (replace None with empty string)
        cleaned_table = []
        for row in table:
            cleaned_row = [str(cell) if cell is not None else "" for cell in row]
            cleaned_table.append(cleaned_row)
        
        # First row as headers
        headers = cleaned_table[0] if cleaned_table else []
        data = cleaned_table[1:] if len(cleaned_table) > 1 else []
        
        return {
            "table_index": table_index,
            "page": page_num,
            "rows": len(data),
            "columns": len(headers),
            "headers": headers,
            "data": data,
            "raw": cleaned_table  # includes headers
        }
    
    @staticmethod
    def extract_single_table(pdf_path: str, page_num: int, table_index: int) -> Optional[Dict[str, Any]]:
        """
        Convenience method to extract a single table without context manager.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-based)
            table_index: Table index (1-based, or -1 for last)
        
        Returns:
            Table dictionary or None
        """
        with TableExtractor(pdf_path) as extractor:
            return extractor.extract_by_index(page_num, table_index)
    
    @staticmethod
    def extract_all_tables(pdf_path: str, page_num: int) -> List[Dict[str, Any]]:
        """
        Convenience method to extract all tables from a page.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-based)
        
        Returns:
            List of table dictionaries
        """
        with TableExtractor(pdf_path) as extractor:
            return extractor.extract_all(page_num)
    
    @staticmethod
    def get_pdf_table_summary(pdf_path: str) -> Dict[int, int]:
        """
        Convenience method to get table summary for entire PDF.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Dictionary mapping page numbers to table counts
        """
        with TableExtractor(pdf_path) as extractor:
            return extractor.get_table_summary()
