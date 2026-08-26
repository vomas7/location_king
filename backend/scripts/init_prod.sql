-- Выполняется один раз при первом старте контейнера PostgreSQL.
-- Здесь только то, что нельзя сделать миграцией: расширения ставит суперпользователь.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
