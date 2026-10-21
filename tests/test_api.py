"""
API endpoint integration tests using FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from src.glycorisk.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_health_endpoint(client):
    """Verify that the health check endpoint returns 200 OK and expected keys."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "engine" in data


def test_api_metadata_endpoint(client):
    """Verify that the metadata endpoint supplies the complete clinical schema."""
    response = client.get("/api/metadata")
    assert response.status_code == 200
    data = response.json()
    assert len(data["features"]) == 8
    assert "Glucose" in data["features"]
    assert "risk_tiers" in data


def test_api_dashboard_html_served(client):
    """Verify that the root endpoint serves valid HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "GLYCORISK AI" in response.text
    assert "styles.css" in response.text
