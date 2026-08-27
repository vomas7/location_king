#!/usr/bin/env bash
# Первичная настройка чистого сервера под Location King.
#
# Ставит Docker, если его нет, забирает репозиторий и передаёт дело deploy.sh.
# Рассчитан на то, что его запускают с телефона: команд минимум, а всё, что
# скрипт не может решить сам, он объясняет и печатает готовой строкой.
#
#     curl -fsSL https://raw.githubusercontent.com/vomas7/location_king/main/server-setup.sh | sudo bash
#
# Реквизиты оператора для правовых документов можно передать той же строкой —
# они уйдут в .env при первом запуске:
#
#     curl -fsSL .../server-setup.sh | sudo OPERATOR_NAME="Имя" \
#         OPERATOR_EMAIL=mail@example.com bash
#
# Запускать можно сколько угодно раз: повторный вызов обновляет код и
# перезапускает развёртывание.

set -euo pipefail

readonly REPO=https://github.com/vomas7/location_king.git
readonly TARGET=/opt/location_king

die() {
    echo
    echo "Ошибка: $*" >&2
    exit 1
}

step() {
    echo
    echo "── $* ──"
}

[ "$(id -u)" = "0" ] || die "запускать нужно от root: sudo bash вместо bash"

# ─── Docker ───────────────────────────────────────────────────────────
if docker compose version > /dev/null 2>&1; then
    echo "Docker уже стоит."
else
    step "Ставлю Docker"

    command -v curl > /dev/null 2>&1 || {
        apt-get update -qq
        apt-get install -y -qq curl
    }

    curl -fsSL https://get.docker.com | sh
    docker compose version > /dev/null 2>&1 ||
        die "Docker поставился, но плагин compose не работает. Смотрите https://docs.docker.com/engine/install/"
fi

# ─── Код ──────────────────────────────────────────────────────────────
if [ -d "$TARGET/.git" ]; then
    step "Обновляю код"
    git -C "$TARGET" pull --ff-only ||
        die "в $TARGET есть локальные правки, git pull не прошёл. Разберитесь с ними и запустите снова"
else
    step "Забираю код в $TARGET"
    command -v git > /dev/null 2>&1 || apt-get install -y -qq git
    git clone --depth 1 "$REPO" "$TARGET"
fi

cd "$TARGET"

# ─── Сертификат Cloudflare ────────────────────────────────────────────
mkdir -p ssl
chmod 700 ssl

if [ ! -s ssl/origin.pem ] || [ ! -s ssl/origin.key ]; then
    cat <<'HINT'

── Остался один шаг: origin-сертификат Cloudflare ──

Он выпускается в панели: SSL/TLS → Origin Server → Create Certificate.
Там же проверьте, что режим шифрования стоит Full (strict), а запись в DNS
идёт через Cloudflare — оранжевое облако.

Скопируйте из панели сертификат и ключ и вставьте на сервере двумя блоками.
Вставлять построчно, как напечатано: отступ перед закрывающим EOF оставит
ввод открытым.

Сначала сертификат:

cat > /opt/location_king/ssl/origin.pem <<'CERT'
...сюда вставить Origin Certificate целиком, вместе со строками BEGIN и END...
CERT

Потом закрытый ключ:

cat > /opt/location_king/ssl/origin.key <<'KEY'
...сюда вставить Private Key целиком, вместе со строками BEGIN и END...
KEY

И запустите эту же команду ещё раз — дальше всё пойдёт само.

HINT
    exit 0
fi

chmod 600 ssl/origin.key

# ─── Развёртывание ────────────────────────────────────────────────────
step "Разворачиваю"
exec ./deploy.sh
