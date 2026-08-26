# Location King

Геогессер по спутниковым снимкам. Игроку показывают участок снимка — без
подписей и без координат — и он ищет это место на карте мира. Чем ближе
поставленная точка к центру участка, тем больше очков.

<!-- markdownlint-disable-next-line -->
> Сервер авторитетен: до принятой догадки клиент не получает координаты цели
> ни в одном ответе API. Снимок приходит через прокси по локальным координатам
> тайлов, так что подсмотреть ответ в DevTools нельзя.

## Как это устроено

Область раунда — это один тайл Web Mercator и его потомки на четыре уровня
вглубь. Цель раунда — центр этого тайла.

Клиент запрашивает тайлы по локальной сетке:
`GET /api/rounds/{id}/tiles/{z}/{x}/{y}.jpg`, где `z` — уровень от 0 до
максимального, а `x` и `y` — номера внутри уровня. Сервер переводит их в
координаты тайлового сервера, забирает снимок и кладёт в Redis. Запрос за
пределы области возвращает 404, чужой раунд — 403.

Расстояние и очки считает только сервер, единственной формулой из
`app/services/scoring.py`.

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic
- **База:** PostgreSQL 16 + PostGIS — зоны хранятся полигонами, точка раунда
  выбирается через `ST_GeneratePoints`
- **Кэш:** Redis 7 — спутниковые тайлы
- **Аутентификация:** свой JWT, пароли argon2id, есть гостевой вход
- **Frontend:** статические HTML/CSS/JS на OpenLayers, без сборки и без
  запросов на сторонние домены
- **Инфраструктура:** Docker Compose, Nginx

## Запуск

```bash
git clone https://github.com/vomas7/location_king
cd location_king

make dev        # поднимет postgres, redis, backend и nginx
make migrate    # накатит миграции
make seed       # загрузит 23 игровые зоны
```

Игра: <http://localhost:8080>. Документация API: <http://localhost:8000/api/docs>.

Остановить — `make down`, вместе с данными — `make down-v`.

### Без Docker

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env      # заполните JWT_SECRET
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

Фронтенд — статика: раздайте каталог `frontend/` любым сервером, который
проксирует `/api` на бэкенд (как это делает `nginx/snippets/site.conf`).

## Разработка

Перед коммитом, из каталога `backend/`:

```bash
ruff check .
ruff format --check .
pytest
```

CI выполняет то же самое и падает, если проверки не проходят или покрытие
опускается ниже 60%.

Структура бэкенда:

```
app/
  routers/    HTTP-слой: разбор запроса, вызов сервиса, ответ
  services/   бизнес-логика и правила игры
  models/     модели SQLAlchemy
  schemas/    схемы Pydantic
  utils/      чистые функции без зависимостей от БД
```

## API

| Метод  | Путь                                    | Что делает                             |
|--------|-----------------------------------------|----------------------------------------|
| `POST` | `/api/auth/register`                    | регистрация по email и паролю          |
| `POST` | `/api/auth/login`                       | вход                                   |
| `POST` | `/api/auth/guest`                       | игра без регистрации                   |
| `POST` | `/api/auth/refresh`                     | обновление пары токенов                |
| `GET`  | `/api/auth/me`                          | профиль и статистика                   |
| `POST` | `/api/sessions`                         | начать партию, получить первый раунд   |
| `GET`  | `/api/sessions/{id}`                    | состояние партии и история раундов     |
| `POST` | `/api/sessions/{id}/finish`             | завершить партию досрочно              |
| `GET`  | `/api/rounds/{id}`                      | активный раунд, без координат          |
| `POST` | `/api/rounds/{id}/guess`                | догадка, в ответе появляется цель      |
| `GET`  | `/api/rounds/{id}/tiles/{z}/{x}/{y}.jpg`| тайл снимка по локальным координатам   |
| `GET`  | `/api/zones`                            | список игровых зон                     |

Полное описание — в `/api/docs`.

## Деплой

См. [docs/deployment.md](docs/deployment.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).
