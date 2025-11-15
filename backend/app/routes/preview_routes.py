"""
PDF Preview Endpoint
Extracts text from first page of uploaded PDF for live extraction preview
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.parser import extract_text_from_bytes
from app.utils.logger import get_logger

logger = get_logger("PreviewAPI")

router = APIRouter()


@router.post("/preview-pdf-text")
async def preview_pdf_text(file: UploadFile = File(...)):
    """
    Extract text from first page of PDF for extraction preview.
    Returns just the text, no validation.
    """
    try:
        # Read PDF bytes
        pdf_bytes = await file.read()
        
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Extract text (our hybrid extractor handles first page efficiently)
        text = extract_text_from_bytes(pdf_bytes)
        
        if not text or text.startswith("[SCANNED_PDF]") or text.startswith("[binary-pdf"):
            return {
                "success": False,
                "text": "",
                "message": "PDF appears to be scanned or image-based. Preview not available."
            }
        
        # Return first 10,000 characters (enough for preview, not too heavy)
        preview_text = text[:10000]
        
        logger.info(f"Preview extracted {len(preview_text)} chars from {file.filename}")
        
        return {
            "success": True,
            "text": preview_text,
            "length": len(preview_text),
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"Preview extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")
