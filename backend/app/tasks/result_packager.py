# app/tasks/result_packager.py
"""
Result Packaging Module
Handles creation of ZIP packages containing all validation results.
"""

import os
import zipfile
from typing import Optional


def create_results_zip(
    results_dir: str,
    timestamp: str,
    csv_filename: Optional[str],
    excel_filename: Optional[str],
    pdf_filename: Optional[str],
    log_filename: str,
    json_filename: str
) -> str:
    """
    Create a ZIP file containing all result files.
    
    Args:
        results_dir: Directory containing all result files
        timestamp: Timestamp string for ZIP filename
        csv_filename: Name of CSV file (without path)
        excel_filename: Name of Excel file (without path), if generated
        pdf_filename: Name of PDF file (without path), if generated
        log_filename: Name of log file (without path)
        json_filename: Name of JSON report file (without path)
        
    Returns:
        ZIP filename
    """
    zip_filename = f'valido_results_{timestamp}.zip'
    zip_path = os.path.join(results_dir, zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add CSV
        if csv_filename:
            csv_path = os.path.join(results_dir, csv_filename)
            if os.path.exists(csv_path):
                zipf.write(csv_path, os.path.basename(csv_path))
        
        # Add Excel
        if excel_filename:
            excel_path = os.path.join(results_dir, excel_filename)
            if os.path.exists(excel_path):
                zipf.write(excel_path, os.path.basename(excel_path))
        
        # Add PDF summary
        if pdf_filename:
            pdf_path = os.path.join(results_dir, pdf_filename)
            if os.path.exists(pdf_path):
                zipf.write(pdf_path, os.path.basename(pdf_path))
        
        # Add extraction log
        log_path = os.path.join(results_dir, log_filename)
        if os.path.exists(log_path):
            zipf.write(log_path, os.path.basename(log_path))
        
        # Add JSON report
        json_path = os.path.join(results_dir, json_filename)
        if os.path.exists(json_path):
            zipf.write(json_path, os.path.basename(json_path))
    
    return zip_filename
