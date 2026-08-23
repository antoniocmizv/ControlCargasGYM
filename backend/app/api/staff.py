"""Gestión de entrenadores y cambio de la propia contraseña."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_coach
from app.core.database import get_db
from app.core.security import hash_secret, verify_secret
from app.models import ROLE_ADMIN, ROLE_COACH, ROLES_STAFF, User
from app.schemas import PasswordChange, StaffCreate, StaffOut, StaffUpdate

router = APIRouter(prefix="/coach", tags=["entrenadores"])


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_own_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    coach: User = Depends(get_current_coach),
):
    """Cualquier entrenador cambia su propia contraseña, nunca la de otro."""
    if not verify_secret(payload.current_password, coach.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser distinta")

    coach.password_hash = hash_secret(payload.new_password)
    db.commit()


@router.get("/staff", response_model=list[StaffOut], dependencies=[Depends(get_current_admin)])
def list_staff(db: Session = Depends(get_db)):
    stmt = select(User).where(User.role.in_(ROLES_STAFF)).order_by(User.id)
    return db.scalars(stmt).all()


@router.post(
    "/staff",
    response_model=StaffOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_admin)],
)
def create_staff(payload: StaffCreate, db: Session = Depends(get_db)):
    entrenador = User(
        name=payload.name.strip(),
        role=ROLE_COACH,
        username=payload.username.strip().lower(),
        password_hash=hash_secret(payload.password),
    )
    db.add(entrenador)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ese usuario ya existe") from None
    db.refresh(entrenador)
    return entrenador


def _otro_entrenador(db: Session, staff_id: int, admin: User) -> User:
    entrenador = db.get(User, staff_id)
    if entrenador is None or entrenador.role not in ROLES_STAFF:
        raise HTTPException(status_code=404, detail="Entrenador no encontrado")
    if entrenador.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Para tus propios datos usa el cambio de contraseña",
        )
    if entrenador.role == ROLE_ADMIN:
        raise HTTPException(status_code=400, detail="No se puede modificar al entrenador principal")
    return entrenador


@router.patch("/staff/{staff_id}", response_model=StaffOut)
def update_staff(
    staff_id: int,
    payload: StaffUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    entrenador = _otro_entrenador(db, staff_id, admin)

    if payload.name is not None:
        entrenador.name = payload.name.strip()
    if payload.password is not None:
        entrenador.password_hash = hash_secret(payload.password)
    if payload.is_active is not None:
        entrenador.is_active = payload.is_active

    db.commit()
    db.refresh(entrenador)
    return entrenador


@router.delete("/staff/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff(
    staff_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    """
    Se desactiva en lugar de borrarse: las baterías que creó guardan su id y
    borrarlo dejaría sesiones sin autor.
    """
    entrenador = _otro_entrenador(db, staff_id, admin)
    entrenador.is_active = False
    db.commit()
