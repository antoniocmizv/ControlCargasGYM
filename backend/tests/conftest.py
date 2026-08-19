import os
import tempfile
from collections.abc import Iterator

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["SECRET_KEY"] = "clave-de-test"
os.environ["COACH_USERNAME"] = "entrenador"
os.environ["COACH_PASSWORD"] = "test1234"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def coach_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login/coach", json={"username": "entrenador", "password": "test1234"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
