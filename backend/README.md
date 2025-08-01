# Oracle Chatbot System Backend

FastAPI-based backend service for the Oracle AI-powered troubleshooting chatbot system.

## Features

- FastAPI application with automatic OpenAPI documentation
- UV package management for fast dependency resolution
- Structured logging with configurable output formats
- CORS middleware configured for frontend communication
- Health check endpoints for monitoring and orchestration
- Pydantic-based configuration management
- Comprehensive test suite

## Quick Start

### Prerequisites

- Python 3.11+
- UV package manager

### Installation

1. Install dependencies:
```bash
uv sync
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Run the development server:
```bash
uv run python run.py
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## API Endpoints

### Health Checks

- `GET /api/v1/health/` - Basic health check
- `GET /api/v1/health/detailed` - Detailed service status
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

### Documentation

- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /openapi.json` - OpenAPI specification

## Configuration

The application uses environment variables for configuration. See `.env.example` for available options:

- **API_HOST**: Server host (default: 0.0.0.0)
- **API_PORT**: Server port (default: 8000)
- **DEBUG**: Enable debug mode (default: false)
- **ALLOWED_ORIGINS**: CORS allowed origins
- **LOG_LEVEL**: Logging level (INFO, DEBUG, WARNING, ERROR)
- **LOG_FORMAT**: Log format (json, console)

## Testing

Run the test suite:

```bash
uv run pytest
```

Run with coverage:

```bash
uv run pytest --cov=oracle --cov-report=html
```

## Development

The application uses:

- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation and settings management
- **Structlog**: Structured logging
- **UV**: Fast Python package installer and resolver

## Docker

The backend can be containerized using the provided Dockerfiles:

- `Dockerfile`: Production build
- `Dockerfile.dev`: Development build with hot reload

## Next Steps

This foundation provides the base structure for:

1. Chat endpoints with AI model integration
2. Document ingestion endpoints
3. Knowledge graph and vector database integration
4. Model serving client implementations
5. Authentication and authorization middleware