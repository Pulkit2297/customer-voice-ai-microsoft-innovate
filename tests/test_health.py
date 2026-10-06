"""Tests for health check endpoint."""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check_status_code():
    """Verify that /health returns HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_payload():
    """Verify that /health returns expected payload."""
    response = client.get("/health")
    assert response.json() == {
        "status": "healthy",
        "service": "CustomerVoice AI",
    }
