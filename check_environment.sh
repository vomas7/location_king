#!/bin/bash
echo "=== Проверка окружения для Location King ==="
echo ""

# Проверка Docker
echo "1. Проверка Docker:"
if command -v docker &> /dev/null; then
    echo "   ✅ Docker установлен: $(docker --version)"
else
    echo "   ❌ Docker не установлен"
fi

# Проверка Docker Compose
echo "2. Проверка Docker Compose:"
if command -v docker-compose &> /dev/null; then
    echo "   ✅ Docker Compose установлен: $(docker-compose --version)"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    echo "   ✅ Docker Compose (плагин) доступен"
else
    echo "   ❌ Docker Compose не установлен"
fi

# Проверка PostgreSQL
echo "3. Проверка PostgreSQL:"
if command -v psql &> /dev/null; then
    echo "   ✅ PostgreSQL клиент установлен: $(psql --version)"
    
    # Проверка сервера
    if pg_isready &> /dev/null; then
        echo "   ✅ Сервер PostgreSQL запущен"
    else
        echo "   ⚠️  Сервер PostgreSQL не запущен"
    fi
else
    echo "   ❌ PostgreSQL не установлен"
fi

# Проверка Python
echo "4. Проверка Python:"
if command -v python3 &> /dev/null; then
    echo "   ✅ Python установлен: $(python3 --version)"
    
    # Проверка зависимостей
    echo "5. Проверка Python зависимостей:"
    cd backend 2>/dev/null && python3 -c "
import sys
deps = ['fastapi', 'sqlalchemy', 'alembic', 'asyncpg', 'psycopg2-binary']
missing = []
for dep in deps:
    try:
        __import__(dep.replace('-', '_'))
    except ImportError:
        missing.append(dep)
if missing:
    print(f'   ❌ Отсутствуют: {missing}')
else:
    print('   ✅ Все зависимости установлены')
" 2>/dev/null || echo "   ⚠️  Не удалось проверить зависимости"
    cd ..
else
    echo "   ❌ Python не установлен"
fi

echo ""
echo "=== Рекомендации ==="
echo ""
echo "Вариант A: Установить Docker и Docker Compose"
echo "  sudo apt-get install docker.io docker-compose"
echo ""
echo "Вариант B: Установить PostgreSQL локально"
echo "  sudo apt-get install postgresql postgresql-contrib postgis"
echo "  sudo -u postgres psql -c \"CREATE USER locationking WITH PASSWORD 'locationking123';\""
echo "  sudo -u postgres psql -c \"CREATE DATABASE location_king;\""
echo "  sudo -u postgres psql -d location_king -c \"GRANT ALL PRIVILEGES ON DATABASE location_king TO locationking;\""
echo "  sudo -u postgres psql -d location_king -c \"CREATE EXTENSION IF NOT EXISTS postgis;\""
echo ""
echo "Затем запустите:"
echo "  cd /home/ilya/location_king/backend"
echo "  python3 apply_migrations.py"