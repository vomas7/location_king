-- Включаем PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- ─── Полигоны локаций ────────────────────────────────────────
-- Здесь хранятся области, внутри которых будет выбираться
-- случайная точка для раунда
CREATE TABLE IF NOT EXISTS location_zones (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    difficulty  SMALLINT NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    -- 1=очень легко (большие города), 5=очень сложно (глушь)
    category    VARCHAR(100),           -- 'city', 'nature', 'architecture', etc.
    polygon     GEOMETRY(POLYGON, 4326) NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_location_zones_polygon
    ON location_zones USING GIST (polygon);
CREATE INDEX IF NOT EXISTS idx_location_zones_difficulty
    ON location_zones (difficulty);

-- ─── Пользователи (синхронизируются с Keycloak по sub) ───────
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    keycloak_id UUID UNIQUE NOT NULL,   -- sub из JWT
    username    VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    total_score BIGINT DEFAULT 0
);

-- ─── Игровые сессии ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS game_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     INTEGER REFERENCES users(id),
    mode        VARCHAR(20) DEFAULT 'solo',  -- 'solo' | 'multiplayer'
    total_score INTEGER DEFAULT 0,
    rounds_total SMALLINT DEFAULT 5,
    rounds_done  SMALLINT DEFAULT 0,
    status      VARCHAR(20) DEFAULT 'active', -- 'active' | 'finished'
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

-- ─── Раунды ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rounds (
    id              SERIAL PRIMARY KEY,
    session_id      UUID REFERENCES game_sessions(id) ON DELETE CASCADE,
    zone_id         INTEGER REFERENCES location_zones(id),
    target_point    GEOMETRY(POINT, 4326) NOT NULL,  -- правильный ответ
    guess_point     GEOMETRY(POINT, 4326),            -- ответ пользователя
    distance_km     NUMERIC(10, 2),                   -- PostGIS считает
    score           INTEGER DEFAULT 0,
    view_extent_km  INTEGER DEFAULT 500,              -- размер экстента для раунда
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    guessed_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_rounds_session
    ON rounds (session_id);
