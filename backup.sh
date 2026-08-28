#!/usr/bin/env bash
# Резервная копия базы.
#
# Запускается по таймеру systemd раз в сутки, но и руками работает:
#
#     ./backup.sh              снять копию
#     ./backup.sh --check      снять и проверить, что она разворачивается
#
# Копия, которую никто ни разу не разворачивал, — это не копия, а надежда.
# Поэтому проверка встроена и таймер вызывает скрипт именно с ней.

set -euo pipefail

cd "$(dirname "$0")"

readonly DIR=backups
readonly KEEP_DAYS=7

die() {
    echo "Ошибка: $*" >&2
    exit 1
}

env_value() {
    sed -n "s/^[[:space:]]*$1=//p" .env | tail -n 1
}

[ -f .env ] || die "нет .env — разворачивать нечего"

user="$(env_value POSTGRES_USER)"
database="$(env_value POSTGRES_DB)"
[ -n "$user" ] && [ -n "$database" ] || die "в .env нет POSTGRES_USER или POSTGRES_DB"

mkdir -p "$DIR"
chmod 700 "$DIR"

stamp="$(date -u '+%Y-%m-%d-%H%M')"
target="$DIR/location_king-$stamp.sql.gz"

echo "Снимаю копию в $target"

# Через временный файл: оборванный дамп не должен занять место готового и
# однажды оказаться единственным, что осталось
docker compose exec -T postgres pg_dump --clean --if-exists -U "$user" "$database" \
    | gzip > "$target.part"
mv "$target.part" "$target"

# gzip проверяет собственную контрольную сумму — обрезанный файл он поймает
gzip --test "$target" || die "копия $target повреждена"

size="$(du -h "$target" | cut -f1)"
echo "Готово: $target ($size)"

# ─── Проверка разворачиванием ─────────────────────────────────────────
if [ "${1:-}" = "--check" ]; then
    echo "Проверяю, что копия разворачивается"

    probe="restore_check_$stamp"
    cleanup() {
        docker compose exec -T postgres psql -U "$user" -d postgres \
            -c "DROP DATABASE IF EXISTS \"$probe\"" > /dev/null 2>&1 || true
    }
    trap cleanup EXIT

    docker compose exec -T postgres psql -U "$user" -d postgres \
        -c "CREATE DATABASE \"$probe\"" > /dev/null

    if ! gzip -dc "$target" | docker compose exec -T postgres \
        psql --quiet --set ON_ERROR_STOP=1 -U "$user" -d "$probe" > /dev/null; then
        die "копия $target не разворачивается — она бесполезна"
    fi

    players="$(
        docker compose exec -T postgres psql -tAc "SELECT count(*) FROM users" \
            -U "$user" -d "$probe"
    )"
    echo "Копия разворачивается, игроков в ней: ${players//[[:space:]]/}"
fi

# ─── Уборка старых ────────────────────────────────────────────────────
removed="$(find "$DIR" -name 'location_king-*.sql.gz' -mtime "+$KEEP_DAYS" -print -delete | wc -l)"
[ "$removed" = "0" ] || echo "Удалено копий старше ${KEEP_DAYS} дней: $removed"

echo "Копий на диске: $(find "$DIR" -name 'location_king-*.sql.gz' | wc -l)"
