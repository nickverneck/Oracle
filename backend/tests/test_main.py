"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from oracle.main import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    app = create_app()
    return TestClient(app)


def test_app_creation():
    """Test that the FastAPI app can be created successfully."""
    app = create_app()
    assert app.title == "Oracle Chatbot System API"
    assert app.version == "0.1.0"


def test_health_check(client):
    """Test the basic health check endpoint."""
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data
    assert "services" in data
    assert data["services"]["api"]["status"] == "healthy"


def test_detailed_health_check(client):
    """Test the detailed health check endpoint."""
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data
    assert "api" in data["services"]
    assert "vllm" in data["services"]
    assert "neo4j" in data["services"]
    assert "chromadb" in data["services"]


def test_readiness_check(client):
    """Test the readiness probe endpoint."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_liveness_check(client):
    """Test the liveness probe endpoint."""
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_openapi_docs(client):
    """Test that OpenAPI documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    openapi_data = response.json()
    assert openapi_data["info"]["title"] == "Oracle Chatbot System API"