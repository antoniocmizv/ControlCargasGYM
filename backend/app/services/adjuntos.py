"""
Guardado de los PDF adjuntos a una batería.

Aceptar ficheros de fuera es la parte con más aristas de la app, así que aquí
se concentran las tres defensas: el tamaño se comprueba mientras se lee (no
después, para que un envío enorme no llene el disco antes de rechazarlo), el
contenido tiene que ser realmente un PDF (la cabecera Content-Type la pone
quien envía y se puede falsear), y el nombre en disco lo genera el servidor,
de modo que no hay forma de escaparse del directorio con un `../`.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

MAX_BYTES = 10 * 1024 * 1024
TROZO = 64 * 1024
FIRMA_PDF = b"%PDF-"
MIME_PDF = "application/pdf"


def directorio() -> Path:
    ruta = Path(settings.attachments_dir)
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def ruta_de(stored_name: str) -> Path:
    # stored_name lo genera esta misma clase; se valida igualmente por si acaso.
    if "/" in stored_name or "\\" in stored_name or stored_name.startswith("."):
        raise HTTPException(status_code=400, detail="Nombre de fichero no válido")
    return directorio() / stored_name


async def guardar_pdf(upload: UploadFile) -> tuple[str, int]:
    """Vuelca el PDF a disco y devuelve (nombre_en_disco, tamaño)."""
    stored_name = f"{uuid.uuid4().hex}.pdf"
    destino = directorio() / stored_name

    total = 0
    primero = True
    try:
        with destino.open("wb") as fichero:
            while trozo := await upload.read(TROZO):
                if primero:
                    if not trozo.startswith(FIRMA_PDF):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="El fichero no es un PDF",
                        )
                    primero = False

                total += len(trozo)
                if total > MAX_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"El PDF supera el máximo de {MAX_BYTES // (1024 * 1024)} MB",
                    )
                fichero.write(trozo)

        if total == 0:
            raise HTTPException(status_code=400, detail="El fichero está vacío")
    except Exception:
        destino.unlink(missing_ok=True)
        raise

    return stored_name, total


def borrar(stored_name: str) -> None:
    ruta_de(stored_name).unlink(missing_ok=True)


def nombre_seguro(filename: str | None) -> str:
    """El nombre que verá el usuario al descargar; nunca toca el disco."""
    limpio = Path(filename or "").name.strip() or "rutina.pdf"
    if not limpio.lower().endswith(".pdf"):
        limpio = f"{limpio}.pdf"
    return limpio[:255]
