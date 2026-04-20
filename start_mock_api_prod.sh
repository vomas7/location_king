#!/bin/bash
# Запуск mock API для production

cd /home/ilya/location_king

# Останавливаем старый процесс если есть
pkill -f "run_mock_api:app" 2>/dev/null

# Запускаем на порту 8001
echo "🚀 Запуск Location King Mock API на порту 8001..."
python3 -m uvicorn run_mock_api:app --host 0.0.0.0 --port 8001 --reload > /tmp/locationking_mock_api.log 2>&1 &

echo "✅ Mock API запущен на http://localhost:8001"
echo "📋 Логи: /tmp/locationking_mock_api.log"
echo ""
echo "Для проверки:"
echo "  curl http://localhost:8001/"
echo "  curl -X POST http://localhost:8001/api/mock/sessions/start -H 'Content-Type: application/json' -d '{\"rounds_total\": 3}'"