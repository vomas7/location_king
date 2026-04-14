#!/usr/bin/env python3
"""
Скрипт для создания миграции Alembic вручную.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from alembic import command
from alembic.config import Config

def create_migration():
    """Создать новую миграцию"""
    # Конфигурация Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Имя миграции
    migration_name = f"enhance_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"Creating migration: {migration_name}")
    
    try:
        # Создаём миграцию
        command.revision(
            alembic_cfg,
            autogenerate=True,
            message=f"enhance models with statistics and ratings",
        )
        print("Migration created successfully!")
    except Exception as e:
        print(f"Error creating migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_migration()