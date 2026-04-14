from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import sessions, rounds, zones
from app.services.satellite_provider import close_satellite_provider

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Location King API")
    yield
    # Shutdown
    logger.info("Shutting down Location King API")
    await close_satellite_provider()


app = FastAPI(
    title="Location King API",
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,  # swagger только в debug
    openapi_url="/api/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(sessions.router)
app.include_router(rounds.router)
app.include_router(zones.router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "location-king-backend",
        "version": "0.1.0",
        "debug": settings.debug,
    }


@app.get("/")
async def root():
    return {
        "message": "Location King API",
        "version": "0.1.0",
        "docs": "/api/docs" if settings.debug else "disabled in production",
        "endpoints": [
            "/api/health",
            "/api/sessions",
            "/api/rounds",
            "/api/zones",
        ]
    }
