# Деплой

Прод-контур поднимается одним `docker compose` из корня репозитория.
Публикацией образов CI не занимается: compose собирает бэкенд локально из
`backend/Dockerfile.prod`.

## Что требуется

- Linux-сервер с Docker и плагином Compose
  ([инструкция Docker](https://docs.docker.com/engine/install/))
- DNS-записи на IP сервера: основной домен и поддомены `api.` и `auth.`
- Заполненный `.env` в корне репозитория

## Сервисы

| Сервис      | Образ                        | Назначение                         |
|-------------|------------------------------|------------------------------------|
| `nginx`     | `nginx:alpine`               | статика фронтенда и прокси к API   |
| `backend`   | сборка `backend/Dockerfile.prod` | FastAPI                        |
| `postgres`  | `postgis/postgis:16-3.4-alpine` | основная БД                     |
| `redis`     | `redis:7-alpine`             | кэш                                |
| `keycloak`  | `quay.io/keycloak/keycloak:24.0` | не подключён к бэкенду         |
| `keycloak_db` | `postgres:16-alpine`       | БД для Keycloak                    |

## Порядок

1. Клонировать репозиторий на сервер.

2. Подготовить конфигурацию:

   ```bash
   cp .env.example .env
   $EDITOR .env
   ```

3. Поднять контейнеры:

   ```bash
   docker compose up --build -d
   docker compose ps
   ```

4. Накатить миграции и загрузить игровые зоны:

   ```bash
   docker compose exec backend alembic upgrade head
   docker compose exec backend python3 scripts/init_test_data.py
   docker compose exec backend python3 scripts/add_more_zones.py
   ```

5. Проверить:

   ```bash
   curl http://api.<ваш-домен>/health
   ```

Скрипт `deploy.sh` в корне делает те же шаги подряд.

Полезные команды собраны в корневом `Makefile`: `make prod`, `make logs`,
`make migrate`, `make shell-db`.

## Обновление

```bash
git pull
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

Миграции применяются только вперёд, уже применённые ревизии не редактируются.

## Что в прод-контуре пока не работает

Это известные проблемы, а не то, что нужно перепроверять при деплое:

- **HTTPS не настроен.** В `nginx/conf.d/locationking.conf` есть только
  `listen 80`, хотя compose публикует и 443. Сертификаты сейчас
  терминируются на стороне хостинга. 443-блок добавляется на этапе 8.
- **Образ бэкенда в проде не используется.** Сервис `backend` монтирует
  `./backend:/app` поверх собранного образа, то есть исполняется код с
  хоста. Убирается на этапе 3.
- **У бэкенда нет выхода в интернет.** Сервис подключён только к сети
  `internal_net` с `internal: true`, а провайдер снимков ходит наружу к
  ESRI. Сеть чинится на этапе 3.
- **Игра работает на заглушке в памяти процесса.** PostgreSQL и Redis
  подняты, но игровым циклом не используются. Переезд на БД — этап 2.
- **Авторизации нет.** Keycloak поднят, но к бэкенду не подключён; все
  запросы выполняются от пользователя `id=1`. Собственный JWT — этап 4.
