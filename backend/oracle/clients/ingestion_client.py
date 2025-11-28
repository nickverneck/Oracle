"""
Client for communicating with the Ingestion Microservice
"""

import httpx
from typing import List, Optional, Dict, Any
from fastapi import UploadFile
import structlog

from oracle.models.ingestion import (
    IngestionResponse,
    ProcessingOptions,
    IngestionError
)
from oracle.core.config import get_settings

logger = structlog.get_logger(__name__)


class IngestionClient:
    """Client for the Ingestion Microservice"""
    
    def __init__(self):
        settings = get_settings()
        self.service_url = getattr(settings, 'INGESTION_SERVICE_URL', 'http://oracle-ingestion-service:8081')
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout for large file processing
    
    async def ingest_documents(
        self,
        files: List[UploadFile],
        processing_options: ProcessingOptions,
        overwrite_existing: bool = False,
        batch_id: Optional[str] = None,
    ) -> IngestionResponse:
        """
        Ingest documents using the Ingestion Microservice.
        
        Args:
            files: List of files to ingest
            processing_options: Processing options
            overwrite_existing: Whether to overwrite existing documents
            batch_id: Optional batch identifier
            
        Returns:
            IngestionResponse: Processing results
        """
        try:
            # Prepare files for upload
            files_data = []
            for file in files:
                content = await file.read()
                await file.seek(0)  # Reset file pointer
                files_data.append(('files', (file.filename, content, file.content_type)))
            
            # Prepare form data
            data = {
                'language': processing_options.language,
                'chunk_size': str(processing_options.chunk_size),
                'chunk_overlap': str(processing_options.chunk_overlap),
                'extract_entities': str(processing_options.extract_entities).lower(),
                'create_embeddings': str(processing_options.create_embeddings).lower(),
            }
            
            if batch_id:
                data['batch_id'] = batch_id
            
            # Make request to ingestion service
            response = await self.client.post(
                f"{self.service_url}/ingest",
                files=files_data,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                return IngestionResponse(**result)
            else:
                # Create an error response
                error = IngestionError(
                    filename="batch",
                    error_type="service_error",
                    error_message=f"Ingestion service returned status {response.status_code}: {response.text}",
                    retry_possible=True,
                    suggestions=["Check ingestion service logs", "Retry the operation"]
                )
                return IngestionResponse(
                    status="failed",
                    processed_files=[],
                    errors=[error],
                    total_files=len(files),
                    successful_files=0,
                    failed_files=len(files),
                    processing_time=0.0,
                    batch_id=batch_id,
                )
                
        except Exception as e:
            logger.error("Ingestion service call failed", error=str(e))
            error = IngestionError(
                filename="batch",
                error_type="connection_error",
                error_message=f"Failed to connect to ingestion service: {str(e)}",
                retry_possible=True,
                suggestions=["Check if ingestion service is running", "Verify network connectivity"]
            )
            return IngestionResponse(
                status="failed",
                processed_files=[],
                errors=[error],
                total_files=len(files),
                successful_files=0,
                failed_files=len(files),
                processing_time=0.0,
                batch_id=batch_id,
            )
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Get the status of an ingestion batch.
        
        Args:
            batch_id: Batch identifier
            
        Returns:
            Dict with batch status information
        """
        try:
            response = await self.client.get(
                f"{self.service_url}/status/{batch_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Status check failed with status {response.status_code}")
                
        except Exception as e:
            logger.error("Failed to get batch status", error=str(e))
            raise Exception(f"Failed to get batch status: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global instance
ingestion_client = None


def get_ingestion_client() -> IngestionClient:
    """Get the ingestion client instance."""
    global ingestion_client
    if ingestion_client is None:
        ingestion_client = IngestionClient()
    return ingestion_client