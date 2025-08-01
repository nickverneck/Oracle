"""Main API router configuration."""

from fastapi import APIRouter

from oracle.api.endpoints import health

# Create the main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])