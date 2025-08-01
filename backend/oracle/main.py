"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from oracle.api.routes import api_router
from oracle.core.config import get_settings
from oracle.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger = structlog.get_logger()
    logger.info("Starting Oracle Chatbot System Backend")
    
    # Application startup logic can be added here
    yield
    
    # Application shutdown logic can be added here
    logger.info("Shutting down Oracle Chatbot System Backend")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging()
    
    app = FastAPI(
        title="Oracle Chatbot System API",
        description="AI-powered troubleshooting chatbot with hybrid knowledge retrieval",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Configure trusted host middleware (add testserver for testing)
    allowed_hosts = settings.ALLOWED_HOSTS + ["testserver"]
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    return app


# Create the application instance
app = create_app()