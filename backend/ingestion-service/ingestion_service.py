"""
Ingestion Microservice for Oracle Chatbot System
"""

import asyncio
import hashlib
import io
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import os

import easyocr
import numpy as np
import fitz  # PyMuPDF
import pypdf
from docx import Document as DocxDocument
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

# Initialize logger
logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Oracle Ingestion Service",
    description="Microservice for document ingestion and processing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global OCR reader cache
ocr_readers = {}

class ProcessingOptions(BaseModel):
    """Options for document processing"""
    language: str = "en"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    extract_entities: bool = False
    create_embeddings: bool = False

class ProcessedFile(BaseModel):
    """Result of processing a single file"""
    filename: str
    file_size: int
    file_type: Optional[str]
    entities_extracted: int
    chunks_created: int
    graph_nodes_added: int
    graph_relationships_added: int
    vector_embeddings_created: int
    processing_time: float
    checksum: str

class IngestionError(BaseModel):
    """Error information for file processing"""
    filename: str
    error_type: str
    error_message: str
    retry_possible: bool
    suggestions: List[str]

class IngestionResponse(BaseModel):
    """Response model for ingestion results"""
    status: str
    processed_files: List[ProcessedFile]
    errors: List[IngestionError]
    total_files: int
    successful_files: int
    failed_files: int
    processing_time: float
    batch_id: Optional[str] = None

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

class DocumentParser:
    """Handles parsing of different document formats."""
    
    @classmethod
    def _normalize_languages(cls, languages: List[str]) -> List[str]:
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

    @classmethod
    def _get_easyocr_reader(cls, languages: List[str], gpu: bool = False):
        """Return a cached EasyOCR Reader for the given languages."""
        langs = tuple(cls._normalize_languages(languages))
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

    @classmethod
    async def parse_pdf_with_ocr(cls, content: bytes, languages: List[str]) -> str:
        """OCR a PDF by rasterizing pages and running EasyOCR."""
        if not content:
            return ""
        
        # Import required modules
        import fitz  # PyMuPDF
        import numpy as np
        
        text_blocks: List[str] = []
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            reader = cls._get_easyocr_reader(languages, gpu=False)
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
            raise ValueError(f"OCR failed: {str(e)}")

        return "\n\n".join([b for b in text_blocks if b.strip()])

    @staticmethod
    async def parse_pdf(content: bytes) -> str:
        """Parse PDF content and extract text."""
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            text_content = []
            
            for page in pdf_reader.pages:
                # Some pages may return None if they are images-only
                extracted = page.extract_text()
                text_content.append(extracted or "")
            
            return "\n".join(text_content)
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {str(e)}")
    
    @staticmethod
    async def parse_docx(content: bytes) -> str:
        """Parse DOCX content and extract text."""
        try:
            doc = DocxDocument(io.BytesIO(content))
            text_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            return "\n".join(text_content)
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX: {str(e)}")
    
    @staticmethod
    async def parse_text(content: bytes, encoding: str = "utf-8") -> str:
        """Parse plain text content."""
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            # Try alternative encodings
            for alt_encoding in ["latin-1", "cp1252", "iso-8859-1"]:
                try:
                    return content.decode(alt_encoding)
                except UnicodeDecodeError:
                    continue
            raise ValueError("Unable to decode text file with any supported encoding")
    
    @classmethod
    async def parse_document(cls, filename: str, content: bytes) -> str:
        """Parse document based on file extension."""
        file_ext = Path(filename).suffix.lower()
        
        if file_ext == ".pdf":
            return await cls.parse_pdf(content)
        elif file_ext == ".docx":
            return await cls.parse_docx(content)
        elif file_ext in [".txt", ".md"]:
            return await cls.parse_text(content)
        elif file_ext == ".doc":
            # For legacy .doc files, we'll treat them as text for now
            # In production, you might want to use python-docx2txt or similar
            return await cls.parse_text(content)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

class TextProcessor:
    """Handles text processing and chunking."""
    
    def __init__(self, options: ProcessingOptions):
        self.options = options
    
    def create_chunks(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        if not text.strip():
            return []
        
        chunks = []
        chunk_size = self.options.chunk_size
        overlap = self.options.chunk_overlap
        
        # Simple word-based chunking
        words = text.split()
        
        if len(words) <= chunk_size:
            return [text]
        
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            
            if end >= len(words):
                break
                
            start = end - overlap
        
        return chunks
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text (placeholder implementation)."""
        # This is a simplified implementation
        # In production, you'd use NLP libraries like spaCy or transformers
        entities = []
        
        # Simple keyword extraction as placeholder
        words = text.split()
        word_freq = {}
        
        for word in words:
            word = word.strip(".,!?;:").lower()
            if len(word) > 3:  # Filter short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top frequent words as "entities"
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        for word, freq in sorted_words[:20]:  # Top 20 words
            entities.append({
                "text": word,
                "type": "KEYWORD",
                "frequency": freq,
                "confidence": min(freq / 10.0, 1.0)  # Simple confidence score
            })
        
        return entities

async def calculate_checksum(content: bytes) -> str:
    """Calculate SHA-256 checksum of file content."""
    return hashlib.sha256(content).hexdigest()

async def process_single_file(
    file: UploadFile,
    filename: str,
    content: bytes,
    processing_options: ProcessingOptions,
) -> tuple[Optional[ProcessedFile], Optional[IngestionError]]:
    """Process a single uploaded file."""
    start_time = time.time()
    
    try:
        # Calculate checksum
        checksum = await calculate_checksum(content)
        
        # Parse document
        is_pdf = Path(filename).suffix.lower() == ".pdf" or (file.content_type or "").lower() == "application/pdf"
        used_ocr = False
        try:
            text_content = await DocumentParser.parse_document(filename, content)
        except ValueError as e:
            if is_pdf:
                logger.warning(
                    "PDF parse failed, attempting OCR fallback",
                    filename=filename,
                    error=str(e),
                )
                try:
                    text_content = await DocumentParser.parse_pdf_with_ocr(content, [processing_options.language])
                    used_ocr = True
                except Exception as ocr_e:
                    return None, IngestionError(
                        filename=filename,
                        error_type="parsing_error",
                        error_message=f"{str(e)}; OCR fallback failed: {str(ocr_e)}",
                        retry_possible=False,
                        suggestions=[
                            "Check file format and integrity",
                            "If scanned, ensure pages are legible (300+ DPI)",
                        ],
                    )
            else:
                return None, IngestionError(
                    filename=filename,
                    error_type="parsing_error",
                    error_message=str(e),
                    retry_possible=False,
                    suggestions=["Check file format and integrity"],
                )
        
        if not text_content.strip():
            if is_pdf and not used_ocr:
                logger.info(
                    "No text extracted from PDF, attempting OCR fallback",
                    filename=filename,
                )
                try:
                    text_content = await DocumentParser.parse_pdf_with_ocr(content, [processing_options.language])
                    used_ocr = True
                except Exception as ocr_e:
                    return None, IngestionError(
                        filename=filename,
                        error_type="empty_content",
                        error_message=f"No text content found; OCR fallback failed: {str(ocr_e)}",
                        retry_possible=False,
                        suggestions=[
                            "Ensure document contains readable text",
                            "If scanned, use 300+ DPI and high contrast",
                        ],
                    )
            if not text_content.strip():
                return None, IngestionError(
                    filename=filename,
                    error_type="empty_content",
                    error_message="No text content found in document",
                    retry_possible=False,
                    suggestions=[
                        "Ensure document contains readable text",
                        "If scanned, use 300+ DPI and high contrast",
                    ],
                )
        
        # Process text
        processor = TextProcessor(processing_options)
        chunks = processor.create_chunks(text_content)
        
        # Extract entities if requested
        entities = []
        if processing_options.extract_entities:
            entities = processor.extract_entities(text_content)
        
        # For this microservice, we'll simulate vector embeddings creation
        vector_embeddings_created = 0
        if processing_options.create_embeddings:
            # In a real implementation, this would interface with a vector database
            vector_embeddings_created = len(chunks)
        
        processing_time = time.time() - start_time
        
        processed_file = ProcessedFile(
            filename=filename,
            file_size=len(content),
            file_type=file.content_type,
            entities_extracted=len(entities),
            chunks_created=len(chunks),
            graph_nodes_added=len(entities) if processing_options.extract_entities else 0,
            graph_relationships_added=max(0, len(entities) - 1) if processing_options.extract_entities else 0,
            vector_embeddings_created=vector_embeddings_created,
            processing_time=processing_time,
            checksum=checksum,
        )
        
        logger.info(
            "Successfully processed file",
            filename=filename,
            chunks=len(chunks),
            entities=len(entities),
            ocr_used=used_ocr,
        )
        
        return processed_file, None
        
    except Exception as e:
        logger.error(f"Unexpected error processing {filename}: {str(e)}", exc_info=True)
        return None, IngestionError(
            filename=filename,
            error_type="processing_error",
            error_message=f"Unexpected error: {str(e)}",
            retry_possible=True,
            suggestions=["Check file integrity", "Retry the operation"]
        )

@app.post("/ingest", response_model=IngestionResponse)
async def ingest_documents(
    files: List[UploadFile] = File(...),
    language: str = Form("en"),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    extract_entities: bool = Form(False),
    create_embeddings: bool = Form(False)
):
    """
    Ingest and process multiple documents.
    
    Args:
        files: List of files to process
        language: Language for OCR processing (default: "en")
        chunk_size: Size of text chunks (default: 1000)
        chunk_overlap: Overlap between chunks (default: 200)
        extract_entities: Whether to extract entities (default: False)
        create_embeddings: Whether to create embeddings (default: False)
        
    Returns:
        IngestionResponse: Processing results
    """
    start_time = time.time()
    
    # Create processing options
    processing_options = ProcessingOptions(
        language=language,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        extract_entities=extract_entities,
        create_embeddings=create_embeddings
    )
    
    # Process files concurrently
    tasks = []
    for file in files:
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        task = process_single_file(
            file, file.filename or "unknown", content, processing_options
        )
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    processed_files = []
    errors = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(IngestionError(
                filename=files[i].filename or f"file_{i}",
                error_type="system_error",
                error_message=str(result),
                retry_possible=True,
                suggestions=["Check system resources", "Retry the operation"]
            ))
        else:
            processed_file, error = result
            if processed_file:
                processed_files.append(processed_file)
            if error:
                errors.append(error)
    
    total_files = len(files)
    successful_files = len(processed_files)
    failed_files = len(errors)
    
    processing_time = time.time() - start_time
    
    response = IngestionResponse(
        status="success" if failed_files == 0 else "partial_success" if successful_files > 0 else "failed",
        processed_files=processed_files,
        errors=errors,
        total_files=total_files,
        successful_files=successful_files,
        failed_files=failed_files,
        processing_time=processing_time,
    )
    
    return response

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
        
        extracted_text = await DocumentParser.parse_pdf_with_ocr(content, lang_list)
        
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
        service="ingestion-service"
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