# 🚀 Быстрый старт Location King

## 📋 Что сделано

Я, Лев 🦁, создал полноценную основу для игры Location King:

### ✅ **Бэкенд (FastAPI + PostgreSQL + PostGIS)**
1. **Модели БД:**
   - `User` - пользователи (интеграция с Keycloak)
   - `GameSession` - игровые сессии
   - `Round` - раунды с геоданными
   - `LocationZone` - игровые зоны

2. **Сервисы:**
   - `satellite_provider.py` - интеграция с Mapbox Satellite API
   - `challenge_generator.py` - генерация случайных точек в зонах
   - `GeometryUtils` - вычисление расстояний и очков

3. **API эндпоинты:**
   - `/api/sessions/*` - управление сессиями
   - `/api/rounds/*` - работа с раундами
   - `/api/zones/*` - список игровых зон
   - `/api/health` - проверка здоровья

4. **Тестовые данные:**
   - 6 игровых зон (Москва, СПб, Сочи, Байкал, Гоби, Европа)
   - Тестовый пользователь

### ✅ **Фронтенд (OpenLayers + Bootstrap)**
1. **Интерфейс:**
   - Карта OpenStreetMap с выбором точек
   - Поле для космического снимка
   - Управление игрой (старт, догадка, подсказка, завершение)
   - Лог действий

2. **Функциональность:**
   - Загрузка списка зон
   - Начало игровой сессии
   - Отправка догадок с координатами
   - Отображение статистики

### ✅ **Инфраструктура**
1. **Docker Compose** готов к запуску
2. **Nginx** как reverse proxy
3. **PostgreSQL** с PostGIS
4. **Redis** для кэширования

## 🚀 Как запустить проект

### Вариант 1: Docker Compose (рекомендуется)

```bash
# 1. Перейдите в папку проекта
cd /home/ilya/location_king

# 2. Создайте .env файл для бэкенда
cp backend/.env.example backend/.env
# Отредактируйте backend/.env, добавьте MAPBOX_ACCESS_TOKEN

# 3. Запустите все сервисы
docker-compose up --build

# 4. Откройте в браузере:
# - Фронтенд: http://localhost
# - Бэкенд API: http://localhost:8000
# - Swagger UI: http://localhost:8000/api/docs
```

### Вариант 2: Ручной запуск (для разработки)

```bash
# 1. Настройте базу данных
sudo -u postgres createdb location_king
sudo -u postgres psql -d location_king -c "CREATE EXTENSION postgis;"

# 2. Настройте бэкенд
cd /home/ilya/location_king/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Создайте .env файл
cp .env.example .env
# Добавьте MAPBOX_ACCESS_TOKEN и настройте DATABASE_URL

# 4. Инициализируйте базу данных
python scripts/init_test_data.py

# 5. Запустите бэкенд
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. В другом терминале запустите фронтенд
cd /home/ilya/location_king/frontend
# Откройте index.html в браузере или используйте простой HTTP-сервер
python3 -m http.server 8080
```

## 🔑 Получение Mapbox токена

1. Зарегистрируйтесь на [Mapbox](https://www.mapbox.com/)
2. Перейдите в [Dashboard](https://account.mapbox.com/)
3. Скопируйте **Default public token**
4. Добавьте в `backend/.env`:
   ```
   MAPBOX_ACCESS_TOKEN=ваш_токен_здесь
   ```

## 🎮 Как играть (тестовый режим)

1. **Откройте** http://localhost (или index.html)
2. **Нажмите** "Начать игру"
3. **Посмотрите** на космический снимок (пока заглушка)
4. **Найдите** это место на карте ниже (OpenStreetMap)
5. **Кликните** на карте или введите координаты вручную
6. **Нажмите** "Отправить догадку"
7. **Получите** результат: расстояние и очки

## 📁 Структура проекта

```
location_king/
├── backend/                 # FastAPI бэкенд
│   ├── app/
│   │   ├── models/         # SQLAlchemy модели
│   │   ├── routers/        # API эндпоинты
│   │   ├── services/       # Бизнес-логика
│   │   ├── schemas/        # Pydantic схемы
│   │   ├── main.py         # Точка входа
│   │   └── config.py       # Конфигурация
│   ├── scripts/            # Вспомогательные скрипты
│   ├── requirements.txt    # Зависимости Python
│   └── Dockerfile
├── frontend/               # Веб-интерфейс
│   ├── index.html          # Основной HTML
│   ├── nginx.conf          # Конфигурация Nginx
│   └── Dockerfile
├── nginx/                  # Конфигурация основного Nginx
├── docker-compose.yml      # Docker Compose
└── docker-compose.dev.yml  # Docker Compose для разработки
```

## 🔧 Что нужно доделать

### Высокий приоритет:
1. **Интеграция с Mapbox Satellite API** - получение реальных снимков
2. **Аутентификация через Keycloak** - реальные пользователи
3. **Улучшение фронтенда** - загрузка реальных снимков

### Средний приоритет:
1. **Система очков** - более сложные формулы
2. **Больше игровых зон** - покрыть весь мир
3. **Мультиплеер** - соревновательный режим

### Низкий приоритет:
1. **Мобильное приложение** - React Native
2. **Социальные функции** - друзья, таблицы лидеров
3. **Ежедневные челленджи** - одинаковые для всех игроков

## 🐛 Известные проблемы

1. **Космические снимки** - пока заглушка, нужен Mapbox токен
2. **Аутентификация** - заглушка для тестирования
3. **Нет тестов** - нужно добавить pytest
4. **Нет CI/CD** - настройка GitHub Actions

## 🤝 Как помочь проекту

1. **Получите Mapbox токен** и добавьте в .env
2. **Протестируйте API** через Swagger UI
3. **Создайте issue** если найдёте баг
4. **Предложите улучшения** для игрового процесса

## 📞 Контакты

- **Разработчик:** Илья
- **Ассистент:** Лев 🦁 (я)
- **Проект:** Location King - геогейссер с космическими снимками

---

**Удачи в разработке! Если что-то не работает - пиши, разберёмся вместе!** 🦁