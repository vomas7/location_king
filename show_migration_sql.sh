#!/bin/bash
echo "=== SQL команды для миграций Location King ==="
echo ""
echo "Миграция 001 (initial):"
echo "----------------------"
cat << 'EOF'
-- 1. Создать расширение PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 2. Таблица users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    keycloak_id UUID NOT NULL,
    username VARCHAR(100) NOT NULL,
    total_score BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX ix_users_keycloak_id ON users(keycloak_id);

-- 3. Таблица location_zones
CREATE TABLE location_zones (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty SMALLINT NOT NULL DEFAULT 1,
    category VARCHAR(100),
    polygon GEOMETRY(POLYGON, 4326) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_location_zones_polygon ON location_zones USING GIST(polygon);

-- 4. Таблица game_sessions
CREATE TABLE game_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode VARCHAR(20) NOT NULL DEFAULT 'solo',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    rounds_total SMALLINT NOT NULL DEFAULT 5,
    rounds_completed SMALLINT NOT NULL DEFAULT 0,
    total_score INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    CONSTRAINT fk_game_sessions_user FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX ix_game_sessions_user_id ON game_sessions(user_id);
CREATE INDEX ix_game_sessions_status ON game_sessions(status);

-- 5. Таблица rounds
CREATE TABLE rounds (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    zone_id INTEGER NOT NULL REFERENCES location_zones(id) ON DELETE RESTRICT,
    target_lng NUMERIC(9,6) NOT NULL,
    target_lat NUMERIC(9,6) NOT NULL,
    guess_lng NUMERIC(9,6),
    guess_lat NUMERIC(9,6),
    distance_km NUMERIC(10,3),
    score INTEGER,
    view_extent_km INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_rounds_session FOREIGN KEY (session_id) REFERENCES game_sessions(id),
    CONSTRAINT fk_rounds_zone FOREIGN KEY (zone_id) REFERENCES location_zones(id)
);
CREATE INDEX ix_rounds_session_id ON rounds(session_id);
CREATE INDEX ix_rounds_zone_id ON rounds(zone_id);
EOF

echo ""
echo "Миграция 002 (enhancements):"
echo "---------------------------"
cat << 'EOF'
-- 1. Расширение таблицы users
ALTER TABLE users ADD COLUMN email VARCHAR(255);
ALTER TABLE users ADD COLUMN display_name VARCHAR(100);
ALTER TABLE users ADD COLUMN games_played INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN games_won INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN total_rounds INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN average_score FLOAT;
ALTER TABLE users ADD COLUMN average_distance FLOAT;
ALTER TABLE users ADD COLUMN best_score INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN worst_score INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN elo_rating INTEGER NOT NULL DEFAULT 1000;
ALTER TABLE users ADD COLUMN rank VARCHAR(50);
ALTER TABLE users ADD COLUMN level INTEGER NOT NULL DEFAULT 1;
ALTER TABLE users ADD COLUMN experience INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN avatar_url TEXT;
ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN country VARCHAR(100);
ALTER TABLE users ADD COLUMN timezone VARCHAR(50);
ALTER TABLE users ADD COLUMN language VARCHAR(10) NOT NULL DEFAULT 'ru';
ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN is_premium BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN updated_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN last_activity_at TIMESTAMPTZ;

CREATE UNIQUE INDEX ix_users_email ON users(email);
CREATE UNIQUE INDEX ix_users_username ON users(username);
CREATE INDEX ix_users_is_active ON users(is_active);

-- 2. Расширение таблицы game_sessions
ALTER TABLE game_sessions ADD COLUMN time_control VARCHAR(20) NOT NULL DEFAULT 'unlimited';
ALTER TABLE game_sessions ADD COLUMN average_score INTEGER DEFAULT 0;
ALTER TABLE game_sessions ADD COLUMN best_round_score INTEGER NOT NULL DEFAULT 0;
ALTER TABLE game_sessions ADD COLUMN worst_round_score INTEGER NOT NULL DEFAULT 0;
ALTER TABLE game_sessions ADD COLUMN last_activity_at TIMESTAMPTZ;
ALTER TABLE game_sessions ADD COLUMN title VARCHAR(100);
ALTER TABLE game_sessions ADD COLUMN description TEXT;
ALTER TABLE game_sessions ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE game_sessions ADD COLUMN allow_comments BOOLEAN NOT NULL DEFAULT true;

CREATE INDEX ix_game_sessions_is_public ON game_sessions(is_public);

-- 3. Расширение таблицы rounds
ALTER TABLE rounds ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending';
ALTER TABLE rounds ADD COLUMN accuracy_percentage NUMERIC(5,2);
ALTER TABLE rounds ADD COLUMN time_limit_seconds SMALLINT;
ALTER TABLE rounds ADD COLUMN max_score INTEGER NOT NULL DEFAULT 5000;
ALTER TABLE rounds ADD COLUMN started_at TIMESTAMPTZ;
ALTER TABLE rounds ADD COLUMN completed_at TIMESTAMPTZ;
ALTER TABLE rounds ADD COLUMN satellite_image_url TEXT;
ALTER TABLE rounds ADD COLUMN hint_used BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE rounds ADD COLUMN notes TEXT;

ALTER TABLE rounds ALTER COLUMN view_extent_km SET DEFAULT 5;

CREATE INDEX ix_rounds_status ON rounds(status);

-- 4. Расширение таблицы location_zones
ALTER TABLE location_zones ADD COLUMN center_point GEOMETRY(POINT, 4326);
ALTER TABLE location_zones ADD COLUMN area_sq_km FLOAT;
ALTER TABLE location_zones ADD COLUMN total_rounds INTEGER NOT NULL DEFAULT 0;
ALTER TABLE location_zones ADD COLUMN average_score FLOAT;
ALTER TABLE location_zones ADD COLUMN average_distance FLOAT;
ALTER TABLE location_zones ADD COLUMN popularity INTEGER NOT NULL DEFAULT 0;
ALTER TABLE location_zones ADD COLUMN country VARCHAR(100);
ALTER TABLE location_zones ADD COLUMN region VARCHAR(100);
ALTER TABLE location_zones ADD COLUMN tags TEXT;
ALTER TABLE location_zones ADD COLUMN thumbnail_url TEXT;
ALTER TABLE location_zones ADD COLUMN is_featured BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE location_zones ADD COLUMN is_premium BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE location_zones ADD COLUMN updated_at TIMESTAMPTZ;

UPDATE location_zones SET category = 'mixed' WHERE category IS NULL;
ALTER TABLE location_zones ALTER COLUMN category SET NOT NULL;
ALTER TABLE location_zones ALTER COLUMN category SET DEFAULT 'mixed';

CREATE INDEX ix_location_zones_name ON location_zones(name);
CREATE INDEX ix_location_zones_difficulty ON location_zones(difficulty);
CREATE INDEX ix_location_zones_category ON location_zones(category);
CREATE INDEX ix_location_zones_is_active ON location_zones(is_active);
CREATE INDEX ix_location_zones_is_featured ON location_zones(is_featured);
EOF

echo ""
echo "=== Инструкция по применению ==="
echo ""
echo "1. Установите PostgreSQL с PostGIS:"
echo "   sudo apt-get install postgresql postgresql-contrib postgis"
echo ""
echo "2. Создайте базу данных и пользователя:"
echo "   sudo -u postgres psql -c \"CREATE USER locationking WITH PASSWORD 'locationking123';\""
echo "   sudo -u postgres psql -c \"CREATE DATABASE location_king;\""
echo "   sudo -u postgres psql -d location_king -c \"GRANT ALL PRIVILEGES ON DATABASE location_king TO locationking;\""
echo ""
echo "3. Примените SQL команды выше через psql:"
echo "   sudo -u postgres psql -d location_king -f миграции.sql"
echo ""
echo "Или используйте готовый скрипт:"
echo "   cd /home/ilya/location_king"
echo "   ./setup_local_dev.sh"