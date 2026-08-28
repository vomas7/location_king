#!/usr/bin/env bash
# Первичная настройка чистого сервера под Location King.
#
# Ставит Docker, если его нет, забирает репозиторий и передаёт дело deploy.sh.
# Рассчитан на Ubuntu Server 24.04 LTS; на любом другом дистрибутиве с apt
# отработает так же, на остальных Docker придётся поставить руками.
# Рассчитан на то, что его запускают с телефона: команд минимум, а всё, что
# скрипт не может решить сам, он объясняет и печатает готовой строкой.
#
#     curl -fsSL https://raw.githubusercontent.com/vomas7/location_king/main/server-setup.sh | sudo bash
#
# По умолчанию сайт получает сертификат Let's Encrypt, и от человека не нужно
# ничего, кроме записей DNS на этот сервер. Реквизиты оператора для правовых
# документов можно передать той же строкой — они уйдут в .env при первом
# запуске:
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

# Скрипт запускают через pipe, поэтому на его stdin лежит он сам: любой
# интерактивный вопрос apt прочитал бы оттуда мусор и завис. Заодно снимаем
# диалог перезапуска служб — в Ubuntu 24.04 он появляется по умолчанию.
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

# Сразу после первой загрузки apt занят автообновлением. Ждём его, а не падаем
apt_install() {
    apt-get -o DPkg::Lock::Timeout=300 update -qq
    apt-get -o DPkg::Lock::Timeout=300 install -y -qq "$@"
}

# ─── Docker ───────────────────────────────────────────────────────────
if docker compose version > /dev/null 2>&1; then
    echo "Docker уже стоит."
else
    step "Ставлю Docker"

    command -v curl > /dev/null 2>&1 || apt_install curl

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
    command -v git > /dev/null 2>&1 || apt_install git
    git clone --depth 1 "$REPO" "$TARGET"
fi

cd "$TARGET"

# ─── Сертификат Cloudflare ────────────────────────────────────────────
# Нужен только контуру cloudflare. По умолчанию сертификат выпускает Let's
# Encrypt, и тогда вмешательства не требуется вовсе.
if [ -f .env ]; then
    profile="$(sed -n 's/^[[:space:]]*NGINX_PROFILE=//p' .env | tail -n 1)"
else
    profile="${NGINX_PROFILE-}"
fi
[ -n "${profile:-}" ] || profile="$(sed -n 's/^[[:space:]]*NGINX_PROFILE=//p' .env.example | tail -n 1)"

mkdir -p ssl
chmod 700 ssl

if [ "$profile" = "cloudflare" ] && { [ ! -s ssl/origin.pem ] || [ ! -s ssl/origin.key ]; }; then
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

[ -s ssl/origin.key ] && chmod 600 ssl/origin.key

# ─── Развёртывание ────────────────────────────────────────────────────
step "Разворачиваю"
exec ./deploy.sh
