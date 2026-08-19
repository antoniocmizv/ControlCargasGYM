from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_coach
from app.core.database import get_db
from app.core.security import hash_secret
from app.models import (
    ROLE_PLAYER,
    TARGET_GROUP,
    TARGET_PLAYER,
    Exercise,
    Group,
    Routine,
    RoutineAssignment,
    RoutineExercise,
    SetLog,
    User,
)
from app.schemas import (
    AssignmentIn,
    ExerciseIn,
    ExerciseOut,
    ExerciseUpdate,
    GroupIn,
    GroupOut,
    PlayerCreate,
    PlayerProgressRow,
    PlayerUpdate,
    RoutineIn,
    RoutineOut,
    RoutineProgress,
    RoutineSummary,
    UserOut,
)
from app.services.routines import players_assigned_to

router = APIRouter(prefix="/coach", tags=["coach"], dependencies=[Depends(get_current_coach)])


def _load_groups(db: Session, group_ids: list[int]) -> list[Group]:
    if not group_ids:
        return []
    groups = db.scalars(select(Group).where(Group.id.in_(group_ids))).all()
    if len(groups) != len(set(group_ids)):
        raise HTTPException(status_code=400, detail="Algún grupo indicado no existe")
    return list(groups)


# ---------------- Jugadores ----------------
@router.get("/players", response_model=list[UserOut])
def list_players(include_inactive: bool = False, db: Session = Depends(get_db)):
    stmt = select(User).where(User.role == ROLE_PLAYER).options(selectinload(User.groups))
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    return db.scalars(stmt.order_by(User.name)).all()


@router.post("/players", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerCreate, db: Session = Depends(get_db)):
    player = User(
        name=payload.name.strip(),
        role=ROLE_PLAYER,
        pin_hash=hash_secret(payload.pin),
        groups=_load_groups(db, payload.group_ids),
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.patch("/players/{player_id}", response_model=UserOut)
def update_player(player_id: int, payload: PlayerUpdate, db: Session = Depends(get_db)):
    player = db.get(User, player_id)
    if player is None or player.role != ROLE_PLAYER:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")

    if payload.name is not None:
        player.name = payload.name.strip()
    if payload.pin is not None:
        player.pin_hash = hash_secret(payload.pin)
    if payload.is_active is not None:
        player.is_active = payload.is_active
    if payload.group_ids is not None:
        player.groups = _load_groups(db, payload.group_ids)

    db.commit()
    db.refresh(player)
    return player


@router.delete("/players/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player(player_id: int, db: Session = Depends(get_db)):
    player = db.get(User, player_id)
    if player is None or player.role != ROLE_PLAYER:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    db.delete(player)
    db.commit()


# ---------------- Grupos ----------------
@router.get("/groups", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db)):
    return db.scalars(select(Group).order_by(Group.name)).all()


@router.post("/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupIn, db: Session = Depends(get_db)):
    group = Group(name=payload.name.strip())
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un grupo con ese nombre") from None
    db.refresh(group)
    return group


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    db.delete(group)
    db.commit()


# ---------------- Ejercicios ----------------
@router.get("/exercises", response_model=list[ExerciseOut])
def list_exercises(include_inactive: bool = False, db: Session = Depends(get_db)):
    stmt = select(Exercise)
    if not include_inactive:
        stmt = stmt.where(Exercise.is_active.is_(True))
    return db.scalars(stmt.order_by(Exercise.category, Exercise.name)).all()


@router.post("/exercises", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(payload: ExerciseIn, db: Session = Depends(get_db)):
    exercise = Exercise(
        name=payload.name.strip(),
        description=payload.description,
        category=payload.category,
    )
    db.add(exercise)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un ejercicio con ese nombre") from None
    db.refresh(exercise)
    return exercise


@router.patch("/exercises/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: int, payload: ExerciseUpdate, db: Session = Depends(get_db)):
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exercise, field, value.strip() if field == "name" and value else value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un ejercicio con ese nombre") from None
    db.refresh(exercise)
    return exercise


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """Archiva el ejercicio si ya se ha usado; lo borra si no."""
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")

    in_use = db.scalar(
        select(func.count()).select_from(RoutineExercise).where(RoutineExercise.exercise_id == exercise_id)
    )
    if in_use:
        exercise.is_active = False
    else:
        db.delete(exercise)
    db.commit()


# ---------------- Baterías ----------------
def _apply_routine_payload(db: Session, routine: Routine, payload: RoutineIn) -> None:
    routine.name = payload.name.strip()
    routine.session_date = payload.session_date
    routine.notes = payload.notes

    if not payload.items:
        raise HTTPException(status_code=400, detail="La batería necesita al menos un ejercicio")
    if not payload.assignments:
        raise HTTPException(status_code=400, detail="Indica a quién va dirigida la batería")

    exercise_ids = {item.exercise_id for item in payload.items}
    found = db.scalars(select(Exercise.id).where(Exercise.id.in_(exercise_ids))).all()
    if len(found) != len(exercise_ids):
        raise HTTPException(status_code=400, detail="Algún ejercicio indicado no existe")

    _reconcile_items(db, routine, payload)
    routine.assignments = [_build_assignment(db, a) for a in payload.assignments]


def _reconcile_items(db: Session, routine: Routine, payload: RoutineIn) -> None:
    """
    Actualiza los ejercicios en su sitio en lugar de recrearlos.

    Recrearlos borraria por cascada las cargas que los jugadores ya hubieran
    registrado, asi que hasta renombrar la sesion vaciaba la sesion entera.
    Cada linea entrante se empareja con la que ya existia por id y, si el
    cliente no lo manda, por ejercicio: perder cargas nunca puede depender de
    que quien llama se acuerde de devolver un identificador.
    """
    disponibles = list(routine.items)
    emparejado: dict[int, RoutineExercise] = {}

    for index, incoming in enumerate(payload.items):
        if incoming.id is None:
            continue
        item = next((e for e in disponibles if e.id == incoming.id), None)
        if item is not None:
            disponibles.remove(item)
            emparejado[index] = item

    for index, incoming in enumerate(payload.items):
        if index in emparejado:
            continue
        item = next((e for e in disponibles if e.exercise_id == incoming.exercise_id), None)
        if item is not None:
            disponibles.remove(item)
            emparejado[index] = item

    conservados: list[RoutineExercise] = []
    for position, incoming in enumerate(payload.items):
        item = emparejado.get(position)
        if item is None:
            item = RoutineExercise(exercise_id=incoming.exercise_id)
        elif item.exercise_id != incoming.exercise_id:
            # Cambiar de ejercicio invalida lo registrado en esa linea.
            _drop_logs(db, item.id)
            item.exercise_id = incoming.exercise_id

        item.position = position
        item.sets = incoming.sets
        item.target_reps = incoming.target_reps
        item.rest_seconds = incoming.rest_seconds
        item.notes = incoming.notes

        # Si se recortan las series, las cargas sobrantes ya no tienen sitio.
        if item.id is not None:
            _drop_logs(db, item.id, above_set=incoming.sets)

        conservados.append(item)

    routine.items = conservados


def _drop_logs(db: Session, routine_exercise_id: int, above_set: int | None = None) -> None:
    stmt = delete(SetLog).where(SetLog.routine_exercise_id == routine_exercise_id)
    if above_set is not None:
        stmt = stmt.where(SetLog.set_number > above_set)
    db.execute(stmt)


def _build_assignment(db: Session, payload: AssignmentIn) -> RoutineAssignment:
    if payload.target_type == TARGET_GROUP:
        if payload.group_id is None or db.get(Group, payload.group_id) is None:
            raise HTTPException(status_code=400, detail="Grupo no válido en la asignación")
        return RoutineAssignment(target_type=TARGET_GROUP, group_id=payload.group_id)

    if payload.target_type == TARGET_PLAYER:
        player = db.get(User, payload.user_id) if payload.user_id else None
        if player is None or player.role != ROLE_PLAYER:
            raise HTTPException(status_code=400, detail="Jugador no válido en la asignación")
        return RoutineAssignment(target_type=TARGET_PLAYER, user_id=payload.user_id)

    return RoutineAssignment(target_type=payload.target_type)


def _routine_summary(db: Session, routine: Routine) -> RoutineSummary:
    return RoutineSummary(
        id=routine.id,
        name=routine.name,
        session_date=routine.session_date,
        exercise_count=len(routine.items),
        assigned_players=len(players_assigned_to(db, routine)),
    )


@router.get("/routines", response_model=list[RoutineSummary])
def list_routines(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Routine).options(selectinload(Routine.items), selectinload(Routine.assignments))
    if date_from:
        stmt = stmt.where(Routine.session_date >= date_from)
    if date_to:
        stmt = stmt.where(Routine.session_date <= date_to)
    routines = db.scalars(stmt.order_by(Routine.session_date.desc(), Routine.id.desc())).all()
    return [_routine_summary(db, routine) for routine in routines]


@router.post("/routines", response_model=RoutineOut, status_code=status.HTTP_201_CREATED)
def create_routine(
    payload: RoutineIn, db: Session = Depends(get_db), coach: User = Depends(get_current_coach)
):
    routine = Routine(coach_id=coach.id, name=payload.name, session_date=payload.session_date)
    _apply_routine_payload(db, routine, payload)
    db.add(routine)
    db.commit()
    db.refresh(routine)
    return routine


@router.get("/routines/{routine_id}", response_model=RoutineOut)
def get_routine(routine_id: int, db: Session = Depends(get_db)):
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise HTTPException(status_code=404, detail="Batería no encontrada")
    return routine


@router.put("/routines/{routine_id}", response_model=RoutineOut)
def update_routine(routine_id: int, payload: RoutineIn, db: Session = Depends(get_db)):
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise HTTPException(status_code=404, detail="Batería no encontrada")
    _apply_routine_payload(db, routine, payload)
    db.commit()
    db.refresh(routine)
    return routine


@router.post("/routines/{routine_id}/duplicate", response_model=RoutineOut, status_code=201)
def duplicate_routine(
    routine_id: int,
    session_date: date,
    db: Session = Depends(get_db),
    coach: User = Depends(get_current_coach),
):
    """Copia una batería a otra fecha: el caso más habitual del día a día."""
    original = db.get(Routine, routine_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Batería no encontrada")

    copy = Routine(
        name=original.name,
        session_date=session_date,
        notes=original.notes,
        coach_id=coach.id,
        items=[
            RoutineExercise(
                exercise_id=item.exercise_id,
                position=item.position,
                sets=item.sets,
                target_reps=item.target_reps,
                rest_seconds=item.rest_seconds,
                notes=item.notes,
            )
            for item in original.items
        ],
        assignments=[
            RoutineAssignment(
                target_type=assignment.target_type,
                group_id=assignment.group_id,
                user_id=assignment.user_id,
            )
            for assignment in original.assignments
        ],
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


@router.delete("/routines/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_routine(routine_id: int, db: Session = Depends(get_db)):
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise HTTPException(status_code=404, detail="Batería no encontrada")
    db.delete(routine)
    db.commit()


@router.get("/routines/{routine_id}/progress", response_model=RoutineProgress)
def routine_progress(routine_id: int, db: Session = Depends(get_db)):
    """Cuántas series lleva registradas cada jugador de esta batería."""
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise HTTPException(status_code=404, detail="Batería no encontrada")

    item_ids = [item.id for item in routine.items]
    total_sets = sum(item.sets for item in routine.items)
    counts: dict[int, int] = {}
    if item_ids:
        rows = db.execute(
            select(SetLog.user_id, func.count(SetLog.id))
            .where(SetLog.routine_exercise_id.in_(item_ids))
            .group_by(SetLog.user_id)
        ).all()
        counts = {user_id: count for user_id, count in rows}

    return RoutineProgress(
        routine=_routine_summary(db, routine),
        rows=[
            PlayerProgressRow(
                player_id=player.id,
                player_name=player.name,
                logged_sets=counts.get(player.id, 0),
                total_sets=total_sets,
            )
            for player in players_assigned_to(db, routine)
        ],
    )
