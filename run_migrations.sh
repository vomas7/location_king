#!/bin/bash
# Скрипт для накатки миграций Location King

set -e

echo "🦁 Location King - Накатка миграций"
echo "===================================="

# Проверяем, где мы
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Рабочая директория: $(pwd)"
echo ""

# Вариант 1: Проверяем, установлен ли Docker
if command -v docker &> /dev/null; then
    echo "✅ Docker обнаружен"
    echo ""
    echo "Запускаем через Docker Compose..."
    
    if [ -f "docker-compose.yml" ]; then
        echo "1. Запускаем PostgreSQL..."
        docker-compose up -d postgres
        
        echo "2. Ждём запуска PostgreSQL..."
        sleep 5
        
        echo "3. Накатываем миграции..."
        docker-compose exec backend python3 apply_migrations.py
        
        echo "4. Инициализируем тестовые данные..."
        docker-compose exec backend python3 scripts/init_test_data.py
        
        echo "✅ Миграции успешно накатаны через Docker!"
        echo ""
        echo "Запустите приложение: docker-compose up --build"
    else
        echo "❌ Файл docker-compose.yml не найден"
    fi
    
    exit 0
fi

# Вариант 2: Проверяем, установлен ли PostgreSQL
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL обнаружен"
    echo ""
    
    # Проверяем, запущен ли сервер
    if pg_isready &> /dev/null; then
        echo "Сервер PostgreSQL запущен"
        
        # Проверяем, есть ли база данных
        if psql -U locationking -d location_king -c "SELECT 1;" &> /dev/null; then
            echo "База данных location_king существует"
        else
            echo "❌ База данных location_king не существует"
            echo ""
            echo "Создайте базу данных:"
            echo "  sudo -u postgres psql -c \"CREATE USER locationking WITH PASSWORD 'locationking123';\""
            echo "  sudo -u postgres psql -c \"CREATE DATABASE location_king;\""
            echo "  sudo -u postgres psql -d location_king -c \"GRANT ALL PRIVILEGES ON DATABASE location_king TO locationking;\""
            echo "  sudo -u postgres psql -d location_king -c \"CREATE EXTENSION IF NOT EXISTS postgis;\""
            exit 1
        fi
        
        # Переходим в backend
        cd backend
        
        # Проверяем Python зависимости
        echo "Проверяем Python зависимости..."
        if python3 -c "import fastapi, sqlalchemy, alembic, asyncpg, psycopg2" &> /dev/null; then
            echo "✅ Все зависимости установлены"
        else
            echo "❌ Не все зависимости установлены"
            echo "Установите: pip3 install -r requirements.txt"
            exit 1
        fi
        
        # Накатываем миграции
        echo "Накатываем миграции..."
        python3 apply_migrations.py
        
        echo "✅ Миграции успешно накатаны!"
        
    else
        echo "❌ Сервер PostgreSQL не запущен"
        echo "Запустите: sudo systemctl start postgresql"
        exit 1
    fi
    
    exit 0
fi

# Вариант 3: Ничего не установлено
echo "❌ Ни Docker, ни PostgreSQL не обнаружены"
echo ""
echo "Выберите вариант установки:"
echo ""
echo "1. Установить Docker (рекомендуется)"
echo "   sudo apt-get install docker.io docker-compose"
echo ""
echo "2. Установить PostgreSQL локально"
echo "   sudo apt-get install postgresql postgresql-contrib postgis"
echo ""
echo "3. Просмотреть SQL миграции без установки"
echo "   ./show_migration_sql.sh"
echo ""
echo "Затем запустите этот скрипт снова: ./run_migrations.sh"

exit 1