from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import adjuntos, anotaciones, auth, coach, export, player, staff
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.migrations import run_migrations
from app.seed import seed

@asynccontextmanager
async def lifespan(_app: FastAPI):
    run_migrations()
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(
    title="Control de Cargas GYM",
    description="API para el control de cargas de un equipo en el gimnasio.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(player.router, prefix="/api")
app.include_router(coach.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(adjuntos.router, prefix="/api")
app.include_router(staff.router, prefix="/api")
app.include_router(anotaciones.router, prefix="/api")


@app.get("/api/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
