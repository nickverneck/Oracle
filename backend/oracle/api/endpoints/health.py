"""Health check endpoints."""

from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from oracle.core.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, Any]


class ServiceStatus(BaseModel):
    """Individual service status model."""
    status: str
    message: str
    response_time_ms: float


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns the overall system health status.
    """
    logger.info("Health check requested")
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0",
        services={
            "api": {
                "status": "healthy",
                "message": "FastAPI backend is running",
                "response_time_ms": 0.0
            }
        }
    )


@router.get("/detailed", response_model=HealthResponse)
async def detailed_health_check() -> HealthResponse:
    """
    Detailed health check endpoint that tests external service connectivity.
    
    This endpoint will be enhanced in future tasks to check:
    - vLLM service connectivity
    - Neo4j database connectivity  
    - ChromaDB connectivity
    - Ollama service connectivity (if configured)
    """
    logger.info("Detailed health check requested")
    
    settings = get_settings()
    services = {
        "api": ServiceStatus(
            status="healthy",
            message="FastAPI backend is running",
            response_time_ms=0.0
        ),
        "vllm": ServiceStatus(
            status="unknown",
            message=f"Service check not implemented (URL: {settings.VLLM_BASE_URL})",
            response_time_ms=0.0
        ),
        "neo4j": ServiceStatus(
            status="unknown", 
            message=f"Service check not implemented (URI: {settings.NEO4J_URI})",
            response_time_ms=0.0
        ),
        "chromadb": ServiceStatus(
            status="unknown",
            message=f"Service check not implemented (Host: {settings.CHROMADB_HOST}:{settings.CHROMADB_PORT})",
            response_time_ms=0.0
        )
    }
    
    # Overall status is healthy if API is running
    # This will be enhanced to check all services in future tasks
    overall_status = "healthy"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="0.1.0",
        services=services
    )


@router.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """
    Kubernetes-style readiness probe.
    
    Returns 200 if the service is ready to accept traffic.
    """
    logger.debug("Readiness check requested")
    return {"status": "ready"}


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if the service is alive and running.
    """
    logger.debug("Liveness check requested")
    return {"status": "alive"}