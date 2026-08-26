# Деплой

Прод-контур поднимается одним `docker compose` из корня репозитория. Образ
бэкенда собирается локально из `backend/Dockerfile.prod`, ничего никуда не
публикуется.

## Что требуется

- Linux-сервер с Docker и плагином Compose
  ([инструкция](https://docs.docker.com/engine/install/))
- DNS-запись на IP сервера
- Заполненный `.env` в корне репозитория

## Сервисы

| Сервис     | Образ                             | Сеть        | Назначение                        |
|------------|-----------------------------------|-------------|-----------------------------------|
| `nginx`    | `nginx:alpine`                    | edge        | статика фронтенда и прокси к API  |
| `backend`  | сборка `backend/Dockerfile.prod`  | edge + data | FastAPI                           |
| `postgres` | `postgis/postgis:16-3.4-alpine`   | data        | основная база                     |
| `redis`    | `redis:7-alpine`                  | data        | кэш спутниковых тайлов            |

Сеть `data` объявлена `internal: true`: база и кэш недоступны снаружи.
Бэкенд подключён и к `edge` — иначе он не смог бы забирать тайлы снимков.

Фронтенд и API отдаются с одного origin, поэтому CORS в прод-контуре не
используется вовсе.

## Порядок

1. Клонировать репозиторий на сервер.

2. Подготовить конфигурацию:

   ```bash
   cp .env.example .env
   $EDITOR .env
   ```

   Обязательные переменные: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`,
   `JWT_SECRET`. Секрет генерируется так:

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Без `JWT_SECRET` бэкенд не стартует — это сделано намеренно.

3. Выбрать контур TLS переменной `NGINX_PROFILE`:

   - `http` (по умолчанию) — сертификаты терминирует хостинг или
     балансировщик, nginx слушает только 80;
   - `tls` — сертификаты свои. Положите их в `./ssl` как `fullchain.pem` и
     `privkey.pem`; nginx поднимет 443, включит HSTS и будет редиректить с 80.

4. Запустить:

   ```bash
   ./deploy.sh
   ```

   Скрипт собирает образы, поднимает контейнеры, ждёт готовности бэкенда,
   накатывает миграции и загружает игровые зоны. То же вручную:

   ```bash
   docker compose up -d --build
   docker compose exec backend alembic upgrade head
   docker compose exec backend python scripts/seed.py
   ```

5. Проверить:

   ```bash
   curl http://<домен>/api/health
   ```

Полезные команды — в корневом `Makefile`: `make prod`, `make prod-down`.

## Обновление

```bash
git pull
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Миграции применяются только вперёд; уже применённые ревизии не редактируются.

## Заголовки безопасности

`nginx/snippets/site.conf` выставляет `X-Content-Type-Options`,
`X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` и
`Content-Security-Policy`; в контуре `tls` добавляется `Strict-Transport-Security`.

CSP строгая: страница не загружает ничего со сторонних доменов — OpenLayers
лежит в `frontend/vendor/`, шрифты системные. Единственное исключение —
`img-src` для тайлов OpenStreetMap на карте догадки. Если меняете фронтенд и
добавляете внешний ресурс, политику придётся расширить осознанно.

Директива `http2 on` требует nginx 1.25.1 и новее; в `nginx:alpine` он новее.

## Провайдер спутниковых снимков

По умолчанию используется ESRI World Imagery, токен не нужен. Адрес задаётся
переменной `SATELLITE_TILE_URL` и меняется без пересборки.

Важно: бэкенд **проксирует** тайлы — иначе клиент узнал бы координаты цели.
Перед сменой провайдера или выходом за рамки личного использования проверьте
его условия: проксирование и кэширование тайлов разрешено не всеми. Для
Mapbox шаблон выглядит так (токен подставьте свой):

```
SATELLITE_TILE_URL=https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}@2x.jpg90?access_token=ВАШ_ТОКЕН
```

## Резервное копирование

Данные лежат в томах `postgres_data` и `redis_data`. Кэш тайлов
восстанавливается сам, а базу стоит выгружать:

```bash
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > backup.sql.gz
```
