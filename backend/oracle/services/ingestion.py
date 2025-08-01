"""
Document ingestion service for processing uploaded files.
"""

import asyncio
import hashlib
import io
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import aiofiles
from fastapi import UploadFile
import pypdf
from docx import Document as DocxDocument

from oracle.models.ingestion import (
    ProcessingOptions,
    ProcessedFile,
    IngestionError,
    IngestionResponse,
    FileUploadInfo,
)
import structlog

logger = structlog.get_logger(__name__)


class DocumentParser:
    """Handles parsing of different document formats."""
    
    @staticmethod
    async def parse_pdf(content: bytes) -> str:
        """Parse PDF content and extract text."""
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            text_content = []
            
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
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
    
    async def parse_document(self, filename: str, content: bytes) -> str:
        """Parse document based on file extension."""
        file_ext = Path(filename).suffix.lower()
        
        if file_ext == ".pdf":
            return await self.parse_pdf(content)
        elif file_ext == ".docx":
            return await self.parse_docx(content)
        elif file_ext in [".txt", ".md"]:
            return await self.parse_text(content)
        elif file_ext == ".doc":
            # For legacy .doc files, we'll treat them as text for now
            # In production, you might want to use python-docx2txt or similar
            return await self.parse_text(content)
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


class IngestionService:
    """Main service for document ingestion and processing."""
    
    def __init__(self, knowledge_service=None):
        self.parser = DocumentParser()
        self.batch_status: Dict[str, Dict] = {}  # In-memory storage for demo
        self.knowledge_service = knowledge_service
    
    async def calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA-256 checksum of file content."""
        return hashlib.sha256(content).hexdigest()
    
    async def process_single_file(
        self,
        file: UploadFile,
        file_info: FileUploadInfo,
        processing_options: ProcessingOptions,
        overwrite_existing: bool = False,
    ) -> Tuple[Optional[ProcessedFile], Optional[IngestionError]]:
        """Process a single uploaded file."""
        start_time = time.time()
        
        try:
            # Read file content
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Calculate checksum
            checksum = await self.calculate_checksum(content)
            
            # Parse document
            try:
                text_content = await self.parser.parse_document(file_info.filename, content)
            except ValueError as e:
                return None, IngestionError(
                    filename=file_info.filename,
                    error_type="parsing_error",
                    error_message=str(e),
                    retry_possible=False,
                    suggestions=["Check file format and integrity"]
                )
            
            if not text_content.strip():
                return None, IngestionError(
                    filename=file_info.filename,
                    error_type="empty_content",
                    error_message="No text content found in document",
                    retry_possible=False,
                    suggestions=["Ensure document contains readable text"]
                )
            
            # Process text
            processor = TextProcessor(processing_options)
            chunks = processor.create_chunks(text_content)
            
            # Extract entities if requested
            entities = []
            if processing_options.extract_entities:
                entities = processor.extract_entities(text_content)
            
            # Simulate knowledge graph operations (will be implemented in task 5)
            graph_nodes_added = len(entities) if processing_options.extract_entities else 0
            graph_relationships_added = max(0, len(entities) - 1) if processing_options.extract_entities else 0
            
            # Create vector embeddings using ChromaDB
            vector_embeddings_created = 0
            if processing_options.create_embeddings and self.knowledge_service:
                try:
                    # Create document metadata
                    document_metadata = {
                        "filename": file_info.filename,
                        "file_type": file_info.content_type,
                        "file_size": file_info.size,
                        "checksum": checksum,
                        "language": processing_options.language,
                        "processed_at": time.time()
                    }
                    
                    # Generate unique document ID
                    document_id = f"{checksum}_{file_info.filename}"
                    
                    # Add document to vector database
                    vector_embeddings_created = await self.knowledge_service.add_document_to_vector_db(
                        text=text_content,
                        metadata=document_metadata,
                        document_id=document_id,
                        chunk_size=processing_options.chunk_size,
                        chunk_overlap=processing_options.chunk_overlap
                    )
                    
                    logger.info(
                        "Created vector embeddings",
                        filename=file_info.filename,
                        chunks=vector_embeddings_created
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to create vector embeddings",
                        filename=file_info.filename,
                        error=str(e)
                    )
                    # Continue processing even if vector embedding fails
                    vector_embeddings_created = 0
            elif processing_options.create_embeddings:
                # Fallback to chunk count if knowledge service not available
                vector_embeddings_created = len(chunks)
            
            processing_time = time.time() - start_time
            
            processed_file = ProcessedFile(
                filename=file_info.filename,
                file_size=file_info.size,
                file_type=file_info.content_type,
                entities_extracted=len(entities),
                chunks_created=len(chunks),
                graph_nodes_added=graph_nodes_added,
                graph_relationships_added=graph_relationships_added,
                vector_embeddings_created=vector_embeddings_created,
                processing_time=processing_time,
                checksum=checksum,
            )
            
            logger.info(f"Successfully processed {file_info.filename}: {len(chunks)} chunks, {len(entities)} entities")
            
            return processed_file, None
            
        except Exception as e:
            logger.error(f"Unexpected error processing {file_info.filename}: {str(e)}", exc_info=True)
            return None, IngestionError(
                filename=file_info.filename,
                error_type="processing_error",
                error_message=f"Unexpected error: {str(e)}",
                retry_possible=True,
                suggestions=["Check file integrity", "Retry the operation"]
            )
    
    async def process_files(
        self,
        files: List[UploadFile],
        file_infos: List[FileUploadInfo],
        processing_options: ProcessingOptions,
        overwrite_existing: bool = False,
        batch_id: Optional[str] = None,
        timeout: int = 300,
    ) -> IngestionResponse:
        """Process multiple files concurrently."""
        start_time = time.time()
        
        # Initialize batch status tracking
        if batch_id:
            self.batch_status[batch_id] = {
                "status": "processing",
                "total_files": len(files),
                "processed_files": 0,
                "start_time": start_time,
            }
        
        # Process files concurrently
        tasks = []
        for file, file_info in zip(files, file_infos):
            task = self.process_single_file(
                file, file_info, processing_options, overwrite_existing
            )
            tasks.append(task)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Ingestion batch {batch_id} timed out after {timeout} seconds")
            if batch_id:
                self.batch_status[batch_id].update({
                    "status": "failed",
                    "error": "timeout",
                    "end_time": time.time(),
                })
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail=f"Processing timed out after {timeout} seconds. Please try again with a smaller batch or a longer timeout."
            )
        
        # Collect results
        processed_files = []
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(IngestionError(
                    filename=file_infos[i].filename,
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
        
        # Update batch status
        if batch_id:
            self.batch_status[batch_id].update({
                "status": "completed",
                "processed_files": len(processed_files),
                "errors": len(errors),
                "end_time": time.time(),
            })
        
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
            batch_id=batch_id,
        )
        
        return response
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get the status of a processing batch."""
        if batch_id not in self.batch_status:
            raise ValueError(f"Batch {batch_id} not found")
        
        return self.batch_status[batch_id]