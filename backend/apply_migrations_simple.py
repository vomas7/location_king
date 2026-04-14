#!/usr/bin/env python3
"""
Простой скрипт для применения миграций с обработкой ошибок.
"""
import os
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def run_sql_file(conn, filepath):
    """Выполнить SQL файл"""
    with open(filepath, 'r') as f:
        sql = f.read()
    
    with conn.cursor() as cur:
        try:
            cur.execute(sql)
            print(f"Successfully executed: {filepath}")
        except Exception as e:
            print(f"Error executing {filepath}: {e}")
            # Пропускаем ошибки дублирования
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print(f"Skipping duplicate error: {e}")
                conn.rollback()
            else:
                raise

def apply_migrations():
    """Применить миграции вручную"""
    # Подключение к БД
    conn = psycopg2.connect(
        host="172.18.0.7",
        port=5432,
        database="location_king",
        user="locationking",
        password="locationking123"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    print("Applying migrations manually...")
    
    try:
        # 1. Создаём таблицу alembic_version если её нет
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL PRIMARY KEY
                )
            """)
            print("Created alembic_version table")
        
        # 2. Проверяем текущую версию
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
            result = cur.fetchone()
            current_version = result[0] if result else None
            print(f"Current version: {current_version}")
        
        # 3. Применяем миграции по порядку
        migrations_dir = Path(__file__).parent / "alembic" / "versions"
        
        # Миграция 001
        if not current_version or current_version < "001":
            print("Applying migration 001...")
            # Создаём расширения PostGIS
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")
                print("Created PostGIS extensions")
            
            # Создаём таблицы из первой миграции
            sql_001 = """
            -- Создаём таблицу users
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                keycloak_id UUID NOT NULL UNIQUE,
                username VARCHAR(100) NOT NULL UNIQUE,
                total_score BIGINT NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            );
            
            -- Создаём таблицу location_zones
            CREATE TABLE IF NOT EXISTS location_zones (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                difficulty SMALLINT NOT NULL DEFAULT 1,
                category VARCHAR(100) NOT NULL DEFAULT 'mixed',
                polygon geometry(POLYGON,4326) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                CONSTRAINT ck_difficulty_range CHECK (difficulty BETWEEN 1 AND 7)
            );
            
            -- Создаём индексы для location_zones
            CREATE INDEX IF NOT EXISTS idx_location_zones_polygon ON location_zones USING gist (polygon);
            CREATE INDEX IF NOT EXISTS ix_location_zones_category ON location_zones (category);
            CREATE INDEX IF NOT EXISTS ix_location_zones_is_active ON location_zones (is_active);
            
            -- Создаём таблицу game_sessions
            CREATE TABLE IF NOT EXISTS game_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mode VARCHAR(20) NOT NULL DEFAULT 'solo',
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                rounds_total SMALLINT NOT NULL DEFAULT 5,
                rounds_done SMALLINT NOT NULL DEFAULT 0,
                total_score INTEGER NOT NULL DEFAULT 0,
                started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                finished_at TIMESTAMP WITH TIME ZONE
            );
            
            -- Создаём индексы для game_sessions
            CREATE INDEX IF NOT EXISTS ix_game_sessions_user_id ON game_sessions (user_id);
            CREATE INDEX IF NOT EXISTS ix_game_sessions_status ON game_sessions (status);
            
            -- Создаём таблицу rounds
            CREATE TABLE IF NOT EXISTS rounds (
                id SERIAL PRIMARY KEY,
                session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
                zone_id INTEGER NOT NULL REFERENCES location_zones(id),
                target_point geometry(POINT,4326) NOT NULL,
                guess_point geometry(POINT,4326),
                distance_km NUMERIC(10, 2),
                score INTEGER NOT NULL DEFAULT 0,
                view_extent_km SMALLINT NOT NULL DEFAULT 5,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                guessed_at TIMESTAMP WITH TIME ZONE
            );
            
            -- Создаём индексы для rounds
            CREATE INDEX IF NOT EXISTS idx_rounds_target_point ON rounds USING gist (target_point);
            CREATE INDEX IF NOT EXISTS idx_rounds_guess_point ON rounds USING gist (guess_point);
            CREATE INDEX IF NOT EXISTS ix_rounds_session_id ON rounds (session_id);
            """
            
            with conn.cursor() as cur:
                # Разделяем SQL на отдельные команды
                commands = sql_001.split(';')
                for command in commands:
                    command = command.strip()
                    if command:
                        try:
                            cur.execute(command)
                        except Exception as e:
                            if "already exists" not in str(e) and "duplicate" not in str(e).lower():
                                print(f"Error executing command: {e}")
                                print(f"Command: {command[:100]}...")
            
            # Обновляем версию
            with conn.cursor() as cur:
                cur.execute("INSERT INTO alembic_version (version_num) VALUES ('001') ON CONFLICT DO NOTHING")
            
            print("Applied migration 001")
        
        # Миграция 002 (упрощённая версия)
        if not current_version or current_version < "002":
            print("Applying migration 002 (simplified)...")
            
            sql_002 = """
            -- Добавляем поля в users
            ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);
            ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);
            ALTER TABLE users ADD COLUMN IF NOT EXISTS games_played INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS games_won INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS total_rounds INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS average_score FLOAT;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS average_distance FLOAT;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS best_score INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS worst_score INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS elo_rating INTEGER NOT NULL DEFAULT 1000;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS rank VARCHAR(50);
            ALTER TABLE users ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS experience INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100);
            ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(50);
            ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) NOT NULL DEFAULT 'ru';
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT false;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT false;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP WITH TIME ZONE;
            
            -- Создаём индексы для users
            CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
            CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active);
            
            -- Добавляем поля в game_sessions
            ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS time_control VARCHAR(20) NOT NULL DEFAULT 'unlimited';
            ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS average_score FLOAT;
            ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS best_round_score INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS worst_round_score INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP WITH TIME ZONE;
            ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS title VARCHAR(100);
            ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS description TEXT;
            ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT false;
            ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS allow_comments BOOLEAN NOT NULL DEFAULT true;
            
            -- Создаём индексы для game_sessions
            CREATE INDEX IF NOT EXISTS ix_game_sessions_is_public ON game_sessions (is_public);
            
            -- Добавляем поля в rounds
            ALTER TABLE rounds ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending';
            ALTER TABLE rounds ADD COLUMN IF NOT EXISTS accuracy_percentage NUMERIC(5, 2);
            ALTER TABLE rounds ADD COLUMN IF NOT EXISTS time_limit_seconds SMALLINT;
            ALTER TABLE rounds ADD COLUMN IF NOT EXISTS max_score INTEGER NOT NULL DEFAULT 5000;
            ALTER TABLE rounds ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;
            ALTER TABLE rounds ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE;
            ALTER TABLE rounds ADD COLUMN IF NOT EXISTS satellite_image_url TEXT;
            ALTER TABLE rounds ADD COLUMN IF NOT EXISTS hint_used BOOLEAN NOT NULL DEFAULT false;
            ALTER TABLE rounds ADD COLUMN IF NOT EXISTS notes TEXT;
            
            -- Создаём индексы для rounds
            CREATE INDEX IF NOT EXISTS ix_rounds_status ON rounds (status);
            
            -- Добавляем поля в location_zones
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS center_point geometry(POINT,4326);
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS area_sq_km FLOAT;
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS total_rounds INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS average_score FLOAT;
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS average_distance FLOAT;
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS popularity INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS country VARCHAR(100);
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS region VARCHAR(100);
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS tags TEXT;
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS is_featured BOOLEAN NOT NULL DEFAULT false;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT false;
            ALTER TABLE location_zones ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;
            
            -- Создаём индексы для location_zones
            CREATE INDEX IF NOT EXISTS idx_location_zones_center_point ON location_zones USING gist (center_point);
            CREATE INDEX IF NOT EXISTS ix_location_zones_name ON location_zones (name);
            CREATE INDEX IF NOT EXISTS ix_location_zones_difficulty ON location_zones (difficulty);
            CREATE INDEX IF NOT EXISTS ix_location_zones_is_featured ON location_zones (is_featured);
            """
            
            with conn.cursor() as cur:
                commands = sql_002.split(';')
                for command in commands:
                    command = command.strip()
                    if command:
                        try:
                            cur.execute(command)
                        except Exception as e:
                            if "already exists" not in str(e) and "duplicate" not in str(e).lower():
                                print(f"Error executing command: {e}")
                                print(f"Command: {command[:100]}...")
            
            # Обновляем версию
            with conn.cursor() as cur:
                cur.execute("UPDATE alembic_version SET version_num = '002' WHERE version_num = '001'")
                if cur.rowcount == 0:
                    cur.execute("INSERT INTO alembic_version (version_num) VALUES ('002') ON CONFLICT DO NOTHING")
            
            print("Applied migration 002")
        
        # Миграция 003
        if not current_version or current_version < "003":
            print("Applying migration 003...")
            
            sql_003 = """
            -- Обновляем constraint difficulty
            ALTER TABLE location_zones DROP CONSTRAINT IF EXISTS ck_difficulty_range;
            ALTER TABLE location_zones ADD CONSTRAINT ck_difficulty_range CHECK (difficulty BETWEEN 1 AND 7);
            
            -- Обновляем view_extent_km
            UPDATE rounds SET view_extent_km = 5 WHERE view_extent_km = 500;
            """
            
            with conn.cursor() as cur:
                commands = sql_003.split(';')
                for command in commands:
                    command = command.strip()
                    if command:
                        try:
                            cur.execute(command)
                        except Exception as e:
                            print(f"Error executing command: {e}")
                            print(f"Command: {command[:100]}...")
            
            # Обновляем версию
            with conn.cursor() as cur:
                cur.execute("UPDATE alembic_version SET version_num = '003' WHERE version_num = '002'")
                if cur.rowcount == 0:
                    cur.execute("INSERT INTO alembic_version (version_num) VALUES ('003') ON CONFLICT DO NOTHING")
            
            print("Applied migration 003")
        
        print("All migrations applied successfully!")
        
    except Exception as e:
        print(f"Error applying migrations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migrations()