"""Entrenador principal, entrenadores normales y cambio de contraseña."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers

DIA = date.today() - timedelta(days=400)


def _entra(client: TestClient, usuario: str, clave: str):
    respuesta = client.post(
        "/api/auth/login/coach", json={"username": usuario, "password": clave}
    )
    assert respuesta.status_code == 200, respuesta.text
    return auth_headers(respuesta.json()["access_token"]), respuesta.json()["user"]


@pytest.fixture
def ayudante(client: TestClient, coach_headers: dict, request) -> dict:
    """
    Un entrenador normal, creado por el principal.

    Usuario distinto en cada prueba: comparten base y alguna lo desactiva o le
    cambia la contraseña, así que reutilizarlo las haría depender del orden.
    """
    usuario = f"ayudante-{abs(hash(request.node.name)) % 100000}"
    creado = client.post(
        "/api/coach/staff",
        headers=coach_headers,
        json={"name": "Ayudante Pérez", "username": usuario, "password": "clavesegura1"},
    )
    assert creado.status_code == 201, creado.text
    headers, datos = _entra(client, usuario, "clavesegura1")
    return {"headers": headers, "user": datos, "id": creado.json()["id"], "usuario": usuario}


# ---------- el principal ----------
def test_el_entrenador_existente_pasa_a_principal(client: TestClient, coach_headers: dict):
    """En una instalación que ya venía funcionando, se promociona al veterano."""
    yo = client.get("/api/auth/me", headers=coach_headers).json()
    assert yo["role"] == "admin"


def test_solo_el_principal_gestiona_entrenadores(client: TestClient, ayudante: dict):
    assert client.get("/api/coach/staff", headers=ayudante["headers"]).status_code == 403

    respuesta = client.post(
        "/api/coach/staff",
        headers=ayudante["headers"],
        json={"name": "Otro", "username": "otro", "password": "clavesegura1"},
    )
    assert respuesta.status_code == 403


def test_no_se_puede_repetir_el_usuario(client: TestClient, coach_headers: dict, ayudante: dict):
    respuesta = client.post(
        "/api/coach/staff",
        headers=coach_headers,
        json={"name": "Duplicado", "username": ayudante["usuario"], "password": "clavesegura1"},
    )
    assert respuesta.status_code == 409


def test_el_principal_no_puede_ser_desactivado(client: TestClient, coach_headers: dict):
    yo = client.get("/api/auth/me", headers=coach_headers).json()
    respuesta = client.patch(
        f"/api/coach/staff/{yo['id']}", headers=coach_headers, json={"is_active": False}
    )
    assert respuesta.status_code == 400


# ---------- lo que sí puede un entrenador normal ----------
def test_un_entrenador_normal_crea_sesiones_y_ve_los_pesos(
    client: TestClient, coach_headers: dict, ayudante: dict
):
    jugador = client.post(
        "/api/coach/players",
        headers=ayudante["headers"],
        json={"name": "De Ayudante", "pin": "5555"},
    )
    assert jugador.status_code == 201, "un entrenador normal gestiona la plantilla"

    ejercicio = client.get("/api/coach/exercises", headers=ayudante["headers"]).json()[0]
    routine = client.post(
        "/api/coach/routines",
        headers=ayudante["headers"],
        json={
            "name": "De un ayudante",
            "session_date": str(DIA),
            "items": [{"exercise_id": ejercicio["id"], "sets": 2}],
            "assignments": [{"target_type": "player", "user_id": jugador.json()["id"]}],
        },
    )
    assert routine.status_code == 201

    vivo = client.get(
        f"/api/coach/routines/{routine.json()['id']}/live", headers=ayudante["headers"]
    )
    assert vivo.status_code == 200, "también ve los pesos en vivo"

    assert client.get("/api/export/excel", headers=ayudante["headers"]).status_code == 200


def test_el_principal_ve_las_sesiones_del_ayudante(
    client: TestClient, coach_headers: dict, ayudante: dict
):
    ejercicio = client.get("/api/coach/exercises", headers=ayudante["headers"]).json()[0]
    creada = client.post(
        "/api/coach/routines",
        headers=ayudante["headers"],
        json={
            "name": "Compartida",
            "session_date": str(DIA),
            "items": [{"exercise_id": ejercicio["id"], "sets": 1}],
            "assignments": [{"target_type": "all"}],
        },
    ).json()

    del_principal = client.get("/api/coach/routines", headers=coach_headers).json()
    assert creada["id"] in [r["id"] for r in del_principal]


# ---------- desactivar ----------
def test_un_entrenador_desactivado_deja_de_entrar(
    client: TestClient, coach_headers: dict, ayudante: dict
):
    client.delete(f"/api/coach/staff/{ayudante['id']}", headers=coach_headers)

    assert client.get("/api/coach/routines", headers=ayudante["headers"]).status_code == 401
    assert (
        client.post(
            "/api/auth/login/coach",
            json={"username": ayudante["usuario"], "password": "clavesegura1"},
        ).status_code
        == 401
    )


# ---------- contraseña ----------
def test_cambiar_la_propia_contrasena(client: TestClient, ayudante: dict):
    respuesta = client.post(
        "/api/coach/password",
        headers=ayudante["headers"],
        json={"current_password": "clavesegura1", "new_password": "otraclave99"},
    )
    assert respuesta.status_code == 204

    assert (
        client.post(
            "/api/auth/login/coach",
            json={"username": ayudante["usuario"], "password": "clavesegura1"},
        ).status_code
        == 401
    ), "la vieja deja de valer"
    _entra(client, ayudante["usuario"], "otraclave99")


def test_hace_falta_la_contrasena_actual(client: TestClient, ayudante: dict):
    respuesta = client.post(
        "/api/coach/password",
        headers=ayudante["headers"],
        json={"current_password": "la-que-no-es", "new_password": "otraclave99"},
    )
    assert respuesta.status_code == 400


def test_la_nueva_contrasena_tiene_un_minimo(client: TestClient, ayudante: dict):
    respuesta = client.post(
        "/api/coach/password",
        headers=ayudante["headers"],
        json={"current_password": "clavesegura1", "new_password": "corta"},
    )
    assert respuesta.status_code == 422


def test_un_jugador_no_toca_la_contrasena_de_entrenador(
    client: TestClient, coach_headers: dict
):
    jugador = client.post(
        "/api/coach/players", json={"name": "Curioso", "pin": "6767"}, headers=coach_headers
    ).json()
    headers = auth_headers(
        client.post(
            "/api/auth/login/player", json={"user_id": jugador["id"], "pin": "6767"}
        ).json()["access_token"]
    )

    respuesta = client.post(
        "/api/coach/password",
        headers=headers,
        json={"current_password": "x", "new_password": "clavesegura1"},
    )
    assert respuesta.status_code == 403
    assert client.get("/api/coach/staff", headers=headers).status_code == 403
