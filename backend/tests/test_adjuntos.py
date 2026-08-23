"""PDF adjuntos: quién puede subirlos, quién verlos y qué se rechaza."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers

DIA = date.today() - timedelta(days=300)
PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"


@pytest.fixture
def bateria(client: TestClient, coach_headers: dict) -> dict:
    dentro = client.post(
        "/api/coach/players", json={"name": "Adj Dentro", "pin": "1212"}, headers=coach_headers
    ).json()
    fuera = client.post(
        "/api/coach/players", json={"name": "Adj Fuera", "pin": "3434"}, headers=coach_headers
    ).json()
    ejercicio = client.get("/api/coach/exercises", headers=coach_headers).json()[0]

    routine = client.post(
        "/api/coach/routines",
        headers=coach_headers,
        json={
            "name": "Con PDF",
            "session_date": str(DIA),
            "items": [{"exercise_id": ejercicio["id"], "sets": 2}],
            "assignments": [{"target_type": "player", "user_id": dentro["id"]}],
        },
    ).json()

    def entra(jugador, pin):
        return auth_headers(
            client.post(
                "/api/auth/login/player", json={"user_id": jugador["id"], "pin": pin}
            ).json()["access_token"]
        )

    return {"routine": routine, "dentro": entra(dentro, "1212"), "fuera": entra(fuera, "3434")}


def _sube(client, coach_headers, routine_id, contenido=PDF, nombre="rutina.pdf"):
    return client.post(
        f"/api/coach/routines/{routine_id}/adjuntos",
        headers=coach_headers,
        files={"file": (nombre, contenido, "application/pdf")},
    )


def test_el_entrenador_sube_un_pdf(client: TestClient, coach_headers: dict, bateria: dict):
    respuesta = _sube(client, coach_headers, bateria["routine"]["id"])

    assert respuesta.status_code == 201
    adjunto = respuesta.json()
    assert adjunto["filename"] == "rutina.pdf"
    assert adjunto["size_bytes"] == len(PDF)
    # La ficha no expone dónde está el fichero en disco.
    assert "stored_name" not in adjunto


def test_el_jugador_asignado_lo_ve_y_lo_descarga(
    client: TestClient, coach_headers: dict, bateria: dict
):
    adjunto = _sube(client, coach_headers, bateria["routine"]["id"]).json()
    routine_id = bateria["routine"]["id"]

    listado = client.get(f"/api/routines/{routine_id}/adjuntos", headers=bateria["dentro"]).json()
    assert [a["id"] for a in listado] == [adjunto["id"]]

    descarga = client.get(
        f"/api/routines/{routine_id}/adjuntos/{adjunto['id']}", headers=bateria["dentro"]
    )
    assert descarga.status_code == 200
    assert descarga.headers["content-type"] == "application/pdf"
    assert descarga.content.startswith(b"%PDF-")


def test_un_jugador_sin_la_bateria_asignada_no_lo_ve(
    client: TestClient, coach_headers: dict, bateria: dict
):
    adjunto = _sube(client, coach_headers, bateria["routine"]["id"]).json()
    routine_id = bateria["routine"]["id"]

    assert client.get(f"/api/routines/{routine_id}/adjuntos", headers=bateria["fuera"]).status_code == 403
    assert (
        client.get(
            f"/api/routines/{routine_id}/adjuntos/{adjunto['id']}", headers=bateria["fuera"]
        ).status_code
        == 403
    )


def test_un_jugador_no_puede_subir(client: TestClient, bateria: dict):
    respuesta = client.post(
        f"/api/coach/routines/{bateria['routine']['id']}/adjuntos",
        headers=bateria["dentro"],
        files={"file": ("x.pdf", PDF, "application/pdf")},
    )
    assert respuesta.status_code == 403


def test_se_rechaza_lo_que_no_es_un_pdf(client: TestClient, coach_headers: dict, bateria: dict):
    """El Content-Type lo pone quien envía: lo que manda es el contenido."""
    respuesta = _sube(
        client, coach_headers, bateria["routine"]["id"], contenido=b"MZ\x90\x00 ejecutable"
    )
    assert respuesta.status_code == 400
    assert "PDF" in respuesta.json()["detail"]


def test_se_rechaza_un_pdf_demasiado_grande(client: TestClient, coach_headers: dict, bateria: dict):
    enorme = b"%PDF-1.4\n" + b"0" * (11 * 1024 * 1024)
    respuesta = _sube(client, coach_headers, bateria["routine"]["id"], contenido=enorme)
    assert respuesta.status_code == 413


def test_un_fichero_vacio_se_rechaza(client: TestClient, coach_headers: dict, bateria: dict):
    assert _sube(client, coach_headers, bateria["routine"]["id"], contenido=b"").status_code == 400


def test_el_nombre_del_fichero_no_puede_escapar_del_directorio(
    client: TestClient, coach_headers: dict, bateria: dict
):
    adjunto = _sube(
        client, coach_headers, bateria["routine"]["id"], nombre="../../../etc/passwd.pdf"
    ).json()
    assert "/" not in adjunto["filename"]
    assert adjunto["filename"] == "passwd.pdf"


def test_borrar_el_adjunto_lo_quita_del_disco(
    client: TestClient, coach_headers: dict, bateria: dict
):
    from app.services import adjuntos as almacen
    from app.models import RoutineAttachment
    from app.core.database import SessionLocal

    adjunto = _sube(client, coach_headers, bateria["routine"]["id"]).json()
    with SessionLocal() as db:
        ruta = almacen.ruta_de(db.get(RoutineAttachment, adjunto["id"]).stored_name)
    assert ruta.is_file()

    assert client.delete(f"/api/coach/adjuntos/{adjunto['id']}", headers=coach_headers).status_code == 204
    assert not ruta.exists()


def test_borrar_la_bateria_se_lleva_sus_adjuntos(
    client: TestClient, coach_headers: dict, bateria: dict
):
    routine_id = bateria["routine"]["id"]
    adjunto = _sube(client, coach_headers, routine_id).json()

    client.delete(f"/api/coach/routines/{routine_id}", headers=coach_headers)

    assert (
        client.get(f"/api/routines/{routine_id}/adjuntos", headers=coach_headers).status_code == 404
    )
    assert (
        client.get(
            f"/api/routines/{routine_id}/adjuntos/{adjunto['id']}", headers=coach_headers
        ).status_code
        == 404
    )
