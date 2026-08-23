"""Datos iniciales: entrenador y catalogo basico de ejercicios."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_secret
from app.models import ROLE_ADMIN, ROLE_COACH, Exercise, User

BASE_EXERCISES = [
    ("Sentadilla trasera", "Pierna"),
    ("Peso muerto", "Pierna"),
    ("Prensa de piernas", "Pierna"),
    ("Zancadas con mancuernas", "Pierna"),
    ("Curl femoral", "Pierna"),
    ("Press banca", "Pecho"),
    ("Press inclinado con mancuernas", "Pecho"),
    ("Dominadas", "Espalda"),
    ("Remo con barra", "Espalda"),
    ("Press militar", "Hombro"),
    ("Hip thrust", "Glúteo"),
    ("Plancha abdominal", "Core"),
]


def seed(db: Session) -> None:
    _asegura_entrenador_principal(db)

    if not db.scalar(select(Exercise.id).limit(1)):
        db.add_all(Exercise(name=name, category=category) for name, category in BASE_EXERCISES)

    db.commit()


def _asegura_entrenador_principal(db: Session) -> None:
    """
    Siempre tiene que haber un entrenador principal.

    En una instalación nueva se crea a partir del .env. En una que ya venía
    funcionando, el entrenador existente pasa de `coach` a `admin`: es un
    cambio de dato, idempotente, sin tocar el esquema.
    """
    if db.scalars(select(User).where(User.role == ROLE_ADMIN)).first() is not None:
        return

    veterano = db.scalars(
        select(User).where(User.role == ROLE_COACH).order_by(User.id)
    ).first()

    if veterano is not None:
        veterano.role = ROLE_ADMIN
        return

    db.add(
        User(
            name=settings.coach_name,
            role=ROLE_ADMIN,
            username=settings.coach_username,
            password_hash=hash_secret(settings.coach_password),
        )
    )
