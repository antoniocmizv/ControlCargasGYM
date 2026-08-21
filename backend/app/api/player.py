from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import ROLE_PLAYER, Exercise, Routine, RoutineExercise, SetLog, User
from app.schemas import (
    ExerciseOut,
    ExerciseProgress,
    ExerciseProgressPoint,
    ExerciseProgressSummary,
    LastPerformance,
    MyRoutineRow,
    PlayerRoutine,
    PlayerRoutineExercise,
    SetLogIn,
    SetLogOut,
)
from app.services.routines import (
    get_player_routines_for_date,
    player_can_access_routine,
    routines_for_player_stmt,
)

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


@router.get("/routines/today", response_model=list[PlayerRoutine])
def routines_today(
    day: date | None = Query(default=None, description="Por defecto, hoy"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_player(user)
    routines = get_player_routines_for_date(db, user, day or date.today())
    if not routines:
        return []

    item_ids = [item.id for routine in routines for item in routine.items]
    logs_by_item: dict[int, list[SetLog]] = {}
    if item_ids:
        logs = db.scalars(
            select(SetLog)
            .where(SetLog.user_id == user.id, SetLog.routine_exercise_id.in_(item_ids))
            .order_by(SetLog.set_number)
        ).all()
        for log in logs:
            logs_by_item.setdefault(log.routine_exercise_id, []).append(log)

    return [
        PlayerRoutine(
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
                    last_performance=_last_performance(
                        db, user.id, item.exercise_id, routine.session_date
                    ),
                )
                for item in routine.items
            ],
        )
        for routine in routines
    ]


@router.get("/routines/mine", response_model=list[MyRoutineRow])
def my_routines(
    limit: int = Query(default=30, ge=1, le=120),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sesiones asignadas al jugador, marcando las que le quedan por rellenar."""
    _require_player(user)
    stmt = (
        routines_for_player_stmt(user)
        .order_by(Routine.session_date.desc())
        .limit(limit)
        .options(selectinload(Routine.items))
    )
    routines = list(db.scalars(stmt).all())

    item_ids = [item.id for routine in routines for item in routine.items]
    registradas: dict[int, int] = {}
    if item_ids:
        filas = db.execute(
            select(RoutineExercise.routine_id, func.count(SetLog.id))
            .join(SetLog, SetLog.routine_exercise_id == RoutineExercise.id)
            .where(SetLog.user_id == user.id, RoutineExercise.id.in_(item_ids))
            .group_by(RoutineExercise.routine_id)
        ).all()
        registradas = {routine_id: total for routine_id, total in filas}

    return [
        MyRoutineRow(
            id=routine.id,
            name=routine.name,
            session_date=routine.session_date,
            exercise_count=len(routine.items),
            total_sets=sum(item.sets for item in routine.items),
            logged_sets=registradas.get(routine.id, 0),
            pending=registradas.get(routine.id, 0) < sum(item.sets for item in routine.items),
        )
        for routine in routines
    ]


@router.get("/progress/exercises", response_model=list[ExerciseProgressSummary])
def my_exercises(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Ejercicios en los que el jugador ya ha registrado algo, con su evolución."""
    _require_player(user)

    filas = db.execute(
        select(
            Exercise,
            Routine.session_date,
            func.max(SetLog.load_kg),
        )
        .join(RoutineExercise, RoutineExercise.exercise_id == Exercise.id)
        .join(SetLog, SetLog.routine_exercise_id == RoutineExercise.id)
        .join(Routine, Routine.id == RoutineExercise.routine_id)
        .where(SetLog.user_id == user.id)
        .group_by(Exercise.id, Routine.session_date)
        .order_by(Exercise.name, Routine.session_date)
    ).all()

    por_ejercicio: dict[int, dict] = {}
    for exercise, session_date, mejor in filas:
        entrada = por_ejercicio.setdefault(
            exercise.id, {"exercise": exercise, "cargas": [], "fechas": []}
        )
        entrada["cargas"].append(float(mejor))
        entrada["fechas"].append(session_date)

    return [
        ExerciseProgressSummary(
            exercise=ExerciseOut.model_validate(entrada["exercise"]),
            sessions=len(entrada["cargas"]),
            best_load_kg=max(entrada["cargas"]),
            latest_load_kg=entrada["cargas"][-1],
            first_load_kg=entrada["cargas"][0],
        )
        for entrada in por_ejercicio.values()
    ]


@router.get("/progress/exercises/{exercise_id}", response_model=ExerciseProgress)
def my_exercise_progress(
    exercise_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Evolución sesión a sesión del jugador en un ejercicio."""
    _require_player(user)

    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")

    filas = db.execute(
        select(
            Routine.session_date,
            Routine.name,
            func.max(SetLog.load_kg),
            func.sum(SetLog.load_kg * func.coalesce(SetLog.reps, 0)),
            func.count(SetLog.id),
        )
        .join(RoutineExercise, RoutineExercise.routine_id == Routine.id)
        .join(SetLog, SetLog.routine_exercise_id == RoutineExercise.id)
        .where(SetLog.user_id == user.id, RoutineExercise.exercise_id == exercise_id)
        .group_by(Routine.session_date, Routine.name)
        .order_by(Routine.session_date)
    ).all()

    return ExerciseProgress(
        exercise=ExerciseOut.model_validate(exercise),
        points=[
            ExerciseProgressPoint(
                session_date=fecha,
                routine_name=nombre,
                best_load_kg=float(mejor),
                total_volume=float(volumen or 0),
                sets=series,
            )
            for fecha, nombre, mejor, volumen, series in filas
        ],
    )


@router.post("/logs", response_model=SetLogOut)
def save_log(payload: SetLogIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Guarda (o actualiza) la carga de una serie. Idempotente por jugador+serie."""
    _require_player(user)

    item = db.get(RoutineExercise, payload.routine_exercise_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Ejercicio de la batería no encontrado")
    if payload.set_number > item.sets:
        raise HTTPException(status_code=400, detail="Número de serie fuera de rango")

    if not player_can_access_routine(db, user, item.routine_id):
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
