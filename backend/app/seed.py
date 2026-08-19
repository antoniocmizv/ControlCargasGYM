"""Datos iniciales: entrenador y catalogo basico de ejercicios."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_secret
from app.models import ROLE_COACH, Exercise, User

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
    ("Hip thrust", "Gluteo"),
    ("Plancha abdominal", "Core"),
]


def seed(db: Session) -> None:
    coach = db.scalars(select(User).where(User.role == ROLE_COACH)).first()
    if coach is None:
        db.add(
            User(
                name=settings.coach_name,
                role=ROLE_COACH,
                username=settings.coach_username,
                password_hash=hash_secret(settings.coach_password),
            )
        )

    if not db.scalar(select(Exercise.id).limit(1)):
        db.add_all(Exercise(name=name, category=category) for name, category in BASE_EXERCISES)

    db.commit()
