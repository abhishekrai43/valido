"""
Table Extraction API Routes
Provides endpoints for extracting tables from PDFs with various strategies.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import tempfile
import os
from app.services.parser import (
    extract_table_by_index,
    extract_all_tables,
    get_table_summary
)
from app.services.table_exporter import TableExporter
from app.utils.logger import get_logger

logger = get_logger("TableRoutes")
router = APIRouter()


class TableExtractionRequest(BaseModel):
    """Request model for table extraction."""
    page_num: int
    table_index: Optional[int] = None  # None means extract all tables
    

class TableExtractionResponse(BaseModel):
    """Response model for table extraction."""
    success: bool
    table: Optional[Dict[str, Any]] = None
    tables: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class TableSummaryResponse(BaseModel):
    """Response model for table summary."""
    success: bool
    summary: Dict[int, int]  # page_num -> table_count
    total_tables: int
    message: Optional[str] = None


@router.post("/extract-table", response_model=TableExtractionResponse)
async def extract_table(file: UploadFile = File(...), page_num: int = 1, table_index: int = 1):
    """
    Extract a specific table from a PDF page.
    
    Args:
        file: PDF file to process
        page_num: Page number (1-based)
        table_index: Table index (1-based, or -1 for last table)
    
    Returns:
        Table data with metadata
    """
    temp_path = None
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
        
        # Extract table
        table_data = extract_table_by_index(temp_path, page_num, table_index)
        
        if table_data:
            return TableExtractionResponse(
                success=True,
                table=table_data,
                message=f"Successfully extracted table {table_index} from page {page_num}"
            )
        else:
            return TableExtractionResponse(
                success=False,
                message=f"No table found at index {table_index} on page {page_num}"
            )
    
    except Exception as e:
        logger.error(f"Table extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract table: {str(e)}")
    
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/extract-all-tables", response_model=TableExtractionResponse)
async def extract_all_tables_route(file: UploadFile = File(...), page_num: int = 1):
    """
    Extract all tables from a PDF page.
    
    Args:
        file: PDF file to process
        page_num: Page number (1-based)
    
    Returns:
        List of all tables found on the page
    """
    temp_path = None
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
        
        # Extract all tables
        tables_data = extract_all_tables(temp_path, page_num)
        
        return TableExtractionResponse(
            success=True,
            tables=tables_data,
            message=f"Successfully extracted {len(tables_data)} table(s) from page {page_num}"
        )
    
    except Exception as e:
        logger.error(f"All tables extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract tables: {str(e)}")
    
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/table-summary", response_model=TableSummaryResponse)
async def get_table_summary_route(file: UploadFile = File(...)):
    """
    Get summary of all tables in a PDF.
    
    Args:
        file: PDF file to process
    
    Returns:
        Dictionary mapping page numbers to table counts
    """
    temp_path = None
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
        
        # Get table summary
        summary = get_table_summary(temp_path)
        total_tables = sum(summary.values())
        
        return TableSummaryResponse(
            success=True,
            summary=summary,
            total_tables=total_tables,
            message=f"Found {total_tables} table(s) across {len(summary)} page(s)"
        )
    
    except Exception as e:
        logger.error(f"Table summary error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get table summary: {str(e)}")
    
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/export-excel")
async def export_tables_to_excel(file: UploadFile = File(...), page_num: int = 1):
    """
    Extract all tables from a page and export to Excel.
    
    Args:
        file: PDF file to process
        page_num: Page number (1-based)
    
    Returns:
        Excel file download
    """
    temp_pdf_path = None
    output_excel_path = None
    
    try:
        # Save uploaded PDF to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            temp_pdf_path = tmp.name
        
        # Extract all tables from page
        tables = extract_all_tables(temp_pdf_path, page_num)
        
        if not tables:
            raise HTTPException(status_code=404, detail=f"No tables found on page {page_num}")
        
        # Create output Excel file
        output_excel_path = tempfile.mktemp(suffix=".xlsx")
        
        # Export to Excel
        success = TableExporter.export_to_excel(tables, output_excel_path)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create Excel file")
        
        # Return file for download
        return FileResponse(
            output_excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"tables_page_{page_num}.xlsx"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export to Excel: {str(e)}")
    
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)
        # Note: output_excel_path is cleaned up by FileResponse after sending


@router.post("/export-pdf")
async def export_tables_to_pdf(file: UploadFile = File(...), page_num: int = 1):
    """
    Extract all tables from a page and export to formatted PDF.
    
    Args:
        file: PDF file to process
        page_num: Page number (1-based)
    
    Returns:
        PDF file download with formatted tables
    """
    temp_pdf_path = None
    output_pdf_path = None
    
    try:
        # Save uploaded PDF to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            temp_pdf_path = tmp.name
        
        # Extract all tables from page
        tables = extract_all_tables(temp_pdf_path, page_num)
        
        if not tables:
            raise HTTPException(status_code=404, detail=f"No tables found on page {page_num}")
        
        # Create output PDF file
        output_pdf_path = tempfile.mktemp(suffix=".pdf")
        
        # Export to PDF
        title = f"Tables from Page {page_num}"
        success = TableExporter.export_to_pdf(tables, output_pdf_path, title)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create PDF file")
        
        # Return file for download
        return FileResponse(
            output_pdf_path,
            media_type="application/pdf",
            filename=f"tables_page_{page_num}.pdf"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export to PDF: {str(e)}")
    
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)
        # Note: output_pdf_path is cleaned up by FileResponse after sending


@router.post("/export-csv")
async def export_table_to_csv(file: UploadFile = File(...), page_num: int = 1, table_index: int = 1):
    """
    Extract a specific table and export to CSV.
    
    Args:
        file: PDF file to process
        page_num: Page number (1-based)
        table_index: Table index (1-based)
    
    Returns:
        CSV file download
    """
    temp_pdf_path = None
    output_csv_path = None
    
    try:
        # Save uploaded PDF to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            temp_pdf_path = tmp.name
        
        # Extract specific table
        table = extract_table_by_index(temp_pdf_path, page_num, table_index)
        
        if not table:
            raise HTTPException(
                status_code=404, 
                detail=f"Table {table_index} not found on page {page_num}"
            )
        
        # Create output CSV file
        output_csv_path = tempfile.mktemp(suffix=".csv")
        
        # Export to CSV
        success = TableExporter.export_to_csv(table, output_csv_path)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create CSV file")
        
        # Return file for download
        return FileResponse(
            output_csv_path,
            media_type="text/csv",
            filename=f"table_{table_index}_page_{page_num}.csv"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export to CSV: {str(e)}")
    
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)
        # Note: output_csv_path is cleaned up by FileResponse after sending
