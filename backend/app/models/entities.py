from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

ROLE_ADMIN = "admin"   # entrenador principal: además gestiona a los demás
ROLE_COACH = "coach"
ROLE_PLAYER = "player"

# Los dos roles con acceso al panel. El esquema no cambia: `role` ya era texto,
# así que basta con admitir un valor más y evitamos un ALTER TABLE.
ROLES_STAFF = (ROLE_ADMIN, ROLE_COACH)

TARGET_ALL = "all"
TARGET_GROUP = "group"
TARGET_PLAYER = "player"


def _now() -> datetime:
    return datetime.now(timezone.utc)


player_groups = Table(
    "player_groups",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False, default=ROLE_PLAYER)
    username: Mapped[str | None] = mapped_column(String(80), unique=True)
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    groups: Mapped[list["Group"]] = relationship(secondary=player_groups, back_populates="players")
    logs: Mapped[list["SetLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    players: Mapped[list[User]] = relationship(secondary=player_groups, back_populates="groups")


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Routine(Base):
    """Batería de ejercicios para un día concreto."""

    __tablename__ = "routines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    coach_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    items: Mapped[list["RoutineExercise"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineExercise.position",
    )
    assignments: Mapped[list["RoutineAssignment"]] = relationship(
        back_populates="routine", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["RoutineAttachment"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineAttachment.created_at",
    )


class RoutineExercise(Base):
    __tablename__ = "routine_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    routine_id: Mapped[int] = mapped_column(ForeignKey("routines.id", ondelete="CASCADE"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    target_reps: Mapped[int | None] = mapped_column(Integer)
    rest_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    routine: Mapped[Routine] = relationship(back_populates="items")
    exercise: Mapped[Exercise] = relationship()
    logs: Mapped[list["SetLog"]] = relationship(back_populates="routine_exercise", cascade="all, delete-orphan")
    prescriptions: Mapped[list["ExercisePrescription"]] = relationship(
        back_populates="routine_exercise", cascade="all, delete-orphan"
    )


class RoutineAssignment(Base):
    """A quien va dirigida la batería: todo el equipo, un grupo o un jugador."""

    __tablename__ = "routine_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    routine_id: Mapped[int] = mapped_column(ForeignKey("routines.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(10), nullable=False)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    routine: Mapped[Routine] = relationship(back_populates="assignments")
    group: Mapped[Group | None] = relationship()
    user: Mapped[User | None] = relationship()


class RoutineAttachment(Base):
    """PDF adjunto a una batería. El fichero vive en disco; aquí solo su ficha."""

    __tablename__ = "routine_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    routine_id: Mapped[int] = mapped_column(
        ForeignKey("routines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # El que trae el fichero: solo se muestra y se usa al descargar, nunca en disco.
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # El que genera el servidor: es el que existe realmente en /data/adjuntos.
    stored_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    routine: Mapped["Routine"] = relationship(back_populates="attachments")


class ExercisePrescription(Base):
    """
    Lo que el entrenador le marca a un jugador concreto en un ejercicio.

    Es la indicación previa ("Ana, en sentadilla haz 80"), distinta del
    `set_logs`, que es lo que el jugador levantó de verdad.
    """

    __tablename__ = "exercise_prescriptions"
    __table_args__ = (
        UniqueConstraint("routine_exercise_id", "user_id", name="uq_anotacion_jugador"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    routine_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("routine_exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_load_kg: Mapped[float | None] = mapped_column(Numeric(6, 2))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)

    routine_exercise: Mapped["RoutineExercise"] = relationship(back_populates="prescriptions")
    user: Mapped["User"] = relationship()


class SetLog(Base):
    """Carga registrada por un jugador en una serie concreta."""

    __tablename__ = "set_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "routine_exercise_id", "set_number", name="uq_log_serie"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    routine_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("routine_exercises.id", ondelete="CASCADE"), nullable=False
    )
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    load_kg: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    reps: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="logs")
    routine_exercise: Mapped[RoutineExercise] = relationship(back_populates="logs")
