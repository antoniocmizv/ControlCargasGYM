"""Lógica compartida para resolver que rutinas ve cada jugador."""

from datetime import date

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ROLE_PLAYER,
    TARGET_ALL,
    TARGET_GROUP,
    TARGET_PLAYER,
    Routine,
    RoutineAssignment,
    User,
    player_groups,
)


def routines_for_player_stmt(user: User) -> Select:
    """Rutinas asignadas al equipo entero, a un grupo del jugador o al jugador."""
    group_ids = [group.id for group in user.groups]
    conditions = [
        RoutineAssignment.target_type == TARGET_ALL,
        and_(RoutineAssignment.target_type == TARGET_PLAYER, RoutineAssignment.user_id == user.id),
    ]
    if group_ids:
        conditions.append(
            and_(
                RoutineAssignment.target_type == TARGET_GROUP,
                RoutineAssignment.group_id.in_(group_ids),
            )
        )

    return (
        select(Routine)
        .join(RoutineAssignment, RoutineAssignment.routine_id == Routine.id)
        .where(or_(*conditions))
        .distinct()
    )


def get_player_routine_for_date(db: Session, user: User, day: date) -> Routine | None:
    stmt = (
        routines_for_player_stmt(user)
        .where(Routine.session_date == day)
        .order_by(Routine.created_at.desc())
        .options(selectinload(Routine.items))
    )
    return db.scalars(stmt).first()


def players_assigned_to(db: Session, routine: Routine) -> list[User]:
    """Jugadores activos alcanzados por las asignaciones de una rutina."""
    target_types = {assignment.target_type for assignment in routine.assignments}
    base = select(User).where(User.role == ROLE_PLAYER, User.is_active.is_(True))

    if TARGET_ALL in target_types:
        return list(db.scalars(base.order_by(User.name)).all())

    group_ids = [a.group_id for a in routine.assignments if a.target_type == TARGET_GROUP and a.group_id]
    user_ids = [a.user_id for a in routine.assignments if a.target_type == TARGET_PLAYER and a.user_id]
    if not group_ids and not user_ids:
        return []

    conditions = []
    if user_ids:
        conditions.append(User.id.in_(user_ids))
    if group_ids:
        conditions.append(
            User.id.in_(select(player_groups.c.user_id).where(player_groups.c.group_id.in_(group_ids)))
        )

    return list(db.scalars(base.where(or_(*conditions)).order_by(User.name)).all())
