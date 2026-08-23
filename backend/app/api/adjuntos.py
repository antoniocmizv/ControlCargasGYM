"""PDF adjuntos a una batería: los sube el entrenador, los ven sus jugadores."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.api.deps import get_current_coach, get_current_user
from app.core.database import get_db
from app.models import ROLES_STAFF, Routine, RoutineAttachment, User
from app.schemas import AttachmentOut
from app.services import adjuntos as almacen
from app.services.routines import player_can_access_routine

router = APIRouter(tags=["adjuntos"])


def _routine_visible(db: Session, routine_id: int, user: User) -> Routine:
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise HTTPException(status_code=404, detail="Batería no encontrada")

    if user.role in ROLES_STAFF:
        return routine
    if not player_can_access_routine(db, user, routine_id):
        raise HTTPException(status_code=403, detail="Esta batería no está asignada a ti")
    return routine


@router.get("/routines/{routine_id}/adjuntos", response_model=list[AttachmentOut])
def list_attachments(
    routine_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _routine_visible(db, routine_id, user).attachments


@router.get("/routines/{routine_id}/adjuntos/{attachment_id}")
def download_attachment(
    routine_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _routine_visible(db, routine_id, user)

    adjunto = db.get(RoutineAttachment, attachment_id)
    if adjunto is None or adjunto.routine_id != routine_id:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")

    ruta = almacen.ruta_de(adjunto.stored_name)
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail="El fichero ya no está disponible")

    return FileResponse(
        ruta,
        media_type=almacen.MIME_PDF,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(adjunto.filename)}"
        },
    )


@router.post(
    "/coach/routines/{routine_id}/adjuntos",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    routine_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    coach: User = Depends(get_current_coach),
):
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise HTTPException(status_code=404, detail="Batería no encontrada")

    stored_name, size = await almacen.guardar_pdf(file)

    adjunto = RoutineAttachment(
        routine_id=routine.id,
        filename=almacen.nombre_seguro(file.filename),
        stored_name=stored_name,
        size_bytes=size,
        uploaded_by=coach.id,
    )
    db.add(adjunto)
    try:
        db.commit()
    except Exception:
        # Si la ficha no llega a guardarse, el fichero no debe quedarse huérfano.
        almacen.borrar(stored_name)
        raise
    db.refresh(adjunto)
    return adjunto


@router.delete("/coach/adjuntos/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: int, db: Session = Depends(get_db), _coach: User = Depends(get_current_coach)
):
    adjunto = db.get(RoutineAttachment, attachment_id)
    if adjunto is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")

    stored_name = adjunto.stored_name
    db.delete(adjunto)
    db.commit()
    almacen.borrar(stored_name)
