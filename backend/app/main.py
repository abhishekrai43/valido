from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from .services.parser import extract_text_from_bytes
from .services.validator import validate_text

app = FastAPI(title="PDF Validator (stub)")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/api/v1/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Accept a single PDF upload and return a validation report.

    This is a minimal stub: it extracts text via the parser stub and runs
    basic deterministic validation via the validator stub.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are accepted")

    body = await file.read()
    try:
        text = extract_text_from_bytes(body)
    except Exception as exc:
        # Keep comments short and actionable; avoid long AI notes in code.
        raise HTTPException(status_code=500, detail=f"parser error: {exc}")

    report = validate_text(text)
    return JSONResponse(content={"filename": file.filename, "report": report})
