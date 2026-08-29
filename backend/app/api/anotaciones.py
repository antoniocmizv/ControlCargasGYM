"""Lo que el entrenador le marca a cada jugador para una batería."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_coach
from app.core.database import get_db
from app.models import ROLE_PLAYER, ExercisePrescription, Routine, RoutineExercise, User
from app.schemas import PrescriptionIn, PrescriptionOut

router = APIRouter(prefix="/coach", tags=["anotaciones"], dependencies=[Depends(get_current_coach)])


def _routine(db: Session, routine_id: int) -> Routine:
    routine = db.scalars(
        select(Routine).where(Routine.id == routine_id).options(selectinload(Routine.items))
    ).first()
    if routine is None:
        raise HTTPException(status_code=404, detail="Batería no encontrada")
    return routine


@router.get("/routines/{routine_id}/anotaciones", response_model=list[PrescriptionOut])
def list_prescriptions(routine_id: int, db: Session = Depends(get_db)):
    routine = _routine(db, routine_id)
    item_ids = [item.id for item in routine.items]
    if not item_ids:
        return []

    stmt = select(ExercisePrescription).where(
        ExercisePrescription.routine_exercise_id.in_(item_ids)
    )
    return db.scalars(stmt).all()


@router.put("/routines/{routine_id}/anotaciones", response_model=list[PrescriptionOut])
def save_prescriptions(
    routine_id: int, payload: list[PrescriptionIn], db: Session = Depends(get_db)
):
    """
    Guarda las anotaciones de una batería de una vez.

    Una anotación vacía (sin kg ni nota) se borra en lugar de guardarse: es la
    forma de quitarla desde la interfaz sin un botón aparte.
    """
    routine = _routine(db, routine_id)
    item_ids = {item.id for item in routine.items}

    for entrada in payload:
        if entrada.routine_exercise_id not in item_ids:
            raise HTTPException(
                status_code=400, detail="Ese ejercicio no pertenece a la batería"
            )

    jugadores = set(
        db.scalars(
            select(User.id).where(
                User.id.in_({e.user_id for e in payload}), User.role == ROLE_PLAYER
            )
        ).all()
    )
    for entrada in payload:
        if entrada.user_id not in jugadores:
            raise HTTPException(status_code=400, detail="Jugador no válido en una anotación")

    existentes = {
        (p.routine_exercise_id, p.user_id): p
        for p in db.scalars(
            select(ExercisePrescription).where(
                ExercisePrescription.routine_exercise_id.in_(item_ids)
            )
        ).all()
    }

    for entrada in payload:
        clave = (entrada.routine_exercise_id, entrada.user_id)
        nota = (entrada.note or "").strip() or None
        vacia = entrada.target_load_kg is None and nota is None

        if clave in existentes:
            if vacia:
                db.delete(existentes.pop(clave))
            else:
                existentes[clave].target_load_kg = entrada.target_load_kg
                existentes[clave].note = nota
        elif not vacia:
            db.add(
                ExercisePrescription(
                    routine_exercise_id=entrada.routine_exercise_id,
                    user_id=entrada.user_id,
                    target_load_kg=entrada.target_load_kg,
                    note=nota,
                )
            )

    db.commit()
    return list_prescriptions(routine_id, db)


@router.delete(
    "/routines/{routine_id}/anotaciones/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
def clear_player_prescriptions(routine_id: int, user_id: int, db: Session = Depends(get_db)):
    """Quita de golpe todas las anotaciones de un jugador en esa batería."""
    routine = _routine(db, routine_id)
    item_ids = [item.id for item in routine.items]
    if not item_ids:
        return

    for prescripcion in db.scalars(
        select(ExercisePrescription).where(
            ExercisePrescription.routine_exercise_id.in_(item_ids),
            ExercisePrescription.user_id == user_id,
        )
    ).all():
        db.delete(prescripcion)
    db.commit()
