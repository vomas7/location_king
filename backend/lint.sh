#!/bin/bash
# Скрипт для линтинга кода с ruff

set -e

echo "🔍 Запускаю ruff lint..."
ruff check app/

echo "🎨 Запускаю ruff format (проверка)..."
ruff format --check app/

echo "✅ Линтинг завершён успешно!"