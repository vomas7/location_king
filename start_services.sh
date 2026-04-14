#!/bin/bash
# Скрипт для запуска сервисов Location King

set -e

echo "🦁 Запуск Location King сервисов"
echo "================================"

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "❌ .env файл не найден!"
    echo "Создайте .env файл из .env.example:"
    echo "  cp .env.example .env"
    echo "И отредактируйте его"
    exit 1
fi

echo "✅ .env файл найден"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен"
    exit 1
fi

echo "✅ Docker и Docker Compose готовы"

# Остановка предыдущих сервисов
echo "🛑 Останавливаю предыдущие сервисы..."
docker-compose -f docker-compose.simple.yml down 2>/dev/null || true

# Создание папки для SSL (пока пустая)
echo "🔐 Подготавливаю SSL папку..."
mkdir -p ssl

# Запуск сервисов
echo "🚀 Запускаю сервисы..."
docker-compose -f docker-compose.simple.yml up --build -d

echo "⏳ Ожидаю запуска сервисов..."
sleep 10

# Проверка запуска
echo "🔍 Проверяю запуск сервисов..."

check_service() {
    local service=$1
    local max_attempts=20
    local attempt=1
    
    echo -n "  $service... "
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.simple.yml ps $service | grep -q "Up"; then
            echo "✅"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo "❌"
    return 1
}

check_service "postgres"
check_service "redis"
check_service "keycloak"
check_service "backend"
check_service "nginx"

echo ""

# Применение миграций БД
echo "📊 Применяю миграции базы данных..."
docker-compose -f docker-compose.simple.yml exec backend python3 apply_migrations.py

# Инициализация тестовых данных
echo "📝 Инициализирую тестовые данные..."
docker-compose -f docker-compose.simple.yml exec backend python3 scripts/init_test_data.py
docker-compose -f docker-compose.simple.yml exec backend python3 scripts/add_more_zones.py

echo ""
echo "🎉 Сервисы успешно запущены!"
echo ""
echo "📋 Статус сервисов:"
docker-compose -f docker-compose.simple.yml ps
echo ""
echo "🌐 Доступные endpoints:"
echo "   Frontend:      http://localhost"
echo "   Backend API:   http://localhost:8000"
echo "   API Docs:      http://localhost:8000/api/docs"
echo "   Keycloak:      http://localhost:8080"
echo "   Keycloak Admin: http://localhost:8080/admin"
echo ""
echo "🔧 Для HTTPS (после настройки SSL):"
echo "   Frontend:      https://localhost"
echo "   Keycloak:      https://localhost/auth"
echo ""
echo "📝 Логи:"
echo "   docker-compose -f docker-compose.simple.yml logs -f"
echo ""
echo "🛑 Остановка:"
echo "   docker-compose -f docker-compose.simple.yml down"
echo ""
echo "✅ Location King готов к работе!"