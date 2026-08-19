from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, coach, export, player
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.seed import seed

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
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


@app.get("/api/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
