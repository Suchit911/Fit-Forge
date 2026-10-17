from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Tests the root API endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["health"] == "/health"


def test_root_health_endpoint(client: TestClient):
    """Tests the /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "AI FITNESS API"
    assert data["version"] == "1.0.0"
    assert "environment" in data
    assert "timestamp" in data
    assert "firebase_connected" in data


def test_v1_health_endpoint(client: TestClient):
    """Tests the /api/v1/health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "AI FITNESS API"
    assert data["firebase_connected"] is True


def test_firebase_initialization_status(client: TestClient):
    """Tests that Firebase Admin SDK is verified as initialized and connected."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["firebase_connected"] is True



def test_cors_preflight(client: TestClient):
    """Tests that CORS headers are appropriately handled."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
