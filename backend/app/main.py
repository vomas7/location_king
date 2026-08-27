"""Точка входа приложения."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppError
from app.routers import auth, leaderboard, rounds, sessions, zones
from app.services.tiles import close_clients

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Location King API запускается")
    yield
    await close_clients()
    logger.info("Location King API остановлен")


app = FastAPI(
    title="Location King API",
    version="1.0.0",
    description="Геогессер по спутниковым снимкам: найди на карте центр показанного участка.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Ошибки бизнес-логики отдаются в том же формате, что и ошибки FastAPI."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(rounds.router)
app.include_router(zones.router)
app.include_router(leaderboard.router)


@app.get("/api/health", tags=["service"])
async def health() -> dict[str, str]:
    """Проверка живости сервиса."""
    return {"status": "ok", "service": "location-king-backend", "version": app.version}
