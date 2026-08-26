# Location King

Геогессер по спутниковым снимкам: игроку показывают квадрат снимка, он ищет
это место на обычной карте и ставит точку. Чем ближе точка к центру снимка,
тем больше очков.

## Состояние проекта

Проект приводится в порядок по этапам, и часть заявленной функциональности
пока не работает. Что есть на сегодня:

- игровой цикл работает на заглушке в памяти процесса (`app/game_mock.py`),
  роутеры `sessions`, `rounds`, `zones` в приложение не подключены;
- PostgreSQL/PostGIS, модели и миграции написаны, но в рабочем контуре не
  задействованы;
- авторизации нет: бэкенд всегда работает от пользователя `id=1`;
- сервер отдаёт клиенту координаты цели, то есть ответ виден в DevTools.

Ничего из перечисленного не нужно считать рабочим, пока соответствующий этап
не закрыт.

## Стек

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic
- База данных: PostgreSQL 16 + PostGIS
- Кэш: Redis 7
- Frontend: статические HTML/JS на OpenLayers, без сборки
- Инфраструктура: Docker Compose, Nginx
- Снимки: ESRI World Imagery (Mapbox — запасной вариант, нужен токен)

## Структура репозитория

```
backend/
  app/
    routers/    HTTP-слой: разбор запроса, вызов сервиса, ответ
    services/   бизнес-логика
    models/     модели SQLAlchemy
    schemas/    схемы Pydantic
    utils/      чистые функции без зависимостей от БД
  alembic/      миграции
  scripts/      сиды и SQL инициализации БД
  tests/        тесты
frontend/       статический клиент
nginx/          конфигурация Nginx для прод-контура
docs/           документация по деплою
```

## Локальный запуск

Нужны Python 3.12 и Docker.

1. Поднять базу и Redis:

   ```bash
   docker run -d --name lk_postgres -p 5432:5432 \
     -e POSTGRES_USER=locationking -e POSTGRES_PASSWORD=locationking \
     -e POSTGRES_DB=location_king postgis/postgis:16-3.4
   docker run -d --name lk_redis -p 6379:6379 redis:7-alpine
   ```

   Одна команда `make dev` появится вместе с `docker-compose.dev.yml`.

2. Установить зависимости и настроить окружение:

   ```bash
   cd backend
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements-dev.txt
   cp .env.example .env
   ```

3. Накатить миграции и загрузить зоны:

   ```bash
   alembic upgrade head
   python scripts/init_test_data.py
   ```

4. Запустить приложение:

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   Проверка: <http://localhost:8000/api/health>.
   Swagger доступен на `/api/docs` при `DEBUG=true`.

Фронтенд — статика, её достаточно раздать любым статическим сервером из
каталога `frontend/`. Адрес API сейчас захардкожен в `frontend/index.js`.

## Линтер и тесты

Перед коммитом, из каталога `backend/`:

```bash
ruff check .
ruff format --check .
pytest
```

Те же три проверки выполняет CI и падает, если хотя бы одна не проходит.

## Деплой

Описан в [docs/deployment.md](docs/deployment.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).
