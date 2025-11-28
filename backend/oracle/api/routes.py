"""Main API router configuration."""

from fastapi import APIRouter

from oracle.api.endpoints import health, chat, ingest, models

# Create the main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(models.router, prefix="/models", tags=["models"])

# You can add more endpoint routers here as your application grows
# For example:
# from oracle.api.endpoints import users
# api_router.include_router(users.router, prefix="/users", tags=["users"])

[
    "api_router"
]