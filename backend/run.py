#!/usr/bin/env python3
"""Development server runner for Oracle backend."""

import uvicorn

from oracle.core.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    uvicorn.run(
        "oracle.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )