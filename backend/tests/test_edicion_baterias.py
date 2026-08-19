"""Editar una batería no debe borrar las cargas que los jugadores ya registraron."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers

TODAY = date.today().isoformat()


@pytest.fixture
def sesion(client: TestClient, coach_headers: dict) -> dict:
    """Batería de 2 ejercicios con un jugador que ya ha registrado cargas."""
    player = client.post(
        "/api/coach/players", json={"name": f"Edita {date.today()}", "pin": "4242"}, headers=coach_headers
    ).json()
    ejercicios = client.get("/api/coach/exercises", headers=coach_headers).json()

    routine = client.post(
        "/api/coach/routines",
        headers=coach_headers,
        json={
            "name": "Sesión original",
            "session_date": TODAY,
            "items": [
                {"exercise_id": ejercicios[0]["id"], "sets": 3, "target_reps": 8},
                {"exercise_id": ejercicios[1]["id"], "sets": 2, "target_reps": 10},
            ],
            "assignments": [{"target_type": "player", "user_id": player["id"]}],
        },
    ).json()

    headers = auth_headers(
        client.post("/api/auth/login/player", json={"user_id": player["id"], "pin": "4242"}).json()[
            "access_token"
        ]
    )
    for numero, kg in [(1, 80), (2, 85), (3, 90)]:
        client.post(
            "/api/logs",
            headers=headers,
            json={"routine_exercise_id": routine["items"][0]["id"], "set_number": numero, "load_kg": kg},
        )

    return {"routine": routine, "player": headers, "player_id": player["id"]}


def _payload(routine: dict, **cambios) -> dict:
    base = {
        "name": routine["name"],
        "session_date": routine["session_date"],
        "items": [
            {
                "id": item["id"],
                "exercise_id": item["exercise"]["id"],
                "sets": item["sets"],
                "target_reps": item["target_reps"],
            }
            for item in routine["items"]
        ],
        "assignments": [
            {"target_type": a["target_type"], "group_id": a["group_id"], "user_id": a["user_id"]}
            for a in routine["assignments"]
        ],
    }
    base.update(cambios)
    return base


def _cargas(client: TestClient, sesion: dict, item_id: int | None = None) -> list:
    """Cargas registradas en un ejercicio concreto de la batería."""
    buscado = item_id or sesion["routine"]["items"][0]["id"]
    hoy = client.get("/api/routines/today", headers=sesion["player"]).json()
    rutina = next(r for r in hoy if r["id"] == sesion["routine"]["id"])
    item = next((i for i in rutina["items"] if i["id"] == buscado), None)
    return item["logs"] if item else []


def test_renombrar_la_sesion_conserva_las_cargas(client: TestClient, coach_headers: dict, sesion: dict):
    client.put(
        f"/api/coach/routines/{sesion['routine']['id']}",
        headers=coach_headers,
        json=_payload(sesion["routine"], name="Sesión renombrada"),
    )

    assert [(log["set_number"], log["load_kg"]) for log in _cargas(client, sesion)] == [
        (1, 80.0),
        (2, 85.0),
        (3, 90.0),
    ]


def test_cambiar_series_y_descanso_conserva_las_cargas(
    client: TestClient, coach_headers: dict, sesion: dict
):
    payload = _payload(sesion["routine"])
    payload["items"][0]["sets"] = 5
    payload["items"][0]["target_reps"] = 6

    client.put(f"/api/coach/routines/{sesion['routine']['id']}", headers=coach_headers, json=payload)

    logs = _cargas(client, sesion)
    assert len(logs) == 3, "ampliar las series no debe tocar lo ya registrado"


def test_recortar_series_borra_solo_las_que_sobran(
    client: TestClient, coach_headers: dict, sesion: dict
):
    payload = _payload(sesion["routine"])
    payload["items"][0]["sets"] = 2

    client.put(f"/api/coach/routines/{sesion['routine']['id']}", headers=coach_headers, json=payload)

    assert [log["set_number"] for log in _cargas(client, sesion)] == [1, 2]


def test_anadir_un_ejercicio_no_afecta_a_los_existentes(
    client: TestClient, coach_headers: dict, sesion: dict
):
    ejercicios = client.get("/api/coach/exercises", headers=coach_headers).json()
    payload = _payload(sesion["routine"])
    payload["items"].append({"exercise_id": ejercicios[5]["id"], "sets": 4, "target_reps": 12})

    respuesta = client.put(
        f"/api/coach/routines/{sesion['routine']['id']}", headers=coach_headers, json=payload
    ).json()

    assert len(respuesta["items"]) == 3
    assert len(_cargas(client, sesion)) == 3


def test_reordenar_ejercicios_conserva_las_cargas(
    client: TestClient, coach_headers: dict, sesion: dict
):
    payload = _payload(sesion["routine"])
    payload["items"].reverse()

    respuesta = client.put(
        f"/api/coach/routines/{sesion['routine']['id']}", headers=coach_headers, json=payload
    ).json()

    # El ejercicio con cargas pasa a la segunda posición pero mantiene su id y sus logs.
    con_cargas = next(i for i in respuesta["items"] if i["id"] == sesion["routine"]["items"][0]["id"])
    assert con_cargas["position"] == 1
    assert len(_cargas(client, sesion)) == 3


def test_quitar_un_ejercicio_borra_sus_cargas(client: TestClient, coach_headers: dict, sesion: dict):
    payload = _payload(sesion["routine"])
    payload["items"] = payload["items"][1:]  # fuera el que tiene cargas

    respuesta = client.put(
        f"/api/coach/routines/{sesion['routine']['id']}", headers=coach_headers, json=payload
    ).json()

    assert len(respuesta["items"]) == 1
    assert _cargas(client, sesion) == []


def test_un_cliente_que_no_manda_ids_tampoco_pierde_cargas(
    client: TestClient, coach_headers: dict, sesion: dict
):
    """El emparejamiento cae de vuelta al ejercicio: no depende del cliente."""
    payload = _payload(sesion["routine"], name="Sin ids")
    for item in payload["items"]:
        item.pop("id")

    client.put(f"/api/coach/routines/{sesion['routine']['id']}", headers=coach_headers, json=payload)

    assert [log["set_number"] for log in _cargas(client, sesion)] == [1, 2, 3]
