# OCR Microservice Implementation

## Overview

This document describes the implementation of separating the EasyOCR functionality into its own microservice to reduce the size of the main backend container and provide better flexibility for users who may not need OCR capabilities.

## Changes Made

### 1. OCR Microservice Creation

A new microservice has been created in `backend/ocr-service/` with the following components:

- **Dockerfile**: A multi-stage Dockerfile that:
  - Downloads OCR models during the build process to cache them in Docker layers
  - Supports both CPU-only and CUDA-enabled PyTorch installations
  - Supports MPS (Metal Performance Shaders) for Mac users
  - Installs only the necessary dependencies for OCR processing

- **ocr_service.py**: A FastAPI application that:
  - Provides an endpoint for PDF OCR processing
  - Manages EasyOCR reader instances with caching
  - Supports multiple languages
  - Includes health check endpoints
  - Handles GPU/CPU configuration

### 2. Backend Container Optimization

The main backend container has been optimized by:

- Removing EasyOCR, PyMuPDF, and NumPy dependencies from `pyproject.toml`
- Removing the local EasyOCR implementation from `DocumentParser`
- Updating the Dockerfile to remove system dependencies only needed for OCR (libgl1, libglib2.0-0)

This reduces the container size significantly by eliminating CUDA, PyTorch, and other heavy dependencies that are only needed for OCR processing.

### 3. Service Communication

The backend now communicates with the OCR microservice via HTTP requests:

- Added `OCR_SERVICE_URL` environment variable configuration
- Replaced local OCR processing with HTTP calls to the OCR service
- Implemented proper error handling for service unavailability

### 4. Docker Compose Updates

Updated both `docker-compose.yml` and `docker-compose.dev.yml` to:

- Include the new OCR service
- Configure service dependencies
- Add volume for model persistence
- Support CUDA/MPS configuration via build arguments

## Configuration Options

### Environment Variables

- `CUDA_ENABLED` (default: false): Set to "true" to enable CUDA support in the OCR service
- `MPS_ENABLED` (default: false): Set to "true" to enable MPS support for Mac users
- `OCR_SERVICE_URL` (default: http://oracle-ocr-service:8081): URL for the OCR microservice

### Docker Build Arguments

When building the OCR service, you can specify:

```bash
# For CUDA support
docker build --build-arg CUDA_ENABLED=true -t ocr-service .

# For MPS support (Mac users)
docker build --build-arg MPS_ENABLED=true -t ocr-service .
```

## Model Caching

The OCR service Dockerfile uses a multi-stage build approach:

1. First stage downloads and caches OCR models
2. Second stage copies the cached models
3. This ensures models are part of the Docker layer cache and don't need to be downloaded on each container start

## Benefits

1. **Reduced Container Size**: Main backend container is much smaller without CUDA/PyTorch dependencies
2. **Flexibility**: Users can choose whether to deploy the OCR service based on their needs
3. **Performance**: OCR processing is isolated and won't affect main backend performance
4. **Scalability**: OCR service can be scaled independently
5. **Hardware Support**: Better support for different hardware configurations (CPU/CUDA/MPS)

## Usage

To use the OCR functionality:

1. Ensure the OCR service is running alongside the main backend
2. The backend will automatically make HTTP calls to the OCR service when processing scanned PDFs
3. Users can disable the OCR service entirely if not needed by not deploying it

## Future Improvements

1. Add authentication between services
2. Implement circuit breaker pattern for service resilience
3. Add metrics and monitoring for the OCR service
4. Support additional OCR engines beyond EasyOCR