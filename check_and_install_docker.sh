#!/bin/bash
# Скрипт для проверки и установки Docker

echo "🔧 Проверка и установка Docker"
echo "=============================="

# Проверка Docker
if command -v docker &> /dev/null; then
    echo "✅ Docker установлен: $(docker --version)"
else
    echo "❌ Docker не установлен"
    echo ""
    echo "Установка Docker..."
    
    # Для Ubuntu/Debian
    if command -v apt-get &> /dev/null; then
        echo "Обнаружена система на основе Debian"
        sudo apt-get update
        sudo apt-get install -y docker.io docker-compose
        sudo systemctl start docker
        sudo systemctl enable docker
    # Для CentOS/RHEL
    elif command -v yum &> /dev/null; then
        echo "Обнаружена система на основе RHEL"
        sudo yum install -y docker docker-compose
        sudo systemctl start docker
        sudo systemctl enable docker
    else
        echo "❌ Неизвестная система. Установите Docker вручную:"
        echo "   https://docs.docker.com/engine/install/"
        exit 1
    fi
    
    echo "✅ Docker установлен"
fi

# Проверка Docker Compose
if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose установлен: $(docker-compose --version)"
else
    echo "⚠️  Docker Compose не установлен"
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y docker-compose
    elif command -v yum &> /dev/null; then
        sudo yum install -y docker-compose
    fi
    echo "✅ Docker Compose установлен"
fi

# Добавление пользователя в группу docker
if ! groups $USER | grep -q '\bdocker\b'; then
    echo "👤 Добавляю пользователя $USER в группу docker..."
    sudo usermod -aG docker $USER
    echo "⚠️  Необходимо выйти и зайти снова для применения изменений"
    echo "   Или выполните: newgrp docker"
fi

echo ""
echo "🔍 Проверка работы Docker..."
if sudo docker run --rm hello-world | grep -q "Hello from Docker"; then
    echo "✅ Docker работает корректно"
else
    echo "❌ Проблема с Docker"
    exit 1
fi

echo ""
echo "🎉 Docker готов к использованию!"
echo ""
echo "Для запуска Location King выполните:"
echo "  ./start_services.sh"