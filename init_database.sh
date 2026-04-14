#!/bin/bash
# Скрипт для инициализации базы данных

set -e

echo "=== Initializing Location King Database ==="

# Проверяем, запущен ли Docker Compose
if ! docker-compose ps postgres 2>/dev/null | grep -q "Up"; then
    echo "Starting PostgreSQL container..."
    docker-compose up -d postgres
    
    # Ждём, пока PostgreSQL запустится
    echo "Waiting for PostgreSQL to start..."
    sleep 5
fi

# Получаем IP контейнера PostgreSQL
POSTGRES_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' location_king_postgres 2>/dev/null || echo "localhost")

echo "PostgreSQL is running at $POSTGRES_IP:5432"

# Создаём базу данных, если её нет
echo "Creating database if not exists..."
docker-compose exec -T postgres psql -U locationking -c "SELECT 1 FROM pg_database WHERE datname = 'location_king'" | grep -q 1 || \
docker-compose exec -T postgres psql -U locationking -c "CREATE DATABASE location_king;"

# Включаем расширение PostGIS
echo "Enabling PostGIS extension..."
docker-compose exec -T postgres psql -U locationking -d location_king -c "CREATE EXTENSION IF NOT EXISTS postgis;"
docker-compose exec -T postgres psql -U locationking -d location_king -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"

echo "Database initialized successfully!"

# Применяем миграции Alembic
echo "=== Applying Alembic Migrations ==="
cd backend

# Создаём .env файл для бэкенда
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://locationking:locationking123@$POSTGRES_IP:5432/location_king
REDIS_URL=redis://:redis123@localhost:6379/0
MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=location-king
KEYCLOAK_CLIENT_ID=location-king-client
DEBUG=true
EOF

# Применяем миграции через Python
echo "Applying migrations..."
python3 apply_migrations.py

# Инициализируем тестовые данные
echo "=== Initializing Test Data ==="
python3 scripts/init_test_data.py

# Добавляем дополнительные зоны
echo "=== Adding Additional Zones ==="
python3 scripts/add_more_zones.py

echo "=== Database Setup Complete ==="
echo "Database is ready for use!"
echo "You can now start the application with: docker-compose up --build"