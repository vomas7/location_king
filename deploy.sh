#!/usr/bin/env bash
# Развернуть Location King одной командой: собрать образы, поднять контур,
# накатить миграции и загрузить игровые зоны.
#
# Первый запуск на чистом сервере сам создаёт .env со сгенерированными
# паролями. Дальше достаточно git pull && ./deploy.sh.
#
# Значения, которые неудобно вписывать руками, можно передать окружением —
# они попадут в .env при его создании:
#
#     SITE_URL=https://example.com OPERATOR_NAME="Имя" \
#         OPERATOR_EMAIL=mail@example.com ./deploy.sh
#
# Подробности — в docs/deployment.md.

set -euo pipefail

cd "$(dirname "$0")"

readonly HEALTH_TIMEOUT_SECONDS=180
readonly SECRET_VARS=(POSTGRES_PASSWORD REDIS_PASSWORD JWT_SECRET)

# Переменные, которые при создании .env можно передать окружением
readonly ENV_OVERRIDES=(SITE_URL OPERATOR_NAME OPERATOR_EMAIL)


readonly CLOUDFLARE_IPS_V4=https://www.cloudflare.com/ips-v4
readonly CLOUDFLARE_IPS_V6=https://www.cloudflare.com/ips-v6
readonly CLOUDFLARE_ORIGIN_PULL_CA=https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem
readonly REAL_IP_SNIPPET=nginx/snippets/cloudflare-real-ip.conf
readonly ORIGIN_PULL_SNIPPET=nginx/snippets/cloudflare-origin-pull.conf

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

# Значение переменной в .env: заменяем строку целиком или дописываем в конец.
# Значение передаём окружением, а не -v: awk разбирает в -v escape-последо-
# вательности, и обратный слэш в имени оператора превратился бы в мусор.
set_env_value() {
    local name="$1"

    name="$name" value="$2" awk '
        $0 ~ "^" ENVIRON["name"] "=" && !done {
            print ENVIRON["name"] "=" ENVIRON["value"]
            done = 1
            next
        }
        { print }
        END { if (!done) print ENVIRON["name"] "=" ENVIRON["value"] }
    ' .env > .env.new

    mv .env.new .env
    chmod 600 .env
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

    # Значения из окружения: так первый запуск обходится без правки .env
    # редактором — это заметно проще, когда сервер настраивают с телефона
    for name in "${ENV_OVERRIDES[@]}"; do
        value="${!name-}"
        [ -n "$value" ] || continue
        set_env_value "$name" "$value"
        echo "${name} взят из окружения."
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

# Не смертельно, но документы без реквизитов оператора бесполезны: игроку
# некуда обратиться по поводу своих данных
if [ -z "$(env_value OPERATOR_NAME)" ] || [ -z "$(env_value OPERATOR_EMAIL)" ]; then
    echo "Внимание: в .env не заполнены OPERATOR_NAME и OPERATOR_EMAIL." >&2
    echo "Условия использования и политика покажут, что реквизиты не указаны." >&2
fi

# ─── Контур TLS ───────────────────────────────────────────────────────
# Список сетей Cloudflare меняется, поэтому он не лежит в репозитории, а
# собирается при каждом развёртывании. Устаревший список опаснее отсутствующего:
# с ним nginx поверил бы заголовку CF-Connecting-IP не от Cloudflare.
write_cloudflare_real_ip() {
    local v4 v6

    v4="$(curl --fail --silent --show-error --max-time 20 "$CLOUDFLARE_IPS_V4" || true)"
    v6="$(curl --fail --silent --show-error --max-time 20 "$CLOUDFLARE_IPS_V6" || true)"

    if [ -z "$v4" ]; then
        [ -s "$REAL_IP_SNIPPET" ] ||
            die "не удалось получить список сетей Cloudflare с ${CLOUDFLARE_IPS_V4}"
        echo "Список сетей Cloudflare недоступен, оставляю прежний."
        return
    fi

    {
        echo "# Собран deploy.sh $(date -u '+%Y-%m-%d %H:%M UTC') из ${CLOUDFLARE_IPS_V4}"
        echo "# Правки в этом файле затрутся при следующем развёртывании."
        # Разбиение по строкам здесь и нужно: в ответе список сетей
        # shellcheck disable=SC2086
        printf 'set_real_ip_from %s;\n' $v4 $v6
        echo "real_ip_header CF-Connecting-IP;"
    } > "$REAL_IP_SNIPPET"

    echo "Сетей Cloudflare в списке: $(grep -c set_real_ip_from "$REAL_IP_SNIPPET")"
}

write_cloudflare_origin_pull() {
    if [ ! -s ssl/cloudflare-origin-pull-ca.pem ]; then
        curl --fail --silent --show-error --max-time 20 \
            --output ssl/cloudflare-origin-pull-ca.pem "$CLOUDFLARE_ORIGIN_PULL_CA" || true
    fi

    if [ -s ssl/cloudflare-origin-pull-ca.pem ]; then
        {
            echo "# Authenticated Origin Pulls включены: origin отвечает только Cloudflare."
            echo "ssl_client_certificate /etc/nginx/ssl/cloudflare-origin-pull-ca.pem;"
            echo "ssl_verify_client on;"
        } > "$ORIGIN_PULL_SNIPPET"
        echo "Authenticated Origin Pulls: включены."
    else
        {
            echo "# Authenticated Origin Pulls выключены: нет ssl/cloudflare-origin-pull-ca.pem."
            echo "# Без них origin доступен любому, кто узнает его адрес в обход Cloudflare."
        } > "$ORIGIN_PULL_SNIPPET"
        echo "Authenticated Origin Pulls: выключены — сертификат Cloudflare не найден." >&2
    fi
}

profile="$(env_value NGINX_PROFILE)"
[ -n "$profile" ] || profile=http

case "$profile" in
    tls)
        [ -s ssl/fullchain.pem ] && [ -s ssl/privkey.pem ] ||
            die "профиль tls требует ssl/fullchain.pem и ssl/privkey.pem"
        ;;
    cloudflare)
        step "Готовлю контур Cloudflare"

        command -v curl > /dev/null 2>&1 ||
            die "для контура cloudflare нужен curl: он забирает список сетей Cloudflare"

        mkdir -p ssl
        [ -s ssl/origin.pem ] && [ -s ssl/origin.key ] || die "$(
            printf '%s\n' \
                "профиль cloudflare требует ssl/origin.pem и ssl/origin.key." \
                "Origin-сертификат берётся в панели Cloudflare:" \
                "SSL/TLS → Origin Server → Create Certificate."
        )"

        write_cloudflare_real_ip
        write_cloudflare_origin_pull
        ;;
esac

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

site="$(env_value SITE_URL)"

if [ "$profile" = "http" ]; then
    if command -v curl > /dev/null 2>&1; then
        curl --fail --silent --show-error http://localhost/api/health && echo
    else
        echo "curl не установлен, проверьте вручную: http://localhost/api/health"
    fi
else
    # Контуры с TLS отвечают по HTTPS, а за Cloudflare origin вдобавок требует
    # клиентский сертификат — запросом с самого сервера это не проверить.
    # Остаётся убедиться, что nginx принял конфигурацию, а игру открыть снаружи.
    docker compose exec -T nginx nginx -t > /dev/null 2>&1 ||
        die "nginx поднялся с нерабочей конфигурацией, смотрите docker compose logs nginx"

    echo "Бэкенд здоров, nginx принял конфигурацию контура ${profile}."
    echo "Откройте снаружи: ${site:-https://<ваш домен>}/api/health"
fi

echo
echo "Готово. Логи: docker compose logs -f   Остановить: docker compose down"
