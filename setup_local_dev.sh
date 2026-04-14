#!/bin/bash
# Скрипт для локальной разработки (без Docker)

set -e

echo "=== Setting up Local Development Environment ==="

# 1. Проверяем PostgreSQL
echo "1. Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is not installed. Please install it first."
    echo "Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
    echo "macOS: brew install postgresql"
    exit 1
fi

# 2. Создаём базу данных
echo "2. Creating database..."
sudo -u postgres psql -c "CREATE DATABASE location_king;" 2>/dev/null || true

# 3. Включаем PostGIS
echo "3. Enabling PostGIS extensions..."
sudo -u postgres psql -d location_king -c "CREATE EXTENSION IF NOT EXISTS postgis;" 2>/dev/null || true
sudo -u postgres psql -d location_king -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;" 2>/dev/null || true

# 4. Создаём пользователя
echo "4. Creating database user..."
sudo -u postgres psql -c "CREATE USER locationking WITH PASSWORD 'locationking123';" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE location_king TO locationking;" 2>/dev/null || true

# 5. Настраиваем бэкенд
echo "5. Setting up backend..."
cd backend

# Создаём .env файл
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://locationking:locationking123@localhost:5432/location_king
REDIS_URL=redis://localhost:6379/0
MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=location-king
KEYCLOAK_CLIENT_ID=location-king-client
DEBUG=true
EOF

# 6. Создаём виртуальное окружение
echo "6. Creating virtual environment..."
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate

# 7. Устанавливаем зависимости
echo "7. Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 8. Применяем миграции
echo "8. Applying migrations..."
python3 apply_migrations.py

# 9. Инициализируем тестовые данные
echo "9. Initializing test data..."
python3 scripts/init_test_data.py

# 10. Добавляем дополнительные зоны
echo "10. Adding additional zones..."
python3 scripts/add_more_zones.py

echo "=== Setup Complete ==="
echo ""
echo "To start the backend:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "To start the frontend (simple server):"
echo "  cd frontend"
echo "  python3 -m http.server 8080"
echo ""
echo "Then open: http://localhost:8080"