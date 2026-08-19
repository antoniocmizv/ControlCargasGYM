"""Flujo completo: el entrenador da de alta la sesion y el jugador registra cargas."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers

TODAY = date.today().isoformat()


@pytest.fixture(scope="module")
def equipo(client: TestClient, coach_headers: dict) -> dict:
    group = client.post("/api/coach/groups", json={"name": "Grupo A"}, headers=coach_headers).json()
    portero = client.post(
        "/api/coach/players",
        json={"name": "Ana Portera", "pin": "1234", "group_ids": [group["id"]]},
        headers=coach_headers,
    ).json()
    suplente = client.post(
        "/api/coach/players", json={"name": "Luis Suplente", "pin": "5678"}, headers=coach_headers
    ).json()

    ejercicios = client.get("/api/coach/exercises", headers=coach_headers).json()
    rutina = client.post(
        "/api/coach/routines",
        headers=coach_headers,
        json={
            "name": "Fuerza tren inferior",
            "session_date": TODAY,
            "items": [
                {"exercise_id": ejercicios[0]["id"], "sets": 3, "target_reps": 8, "rest_seconds": 120},
                {"exercise_id": ejercicios[1]["id"], "sets": 2, "target_reps": 10},
            ],
            "assignments": [{"target_type": "group", "group_id": group["id"]}],
        },
    ).json()

    return {
        "group": group,
        "rutina": rutina,
        "portero": auth_headers(
            client.post(
                "/api/auth/login/player", json={"user_id": portero["id"], "pin": "1234"}
            ).json()["access_token"]
        ),
        "suplente": auth_headers(
            client.post(
                "/api/auth/login/player", json={"user_id": suplente["id"], "pin": "5678"}
            ).json()["access_token"]
        ),
        "portero_id": portero["id"],
    }


def test_la_bateria_solo_la_ve_el_grupo_asignado(client: TestClient, equipo: dict):
    asignada = client.get("/api/routines/today", headers=equipo["portero"]).json()
    assert asignada is not None
    assert asignada["id"] == equipo["rutina"]["id"]
    assert len(asignada["items"]) == 2

    assert client.get("/api/routines/today", headers=equipo["suplente"]).json() is None


def test_registrar_y_corregir_cargas(client: TestClient, equipo: dict):
    item_id = equipo["rutina"]["items"][0]["id"]

    for numero, kg, reps in [(1, 60, 8), (2, 65, 8), (3, 70, 6)]:
        response = client.post(
            "/api/logs",
            headers=equipo["portero"],
            json={"routine_exercise_id": item_id, "set_number": numero, "load_kg": kg, "reps": reps},
        )
        assert response.status_code == 200

    # Reenviar la misma serie corrige el valor en lugar de duplicar el registro.
    client.post(
        "/api/logs",
        headers=equipo["portero"],
        json={"routine_exercise_id": item_id, "set_number": 1, "load_kg": 62.5, "reps": 8},
    )

    logs = client.get("/api/routines/today", headers=equipo["portero"]).json()["items"][0]["logs"]
    assert [(log["set_number"], log["load_kg"]) for log in logs] == [(1, 62.5), (2, 65.0), (3, 70.0)]


def test_no_se_puede_registrar_una_serie_fuera_de_rango(client: TestClient, equipo: dict):
    response = client.post(
        "/api/logs",
        headers=equipo["portero"],
        json={"routine_exercise_id": equipo["rutina"]["items"][0]["id"], "set_number": 9, "load_kg": 50},
    )
    assert response.status_code == 400


def test_no_se_puede_registrar_en_una_bateria_ajena(client: TestClient, equipo: dict):
    response = client.post(
        "/api/logs",
        headers=equipo["suplente"],
        json={"routine_exercise_id": equipo["rutina"]["items"][0]["id"], "set_number": 1, "load_kg": 50},
    )
    assert response.status_code == 403


def test_un_jugador_no_entra_al_panel_del_entrenador(client: TestClient, equipo: dict):
    assert client.get("/api/coach/players", headers=equipo["portero"]).status_code == 403
    assert client.get("/api/export/excel", headers=equipo["portero"]).status_code == 403


def test_progreso_de_la_bateria(client: TestClient, coach_headers: dict, equipo: dict):
    progreso = client.get(
        f"/api/coach/routines/{equipo['rutina']['id']}/progress", headers=coach_headers
    ).json()
    fila = next(row for row in progreso["rows"] if row["player_id"] == equipo["portero_id"])
    assert fila["total_sets"] == 5
    assert fila["logged_sets"] == 3


def test_historial_muestra_la_carga_de_la_sesion_anterior(
    client: TestClient, coach_headers: dict, equipo: dict
):
    ejercicio_id = equipo["rutina"]["items"][0]["exercise"]["id"]
    anterior = client.post(
        "/api/coach/routines",
        headers=coach_headers,
        json={
            "name": "Semana pasada",
            "session_date": (date.today() - timedelta(days=7)).isoformat(),
            "items": [{"exercise_id": ejercicio_id, "sets": 1, "target_reps": 8}],
            "assignments": [{"target_type": "all"}],
        },
    ).json()

    client.post(
        "/api/logs",
        headers=equipo["portero"],
        json={"routine_exercise_id": anterior["items"][0]["id"], "set_number": 1, "load_kg": 55, "reps": 8},
    )

    hoy = client.get("/api/routines/today", headers=equipo["portero"]).json()
    assert hoy["items"][0]["last_performance"]["best_load_kg"] == 55.0


def test_duplicar_bateria_a_otra_fecha(client: TestClient, coach_headers: dict, equipo: dict):
    manana = (date.today() + timedelta(days=1)).isoformat()
    response = client.post(
        f"/api/coach/routines/{equipo['rutina']['id']}/duplicate?session_date={manana}",
        headers=coach_headers,
    )
    assert response.status_code == 201
    copia = response.json()
    assert copia["session_date"] == manana
    assert len(copia["items"]) == len(equipo["rutina"]["items"])
    assert len(copia["assignments"]) == 1


def test_una_bateria_sin_ejercicios_es_rechazada(client: TestClient, coach_headers: dict):
    response = client.post(
        "/api/coach/routines",
        headers=coach_headers,
        json={
            "name": "Vacia",
            "session_date": TODAY,
            "items": [],
            "assignments": [{"target_type": "all"}],
        },
    )
    assert response.status_code == 400
