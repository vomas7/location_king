# 🦁 Location King - Геогейссер с космическими снимками

**Профессиональная игровая платформа для любителей географии и карт**

## 🎯 О проекте

Location King - это современный геогейссер, где игроки:
1. **Видят** квадрат космического снимка (ограниченный экстент)
2. **Ищут** это место на карте OpenStreetMap
3. **Отмечают** предполагаемый центр снимка
4. **Получают** очки на основе точности

## 🏆 Ключевые особенности

### 🎮 Игровой процесс
- **Разные режимы:** Solo, Multiplayer, Challenge, Practice
- **Система рейтингов:** ELO рейтинг (как в шахматах)
- **Уровни и опыт:** Прогрессия игроков
- **Ежедневные челленджи:** Уникальные задания каждый день
- **Таблицы лидеров:** Рейтинги по ELO, общему счёту, среднему счёту

### 🗺️ Игровые зоны
- **12 категорий:** Города, природа, побережья, горы, пустыни и др.
- **7 уровней сложности:** От "Очень легко" до "Мастер"
- **Автостатистика:** Популярность, средний счёт, среднее расстояние
- **Географическая привязка:** Страны, регионы, теги

### 📊 Аналитика
- **Детальная статистика** для каждого игрока
- **Глобальная статистика** игры
- **Анализ популярности** зон
- **Временная статистика** (последние 30 дней)

## 🏗️ Технологический стек

### Бэкенд
- **Python 3.10+** с **FastAPI** (асинхронный)
- **PostgreSQL 15+** с **PostGIS** (геоданные)
- **SQLAlchemy 2.0** (async/await)
- **Alembic** (миграции)
- **Redis** (кэширование и сессии)

### Фронтенд
- **OpenLayers** (интерактивные карты)
- **Bootstrap 5** (адаптивный дизайн)
- **Vanilla JavaScript** (чистый JS)

### Инфраструктура
- **Docker** + **Docker Compose**
- **Nginx** (reverse proxy)
- **Keycloak** (аутентификация)
- **Mapbox Satellite API** (космические снимки)

## 🚀 Быстрый старт

### Вариант 1: Docker Compose (рекомендуется)

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd location_king

# 2. Настройте окружение
cp .env.example .env
# Отредактируйте .env, добавьте MAPBOX_ACCESS_TOKEN

# 3. Запустите все сервисы
docker-compose up --build

# 4. Откройте в браузере
# - Фронтенд: http://localhost
# - Бэкенд API: http://localhost:8000
# - Swagger UI: http://localhost:8000/api/docs
```

### Вариант 2: Локальная разработка

```bash
# 1. Установите PostgreSQL с PostGIS
# Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib postgis

# 2. Запустите скрипт настройки
./setup_local_dev.sh

# 3. Запустите бэкенд
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Запустите фронтенд (в другом терминале)
cd frontend
python3 -m http.server 8080

# 5. Откройте: http://localhost:8080
```

## 🔑 Получение Mapbox токена

1. Зарегистрируйтесь на [Mapbox](https://www.mapbox.com/)
2. Перейдите в [Dashboard](https://account.mapbox.com/)
3. Скопируйте **Default public token**
4. Добавьте в `.env` файл:
   ```
   MAPBOX_ACCESS_TOKEN=ваш_токен_здесь
   ```

## 📁 Структура проекта

```
location_king/
├── backend/                 # FastAPI бэкенд
│   ├── app/
│   │   ├── models/         # SQLAlchemy модели
│   │   │   ├── user.py     # Пользователи с рейтингами
│   │   │   ├── game_session.py  # Игровые сессии
│   │   │   ├── round.py    # Раунды с геоданными
│   │   │   ├── location_zone.py  # Игровые зоны
│   │   │   └── enums.py    # Enum'ы игры
│   │   ├── routers/        # API эндпоинты
│   │   ├── services/       # Бизнес-логика
│   │   ├── schemas/        # Pydantic схемы
│   │   ├── utils/          # Утилиты
│   │   ├── main.py         # Точка входа
│   │   └── config.py       # Конфигурация
│   ├── alembic/           # Миграции
│   ├── scripts/           # Вспомогательные скрипты
│   └── requirements.txt   # Зависимости Python
├── frontend/              # Веб-интерфейс
│   ├── index.html         # Основной HTML
│   ├── nginx.conf         # Конфигурация Nginx
│   └── Dockerfile
├── nginx/                 # Конфигурация основного Nginx
├── docker-compose.yml     # Docker Compose
└── docker-compose.dev.yml # Docker Compose для разработки
```

## 📡 API Документация

После запуска доступны:

- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/redoc  
- **OpenAPI схема:** http://localhost:8000/api/openapi.json

### Основные эндпоинты

#### Игровые сессии
- `POST /api/sessions/start` - Начать новую сессию
- `GET /api/sessions/{session_id}` - Получить информацию о сессии
- `POST /api/sessions/{session_id}/finish` - Завершить сессию

#### Раунды
- `GET /api/rounds/{round_id}` - Получить информацию о раунде
- `POST /api/rounds/{round_id}/guess` - Отправить догадку
- `GET /api/rounds/{round_id}/hint` - Получить подсказку

#### Игровые зоны
- `GET /api/zones/` - Список доступных зон
- `GET /api/zones/random` - Случайная зона
- `GET /api/zones/{zone_id}` - Информация о зоне

#### Статистика
- `GET /api/stats/user/{user_id}` - Статистика пользователя
- `GET /api/stats/global` - Глобальная статистика
- `GET /api/stats/leaderboard` - Таблица лидеров

## 🎮 Как играть

1. **Запустите** проект
2. **Откройте** http://localhost (или http://localhost:8080)
3. **Нажмите** "Начать игру"
4. **Посмотрите** на космический снимок
5. **Найдите** это место на карте ниже
6. **Кликните** на карте или введите координаты
7. **Нажмите** "Отправить догадку"
8. **Получите** результат: расстояние и очки

## 🔧 Разработка

### Миграции базы данных

```bash
cd backend

# Создать новую миграцию
alembic revision --autogenerate -m "описание изменений"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

### Тестирование

```bash
cd backend
source venv/bin/activate

# Запуск тестов
pytest tests/

# Запуск с покрытием кода
pytest --cov=app tests/
```

### Добавление новых зон

```bash
cd backend
python3 scripts/add_more_zones.py
```

## 📊 Модели данных

### User (игрок)
- **Рейтинги:** ELO, уровень, опыт, ранг
- **Статистика:** игры, раунды, счёт, расстояние
- **Профиль:** аватар, био, страна, язык

### GameSession (игровая сессия)
- **Режимы:** solo, multiplayer, challenge, practice
- **Статусы:** active, finished, abandoned, paused
- **Статистика:** счёт, время, раунды

### Round (раунд)
- **Геоданные:** цель, догадка, расстояние
- **Результаты:** очки, точность, уровень очков
- **Время:** начало, завершение, длительность

### LocationZone (игровая зона)
- **География:** полигон, центр, площадь, страна, регион
- **Категории:** city, nature, coast, mountains, desert, etc.
- **Сложность:** 1-7 (очень легко - мастер)
- **Статистика:** популярность, средний счёт, среднее расстояние

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функциональности
3. Внесите изменения
4. Напишите тесты
5. Создайте Pull Request

## 📄 Лицензия

MIT License - смотрите файл [LICENSE](LICENSE)

## 📞 Контакты

- **Разработчик:** Илья
- **Ассистент:** Лев 🦁
- **Проект:** Location King - геогейссер с космическими снимками

---

**Удачи в игре и разработке! Если что-то не работает - создавайте issue!** 🦁