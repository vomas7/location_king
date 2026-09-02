#!/usr/bin/env bash
# Автоматическое развёртывание: следит за веткой deploy и катит её на сервер.
#
# Ветку двигает CI, и только после зелёных проверок, — значит, всё, что здесь
# появилось, уже проверено. Запускается по таймеру systemd раз в две минуты:
#
#     systemctl status location-king-deploy.timer
#     journalctl -u location-king-deploy -f
#
# Развёртывание не удалось — возвращаемся на предыдущую версию и оставляем
# сервер работающим. Молча падать здесь нельзя: игра останется лежать.

set -euo pipefail

# Скрипт переписывает сам себя, когда приезжает новая версия, а bash дочитывает
# файл по ходу выполнения. Поэтому работаем из копии: иначе на середине
# обновления интерпретатор прочитал бы обрывок нового текста.
if [ "${AUTODEPLOY_FROM_COPY:-}" != "1" ]; then
    copy="$(mktemp /tmp/autodeploy.XXXXXX.sh)"
    cat "$0" > "$copy"
    chmod +x "$copy"

    cd "$(dirname "$0")"
    AUTODEPLOY_FROM_COPY=1 AUTODEPLOY_ROOT="$PWD" exec "$copy" "$@"
fi

trap 'rm -f "$0"' EXIT
cd "${AUTODEPLOY_ROOT:?}"

readonly BRANCH=deploy
readonly LOCK=/var/lock/location-king-deploy.lock

log() {
    echo "[autodeploy] $*"
}

# Ручной запуск не должен наложиться на запуск по таймеру: два развёртывания
# одновременно перетопчут друг другу контейнеры
exec 9> "$LOCK"
if ! flock --nonblock 9; then
    log "развёртывание уже идёт, пропускаю"
    exit 0
fi

# Ветки может не быть вовсе — на новом сервере, пока CI не собрал первую
# зелёную версию. Это не ошибка, а нормальное начало жизни
if ! git ls-remote --exit-code --heads --quiet origin "$BRANCH" > /dev/null; then
    log "ветки origin/${BRANCH} ещё нет: CI создаст её после первых зелёных проверок"
    exit 0
fi

# Ветка забирается поимённо, а не общим fetch: репозиторий на сервере мог
# быть склонирован одной веткой (git clone --single-branch), и тогда правило
# выборки тянет только main. Общий fetch в таком репозитории отрабатывает
# успешно и молча — а origin/deploy не появляется никогда, и развёртывание
# останавливается, повторяя «ветки ещё нет» при живой ветке на GitHub
git fetch --prune --quiet origin "+refs/heads/${BRANCH}:refs/remotes/origin/${BRANCH}"

if ! target="$(git rev-parse --verify --quiet "origin/$BRANCH")"; then
    log "ветка origin/${BRANCH} есть на GitHub, но не забралась — смотрите настройку remote.origin.fetch"
    exit 1
fi

current="$(git rev-parse HEAD)"

if [ "$target" = "$current" ]; then
    exit 0
fi

log "новая версия ${target:0:12} (сейчас ${current:0:12})"

# Отдельной функцией, чтобы откат шёл ровно тем же путём, что и установка
deploy_revision() {
    git checkout --quiet -B "$BRANCH" "$1"
    ./deploy.sh
}

if deploy_revision "$target"; then
    log "развёрнуто: ${target:0:12}"
    exit 0
fi

log "версия ${target:0:12} не развернулась, возвращаю ${current:0:12}"

if deploy_revision "$current"; then
    log "откат прошёл: на сервере снова ${current:0:12}"
    exit 1
fi

log "откат тоже не прошёл — игра лежит, нужен человек"
exit 2
