# Microservice Architecture Implementation

## Overview

This document describes the implementation of a microservice architecture for the Oracle Chatbot System, specifically focusing on separating the document ingestion functionality (including OCR) into its own dedicated microservice.

## Architecture Changes

### 1. Ingestion Microservice

The entire document ingestion functionality has been moved to a dedicated microservice located in `backend/ingestion-service/` with the following components:

- **Dockerfile**: A multi-stage Dockerfile that:
  - Downloads OCR models during the build process to cache them in Docker layers
  - Supports both CPU-only and CUDA-enabled PyTorch installations
  - Supports MPS (Metal Performance Shaders) for Mac users
  - Installs all necessary dependencies for document processing and OCR

- **ingestion_service.py**: A FastAPI application that:
  - Provides endpoints for document ingestion
  - Handles OCR processing using EasyOCR
  - Manages document parsing for various formats (PDF, DOCX, TXT, etc.)
  - Includes text processing and chunking functionality
  - Supports multiple languages
  - Includes health check endpoints
  - Handles GPU/CPU configuration

- **requirements.txt**: Explicit dependency file for easier development and maintenance

### 2. Main Backend Container Optimization

The main backend container has been significantly optimized by:

- Removing all document processing and OCR dependencies from `pyproject.toml`
- Removing the local `IngestionService` implementation
- Updating API endpoints to forward requests to the ingestion microservice
- Removing system dependencies only needed for document processing (libgl1, libglib2.0-0)

This reduces the container size significantly by eliminating CUDA, PyTorch, EasyOCR, and other heavy dependencies that are only needed for document processing.

### 3. Service Communication

The main backend now communicates with the ingestion microservice via HTTP requests:

- Added `INGESTION_SERVICE_URL` environment variable configuration
- Replaced local ingestion processing with HTTP calls to the ingestion service
- Implemented proper error handling for service unavailability
- Forwarded all ingestion API endpoints to the microservice

### 4. Docker Compose Updates

Updated both `docker-compose.yml` and `docker-compose.dev.yml` to:

- Include the new ingestion service
- Remove the separate OCR service (now part of ingestion)
- Configure service dependencies
- Add volume for model persistence
- Support CUDA/MPS configuration via build arguments

## Configuration Options

### Environment Variables

- `CUDA_ENABLED` (default: false): Set to "true" to enable CUDA support in the ingestion service
- `MPS_ENABLED` (default: false): Set to "true" to enable MPS support for Mac users
- `INGESTION_SERVICE_URL` (default: http://oracle-ingestion-service:8081): URL for the ingestion microservice

### Docker Build Arguments

When building the ingestion service, you can specify:

```bash
# For CUDA support
docker build --build-arg CUDA_ENABLED=true -t ingestion-service .

# For MPS support (Mac users)
docker build --build-arg MPS_ENABLED=true -t ingestion-service .
```

## Model Caching

The ingestion service Dockerfile uses a multi-stage build approach:

1. First stage downloads and caches OCR models
2. Second stage copies the cached models
3. This ensures models are part of the Docker layer cache and don't need to be downloaded on each container start

## Benefits

1. **Reduced Main Container Size**: Main backend container is much smaller without document processing dependencies
2. **Scalability**: Ingestion service can be scaled independently based on document processing load
3. **Resource Isolation**: Document processing (which can be CPU/GPU intensive) is isolated from the main backend
4. **Flexibility**: Users can choose whether to deploy the ingestion service based on their needs
5. **Performance**: Main backend performance is not affected by document processing tasks
6. **Hardware Support**: Better support for different hardware configurations (CPU/CUDA/MPS)
7. **Maintenance**: Easier to update document processing dependencies without affecting the main backend

## Usage

To use the document ingestion functionality:

1. Ensure the ingestion service is running alongside the main backend
2. The backend will automatically forward ingestion requests to the ingestion service
3. Users can disable the ingestion service entirely if not needed by not deploying it

## API Endpoints

The ingestion service provides the following endpoints:

- `POST /ingest`: Process and ingest documents
- `GET /status/{batch_id}`: Check the status of an ingestion batch
- `GET /health`: Health check endpoint
- `GET /languages`: Get supported languages for OCR
- `POST /ocr`: Direct OCR processing endpoint

## Future Improvements

1. Add authentication between services
2. Implement circuit breaker pattern for service resilience
3. Add metrics and monitoring for the ingestion service
4. Support additional document formats
5. Implement more sophisticated text processing and entity extraction