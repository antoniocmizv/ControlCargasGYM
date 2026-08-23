"""Rellenar sesiones pasadas, progresión del jugador y seguimiento en vivo."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers

HOY = date.today()


@pytest.fixture
def historial(client: TestClient, coach_headers: dict) -> dict:
    """Un jugador con cargas de tres semanas y una sesión de ayer sin rellenar."""
    player = client.post(
        "/api/coach/players", json={"name": "Progreso Test", "pin": "7777"}, headers=coach_headers
    ).json()
    headers = auth_headers(
        client.post("/api/auth/login/player", json={"user_id": player["id"], "pin": "7777"}).json()[
            "access_token"
        ]
    )
    ejercicios = client.get("/api/coach/exercises", headers=coach_headers).json()
    ejercicio = ejercicios[0]

    for semanas, kg in [(3, 60), (2, 65), (1, 70)]:
        routine = client.post(
            "/api/coach/routines",
            headers=coach_headers,
            json={
                "name": f"Semana -{semanas}",
                "session_date": str(HOY - timedelta(weeks=semanas)),
                "items": [{"exercise_id": ejercicio["id"], "sets": 2, "target_reps": 8}],
                "assignments": [{"target_type": "player", "user_id": player["id"]}],
            },
        ).json()
        for numero in (1, 2):
            client.post(
                "/api/logs",
                headers=headers,
                json={
                    "routine_exercise_id": routine["items"][0]["id"],
                    "set_number": numero,
                    "load_kg": kg,
                    "reps": 8,
                },
            )

    ayer = client.post(
        "/api/coach/routines",
        headers=coach_headers,
        json={
            "name": "Sesión de ayer",
            "session_date": str(HOY - timedelta(days=1)),
            "items": [{"exercise_id": ejercicio["id"], "sets": 3, "target_reps": 8}],
            "assignments": [{"target_type": "player", "user_id": player["id"]}],
        },
    ).json()

    return {"player": headers, "player_id": player["id"], "ayer": ayer, "exercise": ejercicio}


# ---------- rellenar una sesión pasada ----------
def test_se_puede_rellenar_una_sesion_de_ayer(client: TestClient, historial: dict):
    item = historial["ayer"]["items"][0]["id"]

    respuesta = client.post(
        "/api/logs",
        headers=historial["player"],
        json={"routine_exercise_id": item, "set_number": 1, "load_kg": 72.5, "reps": 8},
    )
    assert respuesta.status_code == 200

    ayer = str(HOY - timedelta(days=1))
    sesion = client.get("/api/routines/today", params={"day": ayer}, headers=historial["player"]).json()
    assert sesion[0]["items"][0]["logs"][0]["load_kg"] == 72.5


def test_el_historial_marca_las_sesiones_sin_rellenar(client: TestClient, historial: dict):
    sesiones = client.get("/api/routines/mine", headers=historial["player"]).json()

    ayer = next(s for s in sesiones if s["name"] == "Sesión de ayer")
    assert ayer["pending"] is True
    assert ayer["total_sets"] == 3
    assert ayer["logged_sets"] == 0

    completa = next(s for s in sesiones if s["name"] == "Semana -1")
    assert completa["pending"] is False
    assert completa["logged_sets"] == completa["total_sets"]


# ---------- progresión del jugador ----------
def test_progresion_lista_los_ejercicios_trabajados(client: TestClient, historial: dict):
    resumen = client.get("/api/progress/exercises", headers=historial["player"]).json()

    fila = next(r for r in resumen if r["exercise"]["id"] == historial["exercise"]["id"])
    assert fila["sessions"] == 3
    assert fila["first_load_kg"] == 60.0
    assert fila["latest_load_kg"] == 70.0
    assert fila["best_load_kg"] == 70.0


def test_progresion_de_un_ejercicio_va_en_orden_cronologico(client: TestClient, historial: dict):
    detalle = client.get(
        f"/api/progress/exercises/{historial['exercise']['id']}", headers=historial["player"]
    ).json()

    cargas = [punto["best_load_kg"] for punto in detalle["points"]]
    assert cargas == [60.0, 65.0, 70.0]
    assert detalle["points"][0]["sets"] == 2
    assert detalle["points"][0]["total_volume"] == 60.0 * 8 * 2


def test_la_progresion_es_de_cada_jugador(client: TestClient, coach_headers: dict, historial: dict):
    otro = client.post(
        "/api/coach/players", json={"name": "Otro Jugador", "pin": "8888"}, headers=coach_headers
    ).json()
    headers = auth_headers(
        client.post("/api/auth/login/player", json={"user_id": otro["id"], "pin": "8888"}).json()[
            "access_token"
        ]
    )

    assert client.get("/api/progress/exercises", headers=headers).json() == []


def test_el_entrenador_no_entra_en_la_progresion_del_jugador(client: TestClient, coach_headers: dict):
    assert client.get("/api/progress/exercises", headers=coach_headers).status_code == 403


# ---------- seguimiento en vivo del entrenador ----------
def test_seguimiento_en_vivo_muestra_los_kg_de_cada_jugador(
    client: TestClient, coach_headers: dict, historial: dict
):
    item = historial["ayer"]["items"][0]["id"]
    for numero, kg in [(1, 80), (2, 85)]:
        client.post(
            "/api/logs",
            headers=historial["player"],
            json={"routine_exercise_id": item, "set_number": numero, "load_kg": kg, "reps": 6},
        )

    vivo = client.get(
        f"/api/coach/routines/{historial['ayer']['id']}/live", headers=coach_headers
    ).json()

    jugador = next(p for p in vivo["players"] if p["player_id"] == historial["player_id"])
    assert jugador["logged_sets"] == 2
    assert jugador["total_sets"] == 3
    ejercicio = jugador["exercises"][0]
    assert [(log["set_number"], log["load_kg"], log["reps"]) for log in ejercicio["logs"]] == [
        (1, 80.0, 6),
        (2, 85.0, 6),
    ]
    assert ejercicio["best_load_kg"] == 85.0


def test_un_jugador_no_puede_ver_el_seguimiento(client: TestClient, historial: dict):
    respuesta = client.get(
        f"/api/coach/routines/{historial['ayer']['id']}/live", headers=historial["player"]
    )
    assert respuesta.status_code == 403


# ---------- regresiones del code review ----------
def test_dos_baterias_el_mismo_dia_cuentan_como_dos_sesiones(
    client: TestClient, coach_headers: dict
):
    """Agrupar por fecha en vez de por rutina falseaba total, primera y última carga."""
    player = client.post(
        "/api/coach/players", json={"name": "Doble Sesión", "pin": "9090"}, headers=coach_headers
    ).json()
    headers = auth_headers(
        client.post("/api/auth/login/player", json={"user_id": player["id"], "pin": "9090"}).json()[
            "access_token"
        ]
    )
    ejercicio = client.get("/api/coach/exercises", headers=coach_headers).json()[0]

    for nombre, kg in [("Mañana", 60), ("Tarde", 90)]:
        routine = client.post(
            "/api/coach/routines",
            headers=coach_headers,
            json={
                "name": nombre,
                "session_date": str(HOY),
                "items": [{"exercise_id": ejercicio["id"], "sets": 1, "target_reps": 8}],
                "assignments": [{"target_type": "player", "user_id": player["id"]}],
            },
        ).json()
        client.post(
            "/api/logs",
            headers=headers,
            json={
                "routine_exercise_id": routine["items"][0]["id"],
                "set_number": 1,
                "load_kg": kg,
                "reps": 8,
            },
        )

    resumen = next(
        r
        for r in client.get("/api/progress/exercises", headers=headers).json()
        if r["exercise"]["id"] == ejercicio["id"]
    )
    assert resumen["sessions"] == 2
    assert resumen["first_load_kg"] == 60.0
    assert resumen["latest_load_kg"] == 90.0

    detalle = client.get(f"/api/progress/exercises/{ejercicio['id']}", headers=headers).json()
    assert [p["best_load_kg"] for p in detalle["points"]] == [60.0, 90.0]


def test_el_seguimiento_no_hace_una_consulta_por_ejercicio(
    client: TestClient, coach_headers: dict
):
    """La pantalla se refresca cada 20 s: las relaciones van precargadas."""
    from sqlalchemy import event

    from app.core.database import engine

    ejercicios = client.get("/api/coach/exercises", headers=coach_headers).json()[:5]
    routine = client.post(
        "/api/coach/routines",
        headers=coach_headers,
        json={
            "name": "Batería larga",
            "session_date": str(HOY),
            "items": [{"exercise_id": e["id"], "sets": 2} for e in ejercicios],
            "assignments": [{"target_type": "all"}],
        },
    ).json()

    consultas: list[str] = []

    def registra(conn, cursor, statement, params, context, executemany):
        consultas.append(statement)

    event.listen(engine, "before_cursor_execute", registra)
    try:
        client.get(f"/api/coach/routines/{routine['id']}/live", headers=coach_headers)
    finally:
        event.remove(engine, "before_cursor_execute", registra)

    sobre_ejercicios = [s for s in consultas if "FROM exercises" in s]
    assert len(sobre_ejercicios) <= 1, f"{len(sobre_ejercicios)} consultas de ejercicios (N+1)"
