# Multi-stage build for OCR service
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
RUN if [ \"$CUDA_ENABLED\" = \"true\" ]; then \
    echo \"Installing CUDA-enabled PyTorch\"; \
    elif [ \"$MPS_ENABLED\" = \"true\" ]; then \
    echo \"Installing MPS-enabled PyTorch (default)\"; \
    else \
    echo \"Installing CPU-only PyTorch\"; \
    export TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu && \
    export FORCE_CUDA=0; \
    fi

# Copy dependency files
COPY ../pyproject.toml ../uv.lock* ./

# Create directory for models
RUN mkdir -p /models

# Install EasyOCR and download models
# We use a minimal requirements file with just what we need for OCR
RUN echo 'easyocr>=1.7.1' > ocr-requirements.txt && \
    uv pip install --no-cache-dir -r ocr-requirements.txt

# Download default models (English and common languages)
# This ensures models are cached in the Docker layer
RUN python -c \"import easyocr; reader = easyocr.Reader(['en'], gpu=False, download_enabled=True, model_storage_directory='/models')\"

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
RUN if [ \"$CUDA_ENABLED\" = \"true\" ]; then \
    echo \"Installing CUDA-enabled PyTorch\"; \
    elif [ \"$MPS_ENABLED\" = \"true\" ]; then \
    echo \"Installing MPS-enabled PyTorch (default)\"; \
    else \
    echo \"Installing CPU-only PyTorch\"; \
    export TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu && \
    export FORCE_CUDA=0; \
    fi

# Copy only OCR-related dependencies
RUN echo 'easyocr>=1.7.1' > ocr-requirements.txt && \
    echo 'numpy>=1.26.0' >> ocr-requirements.txt && \
    echo 'fastapi>=0.104.0' >> ocr-requirements.txt && \
    echo 'uvicorn[standard]>=0.24.0' >> ocr-requirements.txt && \
    echo 'pydantic>=2.5.0' >> ocr-requirements.txt && \
    echo 'aiofiles>=23.2.0' >> ocr-requirements.txt && \
    echo 'python-multipart>=0.0.6' >> ocr-requirements.txt

# Install Python dependencies
RUN uv pip install --no-cache-dir -r ocr-requirements.txt

# Copy models from the first stage
COPY --from=model-downloader /models /models

# Copy OCR service application code
COPY ocr_service.py ./

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

# Start the OCR service
CMD [\"uv\", \"run\", \"uvicorn\", \"ocr_service:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8081\"]