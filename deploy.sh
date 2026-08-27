#!/usr/bin/env bash
# Развернуть Location King одной командой: собрать образы, поднять контур,
# накатить миграции и загрузить игровые зоны.
#
# Первый запуск на чистом сервере сам создаёт .env со сгенерированными
# паролями. Дальше достаточно git pull && ./deploy.sh.
#
# Подробности — в docs/deployment.md.

set -euo pipefail

cd "$(dirname "$0")"

readonly HEALTH_TIMEOUT_SECONDS=180
readonly SECRET_VARS=(POSTGRES_PASSWORD REDIS_PASSWORD JWT_SECRET)

die() {
    echo "Ошибка: $*" >&2
    exit 1
}

step() {
    echo
    echo "── $* ──"
}

random_secret() {
    if command -v openssl > /dev/null 2>&1; then
        openssl rand -hex 32
    else
        head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'
    fi
}

# ─── Проверки окружения ───────────────────────────────────────────────
docker compose version > /dev/null 2>&1 ||
    die "нужен docker compose: https://docs.docker.com/engine/install/"

docker info > /dev/null 2>&1 ||
    die "демон Docker не отвечает. Запустите его: systemctl start docker"

# ─── .env ─────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    step "Создаю .env"

    [ -f .env.example ] || die "нет ни .env, ни .env.example — репозиторий неполный"
    cp .env.example .env
    chmod 600 .env

    for name in "${SECRET_VARS[@]}"; do
        secret="$(random_secret)"
        # Заменяем только пустое значение: заполненное вручную не трогаем
        sed -i "s|^${name}=$|${name}=${secret}|" .env
    done

    echo "Пароли сгенерированы, файл доступен только владельцу."
    echo "Домен и провайдера снимков задайте в .env, если нужны не значения по умолчанию."
fi

# Файл читаем, а не исполняем: в нём есть значения с пробелами и запятыми,
# на которых source спотыкается, а выполнять чужой текст незачем
env_value() {
    local raw
    raw="$(sed -n "s/^[[:space:]]*$1=//p" .env | tail -n 1)"
    raw="${raw%\"}"
    raw="${raw#\"}"
    printf '%s' "$raw"
}

for name in "${SECRET_VARS[@]}"; do
    [ -n "$(env_value "$name")" ] || die "в .env не заполнена переменная ${name}"
done

if [ "$(env_value NGINX_PROFILE)" = "tls" ]; then
    [ -s ssl/fullchain.pem ] && [ -s ssl/privkey.pem ] ||
        die "профиль tls требует ssl/fullchain.pem и ssl/privkey.pem"
fi

# ─── Сборка и запуск ──────────────────────────────────────────────────
step "Собираю образы и поднимаю контур"
docker compose up -d --build

step "Жду, пока бэкенд станет здоровым"
container="$(docker compose ps -q backend)"
[ -n "$container" ] || die "контейнер backend не запустился, смотрите docker compose logs backend"

deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
until [ "$(docker inspect -f '{{.State.Health.Status}}' "$container")" = "healthy" ]; do
    if [ "$SECONDS" -ge "$deadline" ]; then
        docker compose logs --tail 50 backend >&2
        die "бэкенд не поднялся за ${HEALTH_TIMEOUT_SECONDS} с"
    fi
    sleep 2
done

# ─── Данные ───────────────────────────────────────────────────────────
step "Накатываю миграции"
docker compose exec -T backend alembic upgrade head

step "Загружаю игровые зоны"
docker compose exec -T backend python scripts/seed.py

# ─── Проверка ─────────────────────────────────────────────────────────
step "Проверяю, что игра отвечает"
if command -v curl > /dev/null 2>&1; then
    curl --fail --silent --show-error http://localhost/api/health && echo
else
    echo "curl не установлен, проверьте вручную: http://localhost/api/health"
fi

echo
echo "Готово. Логи: docker compose logs -f   Остановить: docker compose down"
