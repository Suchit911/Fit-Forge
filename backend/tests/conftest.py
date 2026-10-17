import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Provides a TestClient instance for API tests."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    """Ensures dependency overrides do not leak across tests."""
    yield
    app.dependency_overrides.clear()

