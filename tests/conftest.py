import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
TEMP = tempfile.TemporaryDirectory()
os.environ.update(
    JWT_SECRET="test-only-secret-" * 4,
    DATABASE_URL=f"sqlite:///{TEMP.name}/test.db",
    STORAGE_DIR=f"{TEMP.name}/storage",
    MAX_UPLOAD_MB="1",
)
sys.path.insert(0, str(ROOT / "backend"))
from app import app


@pytest.fixture
def client():
    with TestClient(app) as instance:
        yield instance


def account(client, email):
    response = client.post("/auth/register", json={"email": email, "password": "SamplePass123"})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}
