#!/usr/bin/env python3
"""
Запуск только mock API для тестирования исправлений
"""

import sys
import os

# Добавляем путь к модулю app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Создаем приложение
app = FastAPI(title="Location King Mock API", version="1.0.0")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Импортируем mock router
from app.game_mock import router as mock_router
app.include_router(mock_router)

@app.get("/")
async def root():
    return {"message": "Location King Mock API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    print("🚀 Запуск Location King Mock API на http://0.0.0.0:8000")
    print("📚 Документация: http://localhost:8000/docs")
    print("🔧 Mock endpoints доступны по префиксу /api/mock")
    uvicorn.run("run_mock_api:app", host="0.0.0.0", port=8000, reload=True)