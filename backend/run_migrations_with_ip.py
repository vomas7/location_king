#!/usr/bin/env python3
"""
Скрипт для применения миграций с использованием IP адреса.
"""
import os
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from alembic import command
from alembic.config import Config

def apply_migrations():
    """Применить все миграции с использованием IP адреса"""
    # Конфигурация Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Используем IP адрес вместо имени хоста
    # postgresql+psycopg2://postgres:postgres@172.18.0.7:5432/location_king
    database_url = "postgresql+psycopg2://postgres:postgres@172.18.0.7:5432/location_king"
    
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    print("Applying migrations with IP address...")
    
    try:
        # Применяем миграции
        command.upgrade(alembic_cfg, "head")
        print("Migrations applied successfully!")
        
        # Показываем текущую ревизию
        current = command.current(alembic_cfg)
        print(f"Current revision: {current}")
        
    except Exception as e:
        print(f"Error applying migrations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    apply_migrations()