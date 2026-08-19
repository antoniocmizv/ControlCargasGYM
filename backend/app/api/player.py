from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import ROLE_PLAYER, Routine, RoutineExercise, SetLog, User
from app.schemas import (
    ExerciseOut,
    LastPerformance,
    PlayerRoutine,
    PlayerRoutineExercise,
    SetLogIn,
    SetLogOut,
)
from app.services.routines import get_player_routine_for_date, routines_for_player_stmt

router = APIRouter(tags=["jugador"])


def _require_player(user: User) -> User:
    if user.role != ROLE_PLAYER:
        raise HTTPException(status_code=403, detail="Esta sección es para jugadores")
    return user


def _last_performance(db: Session, user_id: int, exercise_id: int, before: date) -> LastPerformance | None:
    """Mejor carga del jugador en ese ejercicio en la sesión anterior más reciente."""
    row = db.execute(
        select(Routine.session_date, SetLog.load_kg, SetLog.reps)
        .join(RoutineExercise, RoutineExercise.id == SetLog.routine_exercise_id)
        .join(Routine, Routine.id == RoutineExercise.routine_id)
        .where(
            SetLog.user_id == user_id,
            RoutineExercise.exercise_id == exercise_id,
            Routine.session_date < before,
        )
        .order_by(Routine.session_date.desc(), SetLog.load_kg.desc())
        .limit(1)
    ).first()

    if row is None:
        return None
    return LastPerformance(session_date=row[0], best_load_kg=float(row[1]), reps=row[2])


@router.get("/routines/today", response_model=PlayerRoutine | None)
def routine_today(
    day: date | None = Query(default=None, description="Por defecto, hoy"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_player(user)
    target_day = day or date.today()
    routine = get_player_routine_for_date(db, user, target_day)
    if routine is None:
        return None

    item_ids = [item.id for item in routine.items]
    logs_by_item: dict[int, list[SetLog]] = {}
    if item_ids:
        logs = db.scalars(
            select(SetLog)
            .where(SetLog.user_id == user.id, SetLog.routine_exercise_id.in_(item_ids))
            .order_by(SetLog.set_number)
        ).all()
        for log in logs:
            logs_by_item.setdefault(log.routine_exercise_id, []).append(log)

    return PlayerRoutine(
        id=routine.id,
        name=routine.name,
        session_date=routine.session_date,
        notes=routine.notes,
        items=[
            PlayerRoutineExercise(
                id=item.id,
                position=item.position,
                sets=item.sets,
                target_reps=item.target_reps,
                rest_seconds=item.rest_seconds,
                notes=item.notes,
                exercise=ExerciseOut.model_validate(item.exercise),
                logs=[SetLogOut.model_validate(log) for log in logs_by_item.get(item.id, [])],
                last_performance=_last_performance(db, user.id, item.exercise_id, routine.session_date),
            )
            for item in routine.items
        ],
    )


@router.get("/routines/mine", response_model=list[dict])
def my_routines(
    limit: int = Query(default=14, ge=1, le=60),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Últimas sesiones asignadas al jugador, para poder rellenar una anterior."""
    _require_player(user)
    stmt = (
        routines_for_player_stmt(user)
        .order_by(Routine.session_date.desc())
        .limit(limit)
        .options(selectinload(Routine.items))
    )
    return [
        {
            "id": routine.id,
            "name": routine.name,
            "session_date": routine.session_date.isoformat(),
            "exercise_count": len(routine.items),
        }
        for routine in db.scalars(stmt).all()
    ]


@router.post("/logs", response_model=SetLogOut)
def save_log(payload: SetLogIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Guarda (o actualiza) la carga de una serie. Idempotente por jugador+serie."""
    _require_player(user)

    item = db.get(RoutineExercise, payload.routine_exercise_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Ejercicio de la batería no encontrado")
    if payload.set_number > item.sets:
        raise HTTPException(status_code=400, detail="Número de serie fuera de rango")

    routine = get_player_routine_for_date(db, user, item.routine.session_date)
    if routine is None or routine.id != item.routine_id:
        raise HTTPException(status_code=403, detail="Esta batería no está asignada a ti")

    log = db.scalars(
        select(SetLog).where(
            SetLog.user_id == user.id,
            SetLog.routine_exercise_id == payload.routine_exercise_id,
            SetLog.set_number == payload.set_number,
        )
    ).first()

    if log is None:
        log = SetLog(user_id=user.id, **payload.model_dump())
        db.add(log)
    else:
        log.load_kg = payload.load_kg
        log.reps = payload.reps

    db.commit()
    db.refresh(log)
    return log


@router.delete("/logs/{log_id}", status_code=204)
def delete_log(log_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_player(user)
    log = db.get(SetLog, log_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    db.delete(log)
    db.commit()
