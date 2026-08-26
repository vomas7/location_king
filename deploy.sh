#!/bin/bash
# Деплой Location King. Подробности — в docs/deployment.md.

set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "Нет файла .env. Создайте его: cp .env.example .env" >&2
    exit 1
fi

if ! docker compose version > /dev/null 2>&1; then
    echo "Нужен docker compose: https://docs.docker.com/engine/install/" >&2
    exit 1
fi

echo "Собираю и поднимаю контейнеры…"
docker compose up -d --build

echo "Жду, пока бэкенд станет здоровым…"
for _ in $(seq 1 30); do
    if [ "$(docker compose ps -q backend | xargs docker inspect -f '{{.State.Health.Status}}')" = "healthy" ]; then
        break
    fi
    sleep 2
done

echo "Накатываю миграции…"
docker compose exec -T backend alembic upgrade head

echo "Загружаю игровые зоны…"
docker compose exec -T backend python scripts/seed.py

echo
echo "Готово. Проверка: curl http://localhost/api/health"
echo "Логи: docker compose logs -f   Остановить: docker compose down"
