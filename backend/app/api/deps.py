from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import ROLE_ADMIN, ROLES_STAFF, User

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sesión no válida o caducada",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise CREDENTIALS_ERROR

    payload = decode_access_token(credentials.credentials)
    if payload is None or not payload.get("sub"):
        raise CREDENTIALS_ERROR

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


def get_current_coach(user: User = Depends(get_current_user)) -> User:
    """Cualquier entrenador, principal o no."""
    if user.role not in ROLES_STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el entrenador puede acceder a esta sección",
        )
    return user


def get_current_admin(user: User = Depends(get_current_coach)) -> User:
    """Solo el entrenador principal gestiona a los demás entrenadores."""
    if user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el entrenador principal puede gestionar entrenadores",
        )
    return user
