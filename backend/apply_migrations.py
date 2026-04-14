#!/usr/bin/env python3
"""
Скрипт для применения миграций Alembic.
"""
import os
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from alembic import command
from alembic.config import Config

def apply_migrations():
    """Применить все миграции"""
    # Конфигурация Alembic
    alembic_cfg = Config("alembic.ini")
    
    print("Applying migrations...")
    
    try:
        # Применяем миграции
        command.upgrade(alembic_cfg, "head")
        print("Migrations applied successfully!")
        
        # Показываем текущую ревизию
        current = command.current(alembic_cfg)
        print(f"Current revision: {current}")
        
    except Exception as e:
        print(f"Error applying migrations: {e}")
        sys.exit(1)

def show_history():
    """Показать историю миграций"""
    alembic_cfg = Config("alembic.ini")
    
    print("Migration history:")
    command.history(alembic_cfg)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "history":
        show_history()
    else:
        apply_migrations()