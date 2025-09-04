# Use Python 3.11 slim image
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

# Set environment variables for CPU-only packages
ARG CUDA_ENABLED=false
RUN if [ "$CUDA_ENABLED" = "false" ]; then \
    export TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu && \
    export FORCE_CUDA=0 ; \
    fi

# Copy dependency files and README
COPY pyproject.toml uv.lock* README.md ./

# Install Python dependencies using UV
# Update lock and install Python deps
RUN uv lock --upgrade && uv sync --frozen

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Start the application
CMD ["uv", "run", "uvicorn", "oracle.main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "300", "--timeout-graceful-shutdown", "300", "--limit-concurrency", "1000", "--backlog", "2048"]