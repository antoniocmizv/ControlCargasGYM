from datetime import date, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_coach
from app.core.database import get_db
from app.services.excel import build_report

router = APIRouter(prefix="/export", tags=["export"], dependencies=[Depends(get_current_coach)])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/excel")
def export_excel(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    player_id: int | None = Query(default=None),
    routine_id: int | None = Query(
        default=None, description="Exporta solo esa sesión, con su parrilla"
    ),
    db: Session = Depends(get_db),
):
    buffer = build_report(db, date_from, date_to, player_id, routine_id=routine_id)
    filename = f"cargas_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return StreamingResponse(
        buffer,
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
