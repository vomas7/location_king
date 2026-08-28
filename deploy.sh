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
# Секреты, без которых приложение не должно стартовать
readonly SECRET_VARS=(POSTGRES_PASSWORD REDIS_PASSWORD JWT_SECRET)

# Пароль Grafana генерируется так же, но требуется только мониторингу
readonly GRAFANA_PASSWORD_VAR=GRAFANA_ADMIN_PASSWORD

readonly MONITORING_SNIPPET=nginx/snippets/monitoring-host.conf

# Переменные, которые при создании .env можно передать окружением
readonly ENV_OVERRIDES=(
    SITE_URL OPERATOR_NAME OPERATOR_EMAIL NGINX_PROFILE SSL_EMAIL SSL_EXTRA_DOMAINS
    MONITORING MONITORING_DOMAIN
)


# Каталог сертификата фиксирован ключом --cert-name: путь в конфигурации
# nginx тогда не зависит от домена
readonly LETSENCRYPT_NAME=main
readonly LETSENCRYPT_LIVE=certbot/conf/live/main
readonly ACME_HELPER=location_king_acme

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

# Значения, переданные окружением, сильнее записанных в .env: так и первый
# запуск обходится без редактора, и потом можно поменять контур или домен той
# же командой. Это заметно проще, когда сервером управляют с телефона.
for name in "${ENV_OVERRIDES[@]}"; do
    value="${!name-}"
    [ -n "$value" ] || continue
    [ "$value" != "$(env_value "$name")" ] || continue

    set_env_value "$name" "$value"
    echo "${name} взят из окружения: ${value}"
done

for name in "${SECRET_VARS[@]}"; do
    [ -n "$(env_value "$name")" ] || die "в .env не заполнена переменная ${name}"
done

# Пароль Grafana дописывается и в уже существующий .env: без него docker
# compose не разберёт файл описания, даже когда мониторинг выключен
if [ -z "$(env_value "$GRAFANA_PASSWORD_VAR")" ]; then
    set_env_value "$GRAFANA_PASSWORD_VAR" "$(random_secret)"
    echo "Пароль администратора Grafana сгенерирован, он в .env."
fi

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

# Домен из SITE_URL: схема и путь тут не нужны, сертификат выпускается на имя
site_domain() {
    local site
    site="$(env_value SITE_URL)"
    site="${site#*://}"
    printf '%s' "${site%%/*}"
}

# Первый сертификат. Дальше его продлевает контейнер certbot — тем же способом
# проверки, поэтому и здесь webroot, а не standalone: иначе продление стало бы
# отличаться от выпуска и однажды отвалилось бы молча.
issue_certificate() {
    local domain="$1" email="$2" extra code
    local domains=("$domain") names=()

    # Разбиение по словам здесь и нужно: в переменной список доменов
    for extra in $(env_value SSL_EXTRA_DOMAINS | tr ',' ' '); do
        domains+=("$extra")
    done

    # Панель мониторинга живёт на своём поддомене и тоже нуждается в
    # сертификате: отдельно его выпускать незачем, имя добавляется в общий
    monitoring_enabled && domains+=("$(monitoring_domain)")

    for extra in "${domains[@]}"; do
        # Повтор имени certbot считает ошибкой, а попасть в список дважды оно
        # может легко: и через SSL_EXTRA_DOMAINS, и как домен панели
        case " ${names[*]} " in
            *" $extra "*) continue ;;
        esac
        names+=(-d "$extra")
    done

    echo "Выпускаю сертификат: ${domains[*]}"

    # Проверку Let's Encrypt присылает на 80-й порт, и его слушает nginx
    # контура. Настоящий nginx на это время не годится: без сертификата он не
    # стартует вовсе, поэтому порт занимает сервер, умеющий ровно одно —
    # отдать файл проверки
    docker compose stop nginx > /dev/null 2>&1 || true
    trap 'docker rm -f "$ACME_HELPER" > /dev/null 2>&1 || true' EXIT
    docker rm -f "$ACME_HELPER" > /dev/null 2>&1 || true

    docker run --rm --detach --name "$ACME_HELPER" --publish 80:80 \
        --volume "$PWD/certbot/www:/usr/share/nginx/html:ro" \
        nginx:alpine > /dev/null ||
        die "не удалось занять 80-й порт для проверки домена"

    code=0
    docker run --rm \
        --volume "$PWD/certbot/conf:/etc/letsencrypt" \
        --volume "$PWD/certbot/www:/var/www/certbot" \
        certbot/certbot certonly \
        --webroot --webroot-path /var/www/certbot \
        --cert-name "$LETSENCRYPT_NAME" "${names[@]}" \
        --email "$email" --agree-tos --no-eff-email --non-interactive || code=$?

    docker rm -f "$ACME_HELPER" > /dev/null 2>&1 || true
    trap - EXIT

    [ "$code" = "0" ] || die "$(
        printf '%s\n' \
            "Let's Encrypt не выдал сертификат." \
            "Проверьте, что домены указывают на этот сервер — в Cloudflare это" \
            "серое облачко, DNS only, — и что 80-й порт открыт снаружи." \
            "Домена, которого нет в DNS, в списке быть не должно: проверка не" \
            "пройдёт целиком. Это касается и поддомена панели мониторинга —" \
            "либо заведите ему запись, либо поставьте MONITORING=false."
    )"
}

# Узел Grafana. Имя домена в конфигурацию nginx подставить переменной нельзя,
# поэтому server-блок собирается здесь — под контур и под настоящее имя.
write_monitoring_host() {
    local domain="$1" tls_lines=""

    case "$profile" in
        letsencrypt)
            tls_lines="$(
                printf '%s\n' \
                    "    listen 443 ssl;" \
                    "    http2 on;" \
                    "" \
                    "    ssl_certificate /etc/letsencrypt/live/main/fullchain.pem;" \
                    "    ssl_certificate_key /etc/letsencrypt/live/main/privkey.pem;"
            )"
            ;;
        cloudflare)
            tls_lines="$(
                printf '%s\n' \
                    "    listen 443 ssl;" \
                    "    http2 on;" \
                    "" \
                    "    ssl_certificate /etc/nginx/ssl/origin.pem;" \
                    "    ssl_certificate_key /etc/nginx/ssl/origin.key;" \
                    "" \
                    "    include /etc/nginx/snippets/cloudflare-real-ip.conf;" \
                    "    include /etc/nginx/snippets/cloudflare-origin-pull.conf;"
            )"
            ;;
        tls)
            tls_lines="$(
                printf '%s\n' \
                    "    listen 443 ssl;" \
                    "    http2 on;" \
                    "" \
                    "    ssl_certificate /etc/nginx/ssl/fullchain.pem;" \
                    "    ssl_certificate_key /etc/nginx/ssl/privkey.pem;"
            )"
            ;;
        *)
            # Контур http: шифрование терминирует кто-то перед нами
            tls_lines="    listen 80;"
            ;;
    esac

    {
        echo "# Собран deploy.sh $(date -u '+%Y-%m-%d %H:%M UTC') под контур ${profile}."
        echo "# Правки в этом файле затрутся при следующем развёртывании."
        echo
        echo "server {"
        echo "$tls_lines"
        echo
        echo "    server_name ${domain};"
        echo
        echo "    include /etc/nginx/snippets/monitoring-proxy.conf;"
        echo "}"
    } > "$MONITORING_SNIPPET"
}

# Мониторинг включён? Значение по умолчанию берём из .env.example, чтобы
# правда о настройках по умолчанию лежала в одном месте
monitoring_enabled() {
    [ "$(env_value MONITORING)" != "false" ]
}

# Домен панели. Пусто — собирается из домена сайта
monitoring_domain() {
    local configured
    configured="$(env_value MONITORING_DOMAIN)"

    if [ -n "$configured" ]; then
        printf '%s' "$configured"
    else
        printf 'grafana.%s' "$(site_domain)"
    fi
}

profile="$(env_value NGINX_PROFILE)"
[ -n "$profile" ] || profile=http

# Профили docker compose: ими включаются необязательные службы
compose_profiles=()
monitoring_enabled && compose_profiles+=(monitoring)

case "$profile" in
    tls)
        [ -s ssl/fullchain.pem ] && [ -s ssl/privkey.pem ] ||
            die "профиль tls требует ssl/fullchain.pem и ssl/privkey.pem"
        ;;
    letsencrypt)
        step "Готовлю сертификат Let's Encrypt"

        domain="$(site_domain)"
        [ -n "$domain" ] ||
            die "профиль letsencrypt требует SITE_URL в .env: из него берётся домен сертификата"

        # Адрес нужен Let's Encrypt, чтобы предупредить об истечении, если
        # продление вдруг перестанет проходить
        email="$(env_value SSL_EMAIL)"
        [ -n "$email" ] || email="$(env_value OPERATOR_EMAIL)"
        [ -n "$email" ] ||
            die "профиль letsencrypt требует SSL_EMAIL или OPERATOR_EMAIL в .env"

        mkdir -p certbot/conf certbot/www

        if [ -s "$LETSENCRYPT_LIVE/fullchain.pem" ]; then
            echo "Сертификат уже выпущен, продлевает его контейнер certbot."
        else
            issue_certificate "$domain" "$email"
        fi

        # Контейнер продления объявлен с profiles: без этого он не поднимется
        compose_profiles+=(letsencrypt)
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

# ─── Наблюдаемость ────────────────────────────────────────────────────
if monitoring_enabled; then
    step "Готовлю мониторинг"

    monitoring_host="$(monitoring_domain)"
    [ -n "$monitoring_host" ] ||
        die "мониторинг включён, но домен панели неоткуда взять: заполните MONITORING_DOMAIN"

    write_monitoring_host "$monitoring_host"

    # Записываем разобранные значения обратно: docker compose читает .env, а
    # не эти функции, и Grafana должна знать свой публичный адрес
    set_env_value MONITORING_DOMAIN "$monitoring_host"
    if [ "$profile" = "http" ]; then
        set_env_value MONITORING_URL "http://${monitoring_host}"
    else
        set_env_value MONITORING_URL "https://${monitoring_host}"
    fi

    echo "Панель будет доступна на ${monitoring_host}."
else
    # Файла нет — nginx подключает узел по маске и не спотыкается об это
    rm -f "$MONITORING_SNIPPET"
    echo "Мониторинг выключен: MONITORING=false."
fi

# Список профилей compose собирается один раз: пустая переменная означала бы,
# что необязательные службы не поднимутся вовсе
if [ "${#compose_profiles[@]}" -gt 0 ]; then
    COMPOSE_PROFILES="$(
        IFS=,
        echo "${compose_profiles[*]}"
    )"
    export COMPOSE_PROFILES
fi

# ─── Сборка и запуск ──────────────────────────────────────────────────
# Коммит уходит в сборку и дальше в /version.json. Иначе снаружи не отличить
# работающее автоматическое развёртывание от молчащего
GIT_SHA="$(git rev-parse HEAD 2> /dev/null || echo unknown)"
export GIT_SHA

step "Собираю образы и поднимаю контур (${GIT_SHA:0:12})"
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

# Границы качаются из сети и весят двадцать мегабайт, поэтому только один раз.
# Не скачались — режим стран просто не включится, остальная игра работает
step "Загружаю границы стран"
docker compose exec -T backend python scripts/load_countries.py --only-new ||
    echo "  ! границы не загрузились: режим «угадай страну» будет недоступен"

# ─── Проверка ─────────────────────────────────────────────────────────
step "Проверяю, что игра отвечает"

site="$(env_value SITE_URL)"

if [ "$profile" = "http" ]; then
    if command -v curl > /dev/null 2>&1; then
        curl --fail --silent --show-error http://localhost/api/health && echo
    else
        echo "curl не установлен, проверьте вручную: http://localhost/api/health"
    fi
elif [ "$profile" = "letsencrypt" ]; then
    docker compose exec -T nginx nginx -t > /dev/null 2>&1 ||
        die "nginx поднялся с нерабочей конфигурацией, смотрите docker compose logs nginx"

    # Настоящая проверка: сертификат признаётся, HTTPS отвечает. Запрос идёт с
    # самого сервера, а он не на всяком хостинге может достучаться до своего же
    # внешнего адреса, — поэтому неудача здесь не приговор
    if curl --fail --silent --show-error --max-time 15 "https://${domain}/api/health"; then
        echo
        echo "Сертификат принят, игра отвечает по HTTPS."
    else
        echo "С самого сервера достучаться до https://${domain} не вышло." >&2
        echo "Так бывает из-за NAT: откройте адрес с другого устройства." >&2
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

if monitoring_enabled; then
    echo
    echo "Мониторинг: $(env_value MONITORING_URL)"
    grafana_user="$(env_value GRAFANA_ADMIN_USER)"
    echo "Вход — ${grafana_user:-admin}, пароль в .env (GRAFANA_ADMIN_PASSWORD)."
fi

echo
echo "Готово. Логи: docker compose logs -f   Остановить: docker compose down"
