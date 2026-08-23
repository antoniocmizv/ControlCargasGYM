"""Generación del reporte .xlsx con las cargas registradas."""

from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Exercise, Routine, RoutineExercise, SetLog, User
from app.services.routines import players_assigned_to

HEADERS = [
    "Fecha",
    "Batería",
    "Jugador",
    "Ejercicio",
    "Categoría",
    "Serie",
    "Kg",
    "Reps hechas",
    "Reps objetivo",
    "Registrado",
]

HEADER_FILL = PatternFill("solid", fgColor="1F2937")
HEADER_FONT = Font(color="FFFFFF", bold=True)
SUBHEADER_FILL = PatternFill("solid", fgColor="374151")
HUECO = "—"

# Una hoja por sesión es útil para una semana o un mes; con el histórico entero
# saldrían cientos de pestañas y el archivo se vuelve imposible de abrir.
MAX_HOJAS_SESION = 50


def _fetch_rows(
    db: Session,
    date_from: date | None,
    date_to: date | None,
    player_id: int | None,
) -> list[tuple]:
    stmt = (
        select(
            Routine.session_date,
            Routine.name,
            User.name,
            Exercise.name,
            Exercise.category,
            SetLog.set_number,
            SetLog.load_kg,
            SetLog.reps,
            RoutineExercise.target_reps,
            SetLog.updated_at,
        )
        .join(User, User.id == SetLog.user_id)
        .join(RoutineExercise, RoutineExercise.id == SetLog.routine_exercise_id)
        .join(Routine, Routine.id == RoutineExercise.routine_id)
        .join(Exercise, Exercise.id == RoutineExercise.exercise_id)
        .order_by(Routine.session_date, User.name, RoutineExercise.position, SetLog.set_number)
    )
    if date_from:
        stmt = stmt.where(Routine.session_date >= date_from)
    if date_to:
        stmt = stmt.where(Routine.session_date <= date_to)
    if player_id:
        stmt = stmt.where(SetLog.user_id == player_id)

    return list(db.execute(stmt).all())


def _autosize(sheet) -> None:
    for index, header in enumerate(HEADERS, start=1):
        longest = max(
            [len(header)] + [len(str(cell.value or "")) for cell in sheet[get_column_letter(index)][1:]]
        )
        sheet.column_dimensions[get_column_letter(index)].width = min(longest + 3, 40)


def build_report(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    player_id: int | None = None,
    por_sesion: bool = False,
) -> BytesIO:
    workbook = Workbook()
    detail = workbook.active
    detail.title = "Cargas"
    detail.append(HEADERS)
    for cell in detail[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")

    rows = _fetch_rows(db, date_from, date_to, player_id)
    for row in rows:
        detail.append(
            [
                row[0],
                row[1],
                row[2],
                row[3],
                row[4] or "",
                row[5],
                float(row[6]),
                row[7],
                row[8],
                row[9].replace(tzinfo=None) if row[9] else None,
            ]
        )

    for row_cells in detail.iter_rows(min_row=2, min_col=1, max_col=1):
        row_cells[0].number_format = "DD/MM/YYYY"
    for row_cells in detail.iter_rows(min_row=2, min_col=10, max_col=10):
        row_cells[0].number_format = "DD/MM/YYYY HH:MM"

    detail.freeze_panes = "A2"
    detail.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{max(detail.max_row, 1)}"
    _autosize(detail)

    _add_summary_sheet(workbook, rows)
    if por_sesion:
        _add_session_sheets(workbook, db, date_from, date_to, player_id)

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def _add_summary_sheet(workbook: Workbook, rows: list[tuple]) -> None:
    """Volumen total (kg x reps) y carga maxima por jugador y ejercicio."""
    summary = workbook.create_sheet("Resumen")
    headers = ["Jugador", "Ejercicio", "Series", "Kg máximo", "Kg medio", "Volumen (kg x reps)"]
    summary.append(headers)
    for cell in summary[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    aggregated: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row[2], row[3])
        load = float(row[6])
        reps = row[7] or 0
        entry = aggregated.setdefault(key, {"sets": 0, "max": 0.0, "total": 0.0, "volume": 0.0})
        entry["sets"] += 1
        entry["max"] = max(entry["max"], load)
        entry["total"] += load
        entry["volume"] += load * reps

    for (player, exercise), entry in sorted(aggregated.items()):
        summary.append(
            [
                player,
                exercise,
                entry["sets"],
                round(entry["max"], 2),
                round(entry["total"] / entry["sets"], 2) if entry["sets"] else 0,
                round(entry["volume"], 2),
            ]
        )

    summary.freeze_panes = "A2"
    for index, header in enumerate(headers, start=1):
        summary.column_dimensions[get_column_letter(index)].width = max(len(header) + 4, 16)


def _nombre_de_hoja(usados: set[str], session_date: date, nombre: str) -> str:
    """Excel limita a 31 caracteres y no admite hojas repetidas ni : \\ / ? * [ ]."""
    limpio = "".join(" " if c in ':\\/?*[]' else c for c in nombre).strip()
    base = f"{session_date:%Y-%m-%d} {limpio}"[:31].strip()
    if base not in usados:
        usados.add(base)
        return base

    for sufijo in range(2, 100):
        marca = f" ({sufijo})"
        candidato = f"{base[: 31 - len(marca)]}{marca}"
        if candidato not in usados:
            usados.add(candidato)
            return candidato

    usados.add(base[:28] + "...")
    return base[:28] + "..."


def _routines_del_periodo(
    db: Session, date_from: date | None, date_to: date | None
) -> list[Routine]:
    stmt = select(Routine).options(
        selectinload(Routine.items).selectinload(RoutineExercise.exercise),
        selectinload(Routine.assignments),
    )
    if date_from:
        stmt = stmt.where(Routine.session_date >= date_from)
    if date_to:
        stmt = stmt.where(Routine.session_date <= date_to)
    return list(db.scalars(stmt.order_by(Routine.session_date, Routine.id)).all())


def _add_session_sheets(
    workbook: Workbook,
    db: Session,
    date_from: date | None,
    date_to: date | None,
    player_id: int | None,
) -> None:
    """Una hoja por sesión: jugadores en filas, una columna por serie."""
    routines = _routines_del_periodo(db, date_from, date_to)
    usados: set[str] = set()

    if len(routines) > MAX_HOJAS_SESION:
        _add_aviso_sheet(workbook, len(routines))
        routines = routines[-MAX_HOJAS_SESION:]

    for routine in routines:
        jugadores = players_assigned_to(db, routine)
        if player_id:
            jugadores = [j for j in jugadores if j.id == player_id]
        if not jugadores or not routine.items:
            continue

        item_ids = [item.id for item in routine.items]
        logs = db.scalars(
            select(SetLog).where(
                SetLog.routine_exercise_id.in_(item_ids),
                SetLog.user_id.in_([j.id for j in jugadores]),
            )
        ).all()
        registradas = {(log.user_id, log.routine_exercise_id, log.set_number): log for log in logs}

        hoja = workbook.create_sheet(_nombre_de_hoja(usados, routine.session_date, routine.name))
        _escribe_parrilla(hoja, routine, jugadores, registradas)


def _escribe_parrilla(hoja, routine: Routine, jugadores: list[User], registradas: dict) -> None:
    hoja["A1"] = routine.name
    hoja["A1"].font = Font(bold=True, size=13)
    hoja["A2"] = f"{routine.session_date:%d/%m/%Y}"
    hoja["A2"].font = Font(color="6B7280")

    # Fila 4: el ejercicio, fusionado sobre sus series. Fila 5: el número de serie.
    fila_ejercicio, fila_serie, primera_fila = 4, 5, 6
    hoja.cell(row=fila_serie, column=1, value="Jugador")

    columna = 2
    for item in routine.items:
        titulo = item.exercise.name
        if item.target_reps:
            titulo = f"{titulo} ({item.sets}×{item.target_reps})"
        celda = hoja.cell(row=fila_ejercicio, column=columna, value=titulo)
        celda.font = HEADER_FONT
        celda.fill = HEADER_FILL
        celda.alignment = Alignment(horizontal="center")
        if item.sets > 1:
            hoja.merge_cells(
                start_row=fila_ejercicio,
                start_column=columna,
                end_row=fila_ejercicio,
                end_column=columna + item.sets - 1,
            )
        for numero in range(1, item.sets + 1):
            serie = hoja.cell(row=fila_serie, column=columna, value=f"S{numero}")
            serie.font = HEADER_FONT
            serie.fill = SUBHEADER_FILL
            serie.alignment = Alignment(horizontal="center")
            columna += 1

    for cabecera in (hoja.cell(row=fila_serie, column=1),):
        cabecera.font = HEADER_FONT
        cabecera.fill = HEADER_FILL

    for indice, jugador in enumerate(jugadores):
        fila = primera_fila + indice
        hoja.cell(row=fila, column=1, value=jugador.name)
        columna = 2
        for item in routine.items:
            for numero in range(1, item.sets + 1):
                log = registradas.get((jugador.id, item.id, numero))
                celda = hoja.cell(
                    row=fila,
                    column=columna,
                    value=float(log.load_kg) if log else HUECO,
                )
                celda.alignment = Alignment(horizontal="center")
                if log is None:
                    celda.font = Font(color="9CA3AF")
                columna += 1

    hoja.freeze_panes = hoja.cell(row=primera_fila, column=2)
    hoja.column_dimensions["A"].width = max(
        [len("Jugador")] + [len(j.name) for j in jugadores]
    ) + 4
    for indice in range(2, columna):
        hoja.column_dimensions[get_column_letter(indice)].width = 7


def _add_aviso_sheet(workbook: Workbook, total: int) -> None:
    hoja = workbook.create_sheet("Aviso", 2)
    hoja["A1"] = "Demasiadas sesiones en el periodo"
    hoja["A1"].font = Font(bold=True, size=13)
    hoja["A3"] = (
        f"El periodo elegido tiene {total} sesiones y solo se han incluido las "
        f"{MAX_HOJAS_SESION} más recientes como hoja."
    )
    hoja["A4"] = "Acota las fechas para tenerlas todas. El detalle completo sigue en «Cargas»."
    hoja.column_dimensions["A"].width = 90
