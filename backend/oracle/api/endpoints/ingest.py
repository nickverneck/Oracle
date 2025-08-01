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

from oracle.models.ingestion import (
    IngestionRequest,
    IngestionResponse,
    ProcessingOptions,
    ProcessedFile,
    IngestionError,
    FileUploadInfo,
)
from oracle.services.ingestion import IngestionService
from oracle.services.knowledge import KnowledgeRetrievalService
from oracle.core.config import get_settings
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()

# Global instances
knowledge_service = None


def get_knowledge_service() -> KnowledgeRetrievalService:
    """Get knowledge retrieval service instance."""
    global knowledge_service
    if knowledge_service is None:
        settings = get_settings()
        config = {
            "neo4j": {
                "uri": getattr(settings, "NEO4J_URI", "bolt://localhost:7687"),
                "username": getattr(settings, "NEO4J_USERNAME", "neo4j"),
                "password": getattr(settings, "NEO4J_PASSWORD", "password")
            },
            "chromadb": {
                "host": getattr(settings, "CHROMADB_HOST", "localhost"),
                "port": getattr(settings, "CHROMADB_PORT", 8002)
            },
            "retrieval": {
                "max_graph_results": 5,
                "max_vector_results": 5,
                "similarity_threshold": 0.7
            }
        }
        knowledge_service = KnowledgeRetrievalService(config)
    return knowledge_service


def get_ingestion_service(
    knowledge_service: KnowledgeRetrievalService = Depends(get_knowledge_service)
) -> IngestionService:
    """Dependency to get ingestion service instance."""
    return IngestionService(knowledge_service=knowledge_service)


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
    overwrite_existing: bool = Form(False, description="Whether to overwrite existing documents"),
    batch_id: Optional[str] = Form(None, description="Optional batch identifier"),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> IngestionResponse:
    """
    Ingest multiple documents for processing into knowledge graph and vector database.
    
    Supports PDF, TXT, DOCX, DOC, and MD file formats.
    Files are processed in parallel with comprehensive error handling.
    """
    start_time = time.time()
    
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
    
    # Create processing options
    try:
        processing_options = ProcessingOptions(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            extract_entities=extract_entities,
            create_embeddings=create_embeddings,
            language=language,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid processing options: {str(e)}"
        )
    
    # Validate file metadata
    file_infos = []
    for file in files:
        try:
            file_info = FileUploadInfo(
                filename=file.filename or "unknown",
                content_type=file.content_type or "application/octet-stream",
                size=file.size or 0,
            )
            file_infos.append(file_info)
        except ValueError as e:
            logger.warning(f"Invalid file {file.filename}: {str(e)}")
            return IngestionResponse(
                status="failed",
                total_files=len(files),
                successful_files=0,
                failed_files=len(files),
                errors=[
                    IngestionError(
                        filename=file.filename or "unknown",
                        error_type="validation_error",
                        error_message=str(e),
                        retry_possible=False,
                        suggestions=["Check file format and size limits"]
                    )
                ],
                processing_time=time.time() - start_time,
                batch_id=batch_id,
            )
    
    logger.info(f"Starting ingestion of {len(files)} files with batch_id: {batch_id}")
    
    # Process files
    try:
        result = await ingestion_service.process_files(
            files=files,
            file_infos=file_infos,
            processing_options=processing_options,
            overwrite_existing=overwrite_existing,
            batch_id=batch_id,
        )
        
        processing_time = time.time() - start_time
        result.processing_time = processing_time
        
        logger.info(
            f"Ingestion completed: {result.successful_files}/{result.total_files} files processed successfully"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ingestion failed with unexpected error: {str(e)}", exc_info=True)
        
        return IngestionResponse(
            status="failed",
            total_files=len(files),
            successful_files=0,
            failed_files=len(files),
            errors=[
                IngestionError(
                    filename="batch",
                    error_type="system_error",
                    error_message=str(e),
                    retry_possible=True,
                    suggestions=["Check system logs", "Retry the operation"]
                )
            ],
            processing_time=time.time() - start_time,
            batch_id=batch_id,
        )


@router.get(
    "/status/{batch_id}",
    summary="Get ingestion batch status",
    description="Check the status of a document ingestion batch",
)
async def get_batch_status(
    batch_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> JSONResponse:
    """Get the status of a document ingestion batch."""
    try:
        status_info = await ingestion_service.get_batch_status(batch_id)
        return JSONResponse(content=status_info)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
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