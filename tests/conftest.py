import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_query():
    return "What are the different perspectives on climate change policy?"
