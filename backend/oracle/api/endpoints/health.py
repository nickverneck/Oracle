"""Health check endpoints."""

from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from oracle.core.config import get_settings
from oracle.services.knowledge import KnowledgeRetrievalService
from oracle.clients.model_manager import ModelManager

logger = structlog.get_logger(__name__)
router = APIRouter()

# Global knowledge service instance for health checks
knowledge_service = None


def get_knowledge_service() -> KnowledgeRetrievalService:
    """Get knowledge retrieval service instance for health checks."""
    global knowledge_service
    if knowledge_service is None:
        settings = get_settings()
        config = {
            "neo4j": {
                "uri": getattr(settings, "NEO4J_URI", "bolt://localhost:7687"),
                "username": getattr(settings, "NEO4J_USERNAME", "neo4j"),
                "password": getattr(settings, "NEO4J_PASSWORD", "password")
            },
            "chromadb": {
                "host": getattr(settings, "CHROMADB_HOST", "localhost"),
                "port": getattr(settings, "CHROMADB_PORT", 8002)
            },
            "retrieval": {
                "max_graph_results": 5,
                "max_vector_results": 5,
                "similarity_threshold": 0.7
            }
        }
        knowledge_service = KnowledgeRetrievalService(config)
    return knowledge_service


async def _check_chromadb_health(knowledge_service: KnowledgeRetrievalService) -> "ServiceStatus":
    """Check ChromaDB health status."""
    start_time = datetime.utcnow()
    
    try:
        # Check ChromaDB availability
        await knowledge_service._ensure_chromadb_availability()
        
        if knowledge_service._chromadb_available:
            # Get additional stats if available
            stats = await knowledge_service.get_vector_db_stats()
            document_count = stats.get("document_count", 0)
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ServiceStatus(
                status="healthy",
                message=f"ChromaDB is accessible with {document_count} documents",
                response_time_ms=response_time
            )
        else:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ServiceStatus(
                status="unhealthy",
                message="ChromaDB is not available",
                response_time_ms=response_time
            )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        return ServiceStatus(
            status="error",
            message=f"ChromaDB health check failed: {str(e)}",
            response_time_ms=response_time
        )


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
async def health_check(
    knowledge_service: KnowledgeRetrievalService = Depends(get_knowledge_service)
) -> HealthResponse:
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
        "chromadb": await _check_chromadb_health(knowledge_service)
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


@router.get("/models", response_model=HealthResponse)
async def model_providers_health() -> HealthResponse:
    """
    Check health status of all model providers.
    
    This endpoint tests connectivity to vLLM, Ollama, and Gemini APIs
    and shows which providers are available for fallback.
    """
    logger.info("Model providers health check requested")
    
    settings = get_settings()
    
    # Initialize model manager
    config = {
        "vllm": {
            "base_url": getattr(settings, "VLLM_BASE_URL", "http://localhost:8001"),
            "api_key": getattr(settings, "VLLM_API_KEY", ""),
            "model": getattr(settings, "VLLM_MODEL", "microsoft/DialoGPT-medium")
        },
        "ollama": {
            "base_url": getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": getattr(settings, "OLLAMA_MODEL", "llama2")
        },
        "gemini": {
            "api_key": getattr(settings, "GEMINI_API_KEY", ""),
            "model": getattr(settings, "GEMINI_MODEL", "gemini-pro")
        },
        "fallback_order": ["vllm", "ollama", "gemini"]
    }
    
    model_manager = ModelManager(config)
    services = {}
    
    # Check each provider
    for provider_name in ["vllm", "ollama", "gemini"]:
        start_time = datetime.utcnow()
        client = model_manager.clients.get(provider_name)
        
        if not client:
            services[provider_name] = ServiceStatus(
                status="not_configured",
                message=f"{provider_name.upper()} client not configured",
                response_time_ms=0.0
            )
            continue
        
        try:
            # Try health check if available
            if hasattr(client, 'health_check'):
                is_healthy = await client.health_check()
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if is_healthy:
                    services[provider_name] = ServiceStatus(
                        status="healthy",
                        message=f"{provider_name.upper()} is available",
                        response_time_ms=response_time
                    )
                else:
                    services[provider_name] = ServiceStatus(
                        status="unhealthy",
                        message=f"{provider_name.upper()} health check failed",
                        response_time_ms=response_time
                    )
            else:
                services[provider_name] = ServiceStatus(
                    status="configured",
                    message=f"{provider_name.upper()} client configured but health check not available",
                    response_time_ms=0.0
                )
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            services[provider_name] = ServiceStatus(
                status="error",
                message=f"{provider_name.upper()} error: {str(e)}",
                response_time_ms=response_time
            )
    
    # Determine overall status
    healthy_providers = [name for name, status in services.items() if status.status == "healthy"]
    configured_providers = [name for name, status in services.items() if status.status in ["healthy", "configured"]]
    
    if healthy_providers:
        overall_status = "healthy"
        status_message = f"At least one provider available: {', '.join(healthy_providers)}"
    elif configured_providers:
        overall_status = "degraded"
        status_message = f"Providers configured but health unknown: {', '.join(configured_providers)}"
    else:
        overall_status = "unhealthy"
        status_message = "No model providers available"
    
    services["overall"] = ServiceStatus(
        status=overall_status,
        message=status_message,
        response_time_ms=0.0
    )
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="0.1.0",
        services=services
    )