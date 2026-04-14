# Location King Backend

Бэкенд для игры-геогейссера "Location King" на FastAPI.

## 🎯 Возможности

- **Управление игровыми сессиями**: создание, получение, завершение
- **Генерация раундов**: случайные точки в заданных зонах
- **Космические снимки**: интеграция с Mapbox Satellite API
- **Система очков**: расчёт на основе точности догадки
- **Игровые зоны**: различные регионы с разной сложностью
- **Аутентификация**: интеграция с Keycloak (в разработке)

## 🏗️ Архитектура

### Технологии
- **Python 3.10+** с **FastAPI** для API
- **PostgreSQL** с **PostGIS** для геоданных
- **SQLAlchemy 2.0** (async) для работы с БД
- **Alembic** для миграций
- **Redis** для кэширования и сессий
- **Mapbox API** для космических снимков

### Структура проекта
```
app/
├── main.py              # Точка входа FastAPI
├── config.py           # Конфигурация приложения
├── database.py         # Настройка БД (async SQLAlchemy)
├── models/             # Модели SQLAlchemy
│   ├── user.py
│   ├── game_session.py
│   ├── round.py
│   └── location_zone.py
├── schemas/            # Pydantic схемы для API
│   └── game.py
├── routers/            # FastAPI роутеры
│   ├── sessions.py
│   ├── rounds.py
│   └── zones.py
├── services/           # Бизнес-логика
│   ├── satellite_provider.py
│   └── challenge_generator.py
└── utils/              # Вспомогательные утилиты
```

## 🚀 Быстрый старт

### 1. Настройка окружения

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd location_king/backend

# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установите зависимости
pip install -r requirements.txt

# Создайте .env файл на основе примера
cp .env.example .env
# Отредактируйте .env файл, указав свои настройки
```

### 2. Настройка базы данных

```bash
# Убедитесь, что PostgreSQL с PostGIS установлен и запущен
# Создайте базу данных
createdb location_king

# Включите расширение PostGIS
psql -d location_king -c "CREATE EXTENSION postgis;"

# Запустите миграции Alembic
alembic upgrade head

# Инициализируйте тестовые данные
python scripts/init_test_data.py
```

### 3. Запуск приложения

```bash
# Запуск в режиме разработки
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или через Docker Compose (из корня проекта)
cd ..
docker-compose up --build
```

### 4. Получение Mapbox токена

1. Зарегистрируйтесь на [Mapbox](https://www.mapbox.com/)
2. Перейдите в [аккаунт](https://account.mapbox.com/)
3. Скопируйте **Default public token**
4. Добавьте его в `.env` файл как `MAPBOX_ACCESS_TOKEN`

## 📚 API Документация

После запуска приложения доступны:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI схема**: http://localhost:8000/api/openapi.json

## 🔧 Основные эндпоинты

### Игровые сессии
- `POST /api/sessions/start` - Начать новую сессию
- `GET /api/sessions/{session_id}` - Получить информацию о сессии
- `GET /api/sessions/{session_id}/history` - История раундов сессии
- `POST /api/sessions/{session_id}/finish` - Завершить сессию досрочно

### Раунды
- `GET /api/rounds/{round_id}` - Получить информацию о раунде
- `POST /api/rounds/{round_id}/guess` - Отправить догадку
- `GET /api/rounds/{round_id}/hint` - Получить подсказку

### Игровые зоны
- `GET /api/zones/` - Список доступных зон
- `GET /api/zones/random` - Случайная зона
- `GET /api/zones/{zone_id}` - Информация о зоне
- `GET /api/zones/{zone_id}/preview` - Превью зоны

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/

# Запуск с покрытием кода
pytest --cov=app tests/
```

## 🐳 Docker

```bash
# Сборка образа
docker build -t location-king-backend .

# Запуск контейнера
docker run -p 8000:8000 --env-file .env location-king-backend
```

## 📊 Модели данных

### User
- `id` - Уникальный идентификатор
- `keycloak_id` - ID пользователя в Keycloak
- `username` - Имя пользователя
- `total_score` - Общий счёт

### GameSession
- `id` - UUID сессии
- `user_id` - Ссылка на пользователя
- `mode` - Режим игры (solo/multiplayer)
- `status` - Статус сессии
- `rounds_total` - Всего раундов
- `rounds_done` - Завершённых раундов
- `total_score` - Счёт сессии

### Round
- `id` - Уникальный идентификатор
- `session_id` - Ссылка на сессию
- `zone_id` - Ссылка на зону
- `target_point` - Правильный ответ (Point, SRID 4326)
- `guess_point` - Догадка пользователя (Point, SRID 4326)
- `distance_km` - Расстояние в км
- `score` - Очки за раунд
- `view_extent_km` - Размер области снимка

### LocationZone
- `id` - Уникальный идентификатор
- `name` - Название зоны
- `description` - Описание
- `difficulty` - Сложность (1-5)
- `category` - Категория
- `polygon` - Полигон зоны (Polygon, SRID 4326)
- `is_active` - Активна ли зона

## 🔄 Миграции

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Описание изменений"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функциональности
3. Внесите изменения
4. Напишите тесты
5. Создайте Pull Request

## 📄 Лицензия

MIT License - смотрите файл [LICENSE](../LICENSE)