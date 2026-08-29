"""Anotaciones: el peso que el entrenador le marca a cada jugador."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers

DIA = date.today() - timedelta(days=500)


@pytest.fixture
def sesion(client: TestClient, coach_headers: dict) -> dict:
    jugadores = [
        client.post(
            "/api/coach/players", json={"name": nombre, "pin": pin}, headers=coach_headers
        ).json()
        for nombre, pin in [("Anota Ana", "1414"), ("Anota Luis", "1515")]
    ]
    ejercicios = client.get("/api/coach/exercises", headers=coach_headers).json()

    routine = client.post(
        "/api/coach/routines",
        headers=coach_headers,
        json={
            "name": "Con anotaciones",
            "session_date": str(DIA),
            "items": [
                {"exercise_id": ejercicios[0]["id"], "sets": 3, "target_reps": 8},
                {"exercise_id": ejercicios[1]["id"], "sets": 2, "target_reps": 10},
            ],
            "assignments": [
                {"target_type": "player", "user_id": j["id"]} for j in jugadores
            ],
        },
    ).json()

    def entra(jugador, pin):
        return auth_headers(
            client.post(
                "/api/auth/login/player", json={"user_id": jugador["id"], "pin": pin}
            ).json()["access_token"]
        )

    return {
        "routine": routine,
        "ana": jugadores[0],
        "luis": jugadores[1],
        "ana_h": entra(jugadores[0], "1414"),
        "luis_h": entra(jugadores[1], "1515"),
    }


def _anota(client, coach_headers, sesion, entradas):
    return client.put(
        f"/api/coach/routines/{sesion['routine']['id']}/anotaciones",
        headers=coach_headers,
        json=entradas,
    )


def test_el_jugador_ve_solo_su_anotacion(client: TestClient, coach_headers: dict, sesion: dict):
    item = sesion["routine"]["items"][0]["id"]
    respuesta = _anota(
        client,
        coach_headers,
        sesion,
        [
            {
                "routine_exercise_id": item,
                "user_id": sesion["ana"]["id"],
                "target_load_kg": 80,
                "note": "Sube 2,5 si sale fácil",
            },
            {
                "routine_exercise_id": item,
                "user_id": sesion["luis"]["id"],
                "target_load_kg": 100,
            },
        ],
    )
    assert respuesta.status_code == 200

    de_ana = client.get(
        "/api/routines/today", params={"day": str(DIA)}, headers=sesion["ana_h"]
    ).json()[0]["items"][0]["prescription"]
    assert de_ana["target_load_kg"] == 80.0
    assert de_ana["note"] == "Sube 2,5 si sale fácil"

    de_luis = client.get(
        "/api/routines/today", params={"day": str(DIA)}, headers=sesion["luis_h"]
    ).json()[0]["items"][0]["prescription"]
    assert de_luis["target_load_kg"] == 100.0
    assert de_luis["note"] is None


def test_sin_anotacion_el_campo_viene_vacio(client: TestClient, sesion: dict):
    segundo = client.get(
        "/api/routines/today", params={"day": str(DIA)}, headers=sesion["ana_h"]
    ).json()[0]["items"][1]
    assert segundo["prescription"] is None


def test_una_anotacion_vacia_la_borra(client: TestClient, coach_headers: dict, sesion: dict):
    item = sesion["routine"]["items"][0]["id"]
    _anota(
        client,
        coach_headers,
        sesion,
        [{"routine_exercise_id": item, "user_id": sesion["ana"]["id"], "target_load_kg": 80}],
    )

    _anota(
        client,
        coach_headers,
        sesion,
        [
            {
                "routine_exercise_id": item,
                "user_id": sesion["ana"]["id"],
                "target_load_kg": None,
                "note": "   ",
            }
        ],
    )

    guardadas = client.get(
        f"/api/coach/routines/{sesion['routine']['id']}/anotaciones", headers=coach_headers
    ).json()
    assert guardadas == []


def test_reenviar_una_anotacion_la_actualiza(
    client: TestClient, coach_headers: dict, sesion: dict
):
    item = sesion["routine"]["items"][0]["id"]
    for kg in (80, 85):
        _anota(
            client,
            coach_headers,
            sesion,
            [{"routine_exercise_id": item, "user_id": sesion["ana"]["id"], "target_load_kg": kg}],
        )

    guardadas = client.get(
        f"/api/coach/routines/{sesion['routine']['id']}/anotaciones", headers=coach_headers
    ).json()
    assert len(guardadas) == 1
    assert guardadas[0]["target_load_kg"] == 85.0


def test_el_seguimiento_muestra_lo_anotado(
    client: TestClient, coach_headers: dict, sesion: dict
):
    item = sesion["routine"]["items"][0]["id"]
    _anota(
        client,
        coach_headers,
        sesion,
        [
            {
                "routine_exercise_id": item,
                "user_id": sesion["ana"]["id"],
                "target_load_kg": 80,
                "note": "Técnica",
            }
        ],
    )

    vivo = client.get(
        f"/api/coach/routines/{sesion['routine']['id']}/live", headers=coach_headers
    ).json()
    ana = next(p for p in vivo["players"] if p["player_id"] == sesion["ana"]["id"])
    assert ana["exercises"][0]["target_load_kg"] == 80.0
    assert ana["exercises"][0]["note"] == "Técnica"


def test_no_se_anota_en_un_ejercicio_de_otra_bateria(
    client: TestClient, coach_headers: dict, sesion: dict
):
    ejercicio = client.get("/api/coach/exercises", headers=coach_headers).json()[0]
    otra = client.post(
        "/api/coach/routines",
        headers=coach_headers,
        json={
            "name": "Ajena",
            "session_date": str(DIA),
            "items": [{"exercise_id": ejercicio["id"], "sets": 1}],
            "assignments": [{"target_type": "all"}],
        },
    ).json()

    respuesta = _anota(
        client,
        coach_headers,
        sesion,
        [
            {
                "routine_exercise_id": otra["items"][0]["id"],
                "user_id": sesion["ana"]["id"],
                "target_load_kg": 50,
            }
        ],
    )
    assert respuesta.status_code == 400


def test_un_jugador_no_puede_anotar(client: TestClient, sesion: dict):
    respuesta = client.put(
        f"/api/coach/routines/{sesion['routine']['id']}/anotaciones",
        headers=sesion["ana_h"],
        json=[
            {
                "routine_exercise_id": sesion["routine"]["items"][0]["id"],
                "user_id": sesion["ana"]["id"],
                "target_load_kg": 200,
            }
        ],
    )
    assert respuesta.status_code == 403


def test_quitar_todas_las_de_un_jugador(client: TestClient, coach_headers: dict, sesion: dict):
    for item in sesion["routine"]["items"]:
        _anota(
            client,
            coach_headers,
            sesion,
            [{"routine_exercise_id": item["id"], "user_id": sesion["ana"]["id"], "target_load_kg": 60}],
        )

    respuesta = client.delete(
        f"/api/coach/routines/{sesion['routine']['id']}/anotaciones/{sesion['ana']['id']}",
        headers=coach_headers,
    )
    assert respuesta.status_code == 204

    guardadas = client.get(
        f"/api/coach/routines/{sesion['routine']['id']}/anotaciones", headers=coach_headers
    ).json()
    assert guardadas == []
