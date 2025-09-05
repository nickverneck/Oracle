# Multi-stage build for Ingestion Service
# Stage 1: Download models
FROM python:3.11-slim as model-downloader

# Install system dependencies needed for model download
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

# Set environment variables for CPU-only packages by default
ARG CUDA_ENABLED=false
ARG MPS_ENABLED=false

# Configure PyTorch installation based on target device
RUN if [ "$CUDA_ENABLED" = "true" ]; then \
    echo "Installing CUDA-enabled PyTorch"; \
    elif [ "$MPS_ENABLED" = "true" ]; then \
    echo "Installing MPS-enabled PyTorch (default)"; \
    else \
    echo "Installing CPU-only PyTorch"; \
    export TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu && \
    export FORCE_CUDA=0; \
    fi

# Create directory for models
RUN mkdir -p /models

# Install PyTorch and EasyOCR for model downloading
# We use a minimal requirements file with just what we need for OCR model download
RUN echo 'torch>=2.0.0' > download-requirements.txt && \
    echo 'torchvision>=0.15.0' >> download-requirements.txt && \
    echo 'easyocr>=1.7.1' >> download-requirements.txt && \
    uv pip install --system --no-cache-dir -r download-requirements.txt

# Download default models (English and common languages)
# This ensures models are cached in the Docker layer
RUN python -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False, download_enabled=True, model_storage_directory='/models')"

# Stage 2: Application
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

# Set environment variables for PyTorch based on build args
ARG CUDA_ENABLED=false
ARG MPS_ENABLED=false

# Configure PyTorch installation based on target device
RUN if [ "$CUDA_ENABLED" = "true" ]; then \
    echo "Installing CUDA-enabled PyTorch"; \
    export TORCH_INDEX_URL=https://download.pytorch.org/whl/cu118; \
    elif [ "$MPS_ENABLED" = "true" ]; then \
    echo "Installing MPS-enabled PyTorch (default)"; \
    else \
    echo "Installing CPU-only PyTorch"; \
    export TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu && \
    export FORCE_CUDA=0; \
    fi

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Copy models from the first stage
COPY --from=model-downloader /models /models

# Copy ingestion service application code
COPY ingestion_service.py ./

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Set environment variable for model storage
ENV EASYOCR_MODULE_PATH=/models

# Start the ingestion service
CMD ["uv", "run", "uvicorn", "ingestion_service:app", "--host", "0.0.0.0", "--port", "8081"]