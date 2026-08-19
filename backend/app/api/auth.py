from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, verify_secret
from app.models import ROLE_COACH, ROLE_PLAYER, User
from app.schemas import CoachLogin, PlayerLogin, PlayerOption, Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

BAD_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
)


@router.get("/players", response_model=list[PlayerOption])
def list_player_options(db: Session = Depends(get_db)):
    """Lista publica de jugadores para el selector de la pantalla de login."""
    stmt = (
        select(User)
        .where(User.role == ROLE_PLAYER, User.is_active.is_(True))
        .order_by(User.name)
    )
    return db.scalars(stmt).all()


@router.post("/login/player", response_model=Token)
def login_player(payload: PlayerLogin, db: Session = Depends(get_db)):
    user = db.get(User, payload.user_id)
    if user is None or user.role != ROLE_PLAYER or not user.is_active:
        raise BAD_CREDENTIALS
    if not verify_secret(payload.pin, user.pin_hash):
        raise BAD_CREDENTIALS
    return Token(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.post("/login/coach", response_model=Token)
def login_coach(payload: CoachLogin, db: Session = Depends(get_db)):
    stmt = select(User).where(User.username == payload.username, User.role == ROLE_COACH)
    user = db.scalars(stmt).first()
    if user is None or not user.is_active:
        raise BAD_CREDENTIALS
    if not verify_secret(payload.password, user.password_hash):
        raise BAD_CREDENTIALS
    return Token(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_user)):
    return user
