# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

# Set environment variables for CPU-only packages
ENV TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ENV FORCE_CUDA=0

# Copy dependency files and README
COPY pyproject.toml uv.lock* README.md ./

# Install Python dependencies using UV
RUN uv sync --frozen

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["uv", "run", "uvicorn", "oracle.main:app", "--host", "0.0.0.0", "--port", "8000"]