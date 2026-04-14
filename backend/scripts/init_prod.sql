-- Production database initialization script
-- Run automatically when PostgreSQL container starts

-- Enable PostGIS extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create read-only user for analytics (optional)
CREATE USER locationking_readonly WITH PASSWORD 'readonly_password_here';
GRANT CONNECT ON DATABASE location_king_prod TO locationking_readonly;
GRANT USAGE ON SCHEMA public TO locationking_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO locationking_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO locationking_readonly;

-- Create backup user (optional)
CREATE USER locationking_backup WITH PASSWORD 'backup_password_here';
GRANT CONNECT ON DATABASE location_king_prod TO locationking_backup;

-- Set up monitoring extensions (optional)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configure performance settings (run as superuser in production)
-- ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
-- ALTER SYSTEM SET max_connections = '200';
-- ALTER SYSTEM SET shared_buffers = '512MB';
-- ALTER SYSTEM SET effective_cache_size = '1536MB';
-- ALTER SYSTEM SET maintenance_work_mem = '128MB';
-- ALTER SYSTEM SET checkpoint_completion_target = '0.9';
-- ALTER SYSTEM SET wal_buffers = '16MB';
-- ALTER SYSTEM SET default_statistics_target = '100';
-- ALTER SYSTEM SET random_page_cost = '1.1';
-- ALTER SYSTEM SET effective_io_concurrency = '200';
-- ALTER SYSTEM SET work_mem = '2621kB';
-- ALTER SYSTEM SET min_wal_size = '1GB';
-- ALTER SYSTEM SET max_wal_size = '4GB';

-- Create indexes for performance (will be created by Alembic, but adding critical ones here)
-- CREATE INDEX IF NOT EXISTS idx_rounds_session_id ON rounds(session_id);
-- CREATE INDEX IF NOT EXISTS idx_rounds_zone_id ON rounds(zone_id);
-- CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON game_sessions(user_id);
-- CREATE INDEX IF NOT EXISTS idx_game_sessions_status ON game_sessions(status);
-- CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Create partition for rounds table (for large-scale deployments)
-- CREATE TABLE rounds_2024 PARTITION OF rounds FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
-- CREATE TABLE rounds_2025 PARTITION OF rounds FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Production database initialization completed successfully';
END $$;