"""
Puesta al día del esquema al arrancar.

El servidor lleva una base creada con `create_all` antes de que existiera
Alembic, y esa base no tiene tabla `alembic_version`. Si Alembic la viera
"sin migrar" intentaría crear tablas que ya existen y el arranque fallaría.
Por eso, cuando encuentra datos pero no historial, la sella en la revisión
base y sigue desde ahí. Es idempotente: arrancar dos veces no repite nada.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import engine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REVISION_BASE = "7e029f307b2d"


def _config(connection) -> Config:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    config.attributes["connection"] = connection
    return config


def run_migrations() -> None:
    with engine.connect() as connection:
        tablas = set(inspect(connection).get_table_names())
        config = _config(connection)

        base_previa_sin_alembic = "alembic_version" not in tablas and "users" in tablas
        if base_previa_sin_alembic:
            command.stamp(config, REVISION_BASE)

        command.upgrade(config, "head")

        # Alembic no confirma cuando la conexion la pone quien llama: sin este
        # commit la tabla de versiones queda vacia y el siguiente arranque
        # intentaria crear de nuevo tablas que ya existen.
        connection.commit()
