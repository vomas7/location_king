#!/bin/bash
echo "🧹 Запуск ruff для линтинга и форматирования кода"
echo "=================================================="

# Устанавливаем ruff если не установлен
if ! command -v ruff &> /dev/null; then
    echo "Установка ruff..."
    pip install ruff==0.9.4
fi

# Переходим в директорию с Python кодом
cd backend

echo ""
echo "1. Проверка стиля кода..."
ruff check .

echo ""
echo "2. Форматирование кода..."
ruff format .

echo ""
echo "3. Автоисправление проблем..."
ruff check --fix .

echo ""
echo "4. Проверка импортов..."
ruff check --select I .

echo ""
echo "=================================================="
echo "✅ Линтинг и форматирование завершены!"
echo ""
echo "Команды для ручного запуска:"
echo "  ruff check .          # Проверка кода"
echo "  ruff format .         # Форматирование кода"
echo "  ruff check --fix .    # Автоисправление"
echo "  ruff check --select I .  # Проверка импортов"