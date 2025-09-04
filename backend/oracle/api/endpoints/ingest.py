"""
Document ingestion API endpoints.
"""

import asyncio
import hashlib
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
import httpx

from oracle.models.ingestion import (
    IngestionRequest,
    IngestionResponse,
    ProcessingOptions,
    ProcessedFile,
    IngestionError,
    FileUploadInfo,
)
from oracle.core.config import get_settings
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()

def get_ingestion_service_url() -> str:
    """Get the ingestion service URL from settings."""
    settings = get_settings()
    return getattr(settings, 'INGESTION_SERVICE_URL', 'http://oracle-ingestion-service:8081')

@router.post(
    "/",
    response_model=IngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest documents for knowledge processing",
    description="Upload and process documents for knowledge graph and vector database storage",
)
async def ingest_documents(
    files: List[UploadFile] = File(..., description="Documents to ingest"),
    chunk_size: int = Form(1000, description="Size of text chunks for processing"),
    chunk_overlap: int = Form(200, description="Overlap between consecutive chunks"),
    extract_entities: bool = Form(True, description="Whether to extract entities for knowledge graph"),
    create_embeddings: bool = Form(True, description="Whether to create vector embeddings"),
    language: str = Form("en", description="Document language code"),
    batch_id: Optional[str] = Form(None, description="Optional batch identifier"),
    ingestion_service_url: str = Depends(get_ingestion_service_url),
) -> IngestionResponse:
    """
    Ingest multiple documents by forwarding to the Ingestion Microservice.
    
    Supports PDF, TXT, DOCX, DOC, and MD file formats.
    Files are processed by the dedicated ingestion service.
    """
    start_time = time.time()
    
    # Log incoming request details for diagnostics
    logger.info(f"Received ingestion request with {len(files)} files")
    for file in files:
        logger.info(f"File details - Name: {file.filename}, Size: {file.size}, Content-Type: {file.content_type}")
    
    # Validate files
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for ingestion"
        )
    
    if len(files) > 50:  # Reasonable batch limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many files in batch. Maximum 50 files allowed."
        )
    
    try:
        # Forward request to ingestion microservice
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout
            # Prepare files for upload
            files_data = []
            for file in files:
                content = await file.read()
                await file.seek(0)  # Reset file pointer
                files_data.append(('files', (file.filename, content, file.content_type)))
            
            # Prepare form data
            data = {
                'language': language,
                'chunk_size': str(chunk_size),
                'chunk_overlap': str(chunk_overlap),
                'extract_entities': str(extract_entities).lower(),
                'create_embeddings': str(create_embeddings).lower(),
            }
            
            if batch_id:
                data['batch_id'] = batch_id
            
            # Make request to ingestion service
            response = await client.post(
                f"{ingestion_service_url}/ingest",
                files=files_data,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                processing_time = time.time() - start_time
                result['processing_time'] = processing_time
                logger.info(
                    f"Ingestion completed: {result['successful_files']}/{result['total_files']} files processed successfully"
                )
                return IngestionResponse(**result)
            else:
                logger.error(f"Ingestion service returned error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Ingestion service error: {response.text}"
                )
                
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to ingestion service: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion service is unavailable"
        )
    except Exception as e:
        logger.error(f"Ingestion failed with unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process ingestion request"
        )

@router.get(
    "/status/{batch_id}",
    summary="Get ingestion batch status",
    description="Check the status of a document ingestion batch",
)
async def get_batch_status(
    batch_id: str,
    ingestion_service_url: str = Depends(get_ingestion_service_url),
) -> JSONResponse:
    """Get the status of a document ingestion batch from the ingestion service."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ingestion_service_url}/status/{batch_id}"
            )
            
            if response.status_code == 200:
                return JSONResponse(content=response.json())
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Batch not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Ingestion service error: {response.text}"
                )
                
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to ingestion service: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion service is unavailable"
        )
    except Exception as e:
        logger.error(f"Failed to get batch status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve batch status"
        )

@router.get(
    "/supported-formats",
    summary="Get supported file formats",
    description="List all supported document formats for ingestion",
)
async def get_supported_formats() -> JSONResponse:
    """Get list of supported file formats for document ingestion."""
    formats = {
        "supported_formats": [
            {
                "extension": ".pdf",
                "description": "Portable Document Format",
                "max_size_mb": 50
            },
            {
                "extension": ".txt",
                "description": "Plain text files",
                "max_size_mb": 50
            },
            {
                "extension": ".docx",
                "description": "Microsoft Word (Office Open XML)",
                "max_size_mb": 50
            },
            {
                "extension": ".doc",
                "description": "Microsoft Word (Legacy)",
                "max_size_mb": 50
            },
            {
                "extension": ".md",
                "description": "Markdown files",
                "max_size_mb": 50
            }
        ],
        "max_files_per_batch": 50,
        "max_file_size_bytes": 50 * 1024 * 1024
    }
    return JSONResponse(content=formats)