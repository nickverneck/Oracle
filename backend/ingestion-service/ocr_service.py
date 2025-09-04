"""
OCR Microservice for Oracle Chatbot System
"""

import io
from typing import List, Optional
import os

import easyocr
import numpy as np
import fitz  # PyMuPDF
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

# Initialize logger
logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Oracle OCR Service",
    description="Microservice for OCR processing using EasyOCR",
    version="1.0.0"
)

# Global OCR reader cache
ocr_readers = {}

class OCRResponse(BaseModel):
    """Response model for OCR results"""
    text: str
    language: str
    success: bool
    error_message: Optional[str] = None

class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    service: str

def _normalize_languages(languages: List[str]) -> List[str]:
    """Normalize language codes to EasyOCR expected codes."""
    if not languages:
        return ["en"]
    norm = []
    mapping = {
        "zh": "ch_sim",
        "zh-cn": "ch_sim",
        "zh-hans": "ch_sim",
        "zh-tw": "ch_tra",
        "zh-hant": "ch_tra",
        "pt-br": "pt",
    }
    for lang in languages:
        code = lang.lower()
        code = mapping.get(code, mapping.get(code.split("-")[0], code.split("-")[0]))
        norm.append(code)
    # Always include English as a helper language
    if "en" not in norm:
        norm.append("en")
    # Preserve order but deduplicate
    seen = set()
    dedup: List[str] = []
    for x in norm:
        if x not in seen:
            dedup.append(x)
            seen.add(x)
    return dedup

def _get_easyocr_reader(languages: List[str], gpu: bool = False):
    """Return a cached EasyOCR Reader for the given languages."""
    langs = tuple(_normalize_languages(languages))
    if langs in ocr_readers:
        return ocr_readers[langs]
    
    # Set model storage directory from environment variable
    model_storage_directory = os.environ.get("EASYOCR_MODULE_PATH", None)
    
    reader = easyocr.Reader(
        list(langs), 
        gpu=gpu, 
        verbose=False,
        model_storage_directory=model_storage_directory
    )
    ocr_readers[langs] = reader
    return reader

@app.post("/ocr", response_model=OCRResponse)
async def ocr_pdf(
    file: UploadFile = File(...),
    languages: str = Form("en"),
    gpu: bool = Form(False)
):
    """
    Perform OCR on a PDF file.
    
    Args:
        file: PDF file to process
        languages: Comma-separated list of language codes (default: "en")
        gpu: Whether to use GPU acceleration (default: False)
        
    Returns:
        OCRResponse: Extracted text and processing status
    """
    try:
        # Validate file type
        if not file.content_type == "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        if not content:
            return OCRResponse(
                text="",
                language=languages,
                success=False,
                error_message="Empty file provided"
            )
        
        # Parse languages
        lang_list = [lang.strip() for lang in languages.split(",")] if languages else ["en"]
        
        # Import required modules
        import fitz  # PyMuPDF
        import numpy as np
        
        text_blocks: List[str] = []
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            reader = _get_easyocr_reader(lang_list, gpu=gpu)
            for page in doc:
                # Render at higher DPI for better OCR
                pix = page.get_pixmap(dpi=200, alpha=False)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 4:
                    img = img[:, :, :3]  # drop alpha
                # Run OCR; paragraph groups lines logically
                lines = reader.readtext(img, detail=0, paragraph=True)
                if lines:
                    text_blocks.append("\n".join([s for s in lines if isinstance(s, str) and s.strip()]))
        except Exception as e:
            logger.error("OCR processing failed", error=str(e))
            return OCRResponse(
                text="",
                language=languages,
                success=False,
                error_message=f"OCR processing failed: {str(e)}"
            )
        
        extracted_text = "\n\n".join([b for b in text_blocks if b.strip()])
        
        return OCRResponse(
            text=extracted_text,
            language=languages,
            success=True
        )
        
    except Exception as e:
        logger.error("Unexpected error in OCR processing", error=str(e))
        return OCRResponse(
            text="",
            language=languages,
            success=False,
            error_message=f"Unexpected error: {str(e)}"
        )

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthCheckResponse: Service status
    """
    return HealthCheckResponse(
        status="healthy",
        service="ocr-service"
    )

@app.get("/languages")
async def supported_languages():
    """
    Get list of supported languages.
    
    Returns:
        dict: List of supported language codes
    """
    # This is a simplified list - in practice, EasyOCR supports many more
    languages = [
        "en", "ch_sim", "ch_tra", "fr", "de", "ja", "ko", "es", "ru", "ar",
        "hi", "pt", "it", "tr", "pl", "nl", "sv", "da", "no", "fi"
    ]
    return {"supported_languages": languages}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)