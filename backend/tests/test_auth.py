from fastapi.testclient import TestClient


def test_health(client: TestClient):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_coach_login_ok(coach_headers: dict):
    assert coach_headers["Authorization"].startswith("Bearer ")


def test_coach_login_con_password_incorrecta(client: TestClient):
    response = client.post(
        "/api/auth/login/coach", json={"username": "entrenador", "password": "incorrecta"}
    )
    assert response.status_code == 401


def test_endpoint_protegido_sin_token(client: TestClient):
    assert client.get("/api/coach/players").status_code == 401


def test_lista_publica_de_jugadores_no_expone_pin(client: TestClient, coach_headers: dict):
    client.post(
        "/api/coach/players", json={"name": "Publico Test", "pin": "4321"}, headers=coach_headers
    )
    options = client.get("/api/auth/players").json()
    assert any(option["name"] == "Publico Test" for option in options)
    assert all(set(option) == {"id", "name"} for option in options)


def test_login_jugador_con_pin(client: TestClient, coach_headers: dict):
    player = client.post(
        "/api/coach/players", json={"name": "Login Test", "pin": "1111"}, headers=coach_headers
    ).json()

    assert client.post(
        "/api/auth/login/player", json={"user_id": player["id"], "pin": "9999"}
    ).status_code == 401

    response = client.post("/api/auth/login/player", json={"user_id": player["id"], "pin": "1111"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "player"
