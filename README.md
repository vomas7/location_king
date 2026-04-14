# 🦁 Location King

Профессиональный геогейссер с космическими снимками. Игроки видят квадрат спутникового снимка и должны найти его центр на карте.

## 🚀 Быстрый старт

### Требования
- Docker & Docker Compose
- SSL сертификаты для вашего домена
- Домен (например, locationking.ru)

### Установка

1. **Клонируйте репозиторий**
   ```bash
   git clone <repository-url>
   cd location_king
   ```

2. **Настройте окружение**
   ```bash
   cp .env.example .env
   # Отредактируйте .env файл
   ```

3. **Добавьте SSL сертификаты**
   ```bash
   mkdir -p ssl
   # Поместите ваши сертификаты:
   # - ssl/fullchain.pem
   # - ssl/privkey.pem
   ```

4. **Запустите приложение**
   ```bash
   ./deploy.sh
   ```

## 🏗️ Архитектура

### Технологии
- **Backend:** Python + FastAPI (асинхронный)
- **Frontend:** OpenLayers + Bootstrap 5
- **База данных:** PostgreSQL + PostGIS
- **Аутентификация:** Keycloak
- **Спутниковые снимки:** ESRI World Imagery (бесплатно)
- **Инфраструктура:** Docker + Nginx

### Сервисы
- `nginx` - Веб-сервер и прокси
- `backend` - FastAPI приложение
- `postgres` - База данных с PostGIS
- `redis` - Кэш и сессии
- `keycloak` - Аутентификация

## 📁 Структура проекта

```
location_king/
├── backend/                 # FastAPI приложение
│   ├── app/                # Исходный код
│   ├── alembic/            # Миграции базы данных
│   ├── scripts/            # Вспомогательные скрипты
│   └── requirements.txt    # Зависимости Python
├── frontend/               # Веб-интерфейс
│   └── index.html          # Основная страница
├── nginx/                  # Конфигурация Nginx
│   └── conf.d/
│       └── locationking.ru.conf
├── ssl/                    # SSL сертификаты
├── .env                    # Конфигурация (не в репозитории)
├── .env.example            # Пример конфигурации
├── docker-compose.yml      # Docker Compose
├── deploy.sh               # Скрипт деплоя
└── README.md               # Эта документация
```

## 🔧 Конфигурация

### .env файл
Создайте `.env` файл на основе `.env.example`:

```bash
# База данных
POSTGRES_USER=locationking
POSTGRES_PASSWORD=your_password
POSTGRES_DB=location_king

# Redis
REDIS_PASSWORD=your_redis_password

# Keycloak
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin_password
KEYCLOAK_URL=https://your-domain.ru/auth
KEYCLOAK_REALM=location-king
KEYCLOAK_CLIENT_ID=location-king-client

# Приложение
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/location_king
REDIS_URL=redis://:password@redis:6379/0
MAPBOX_ACCESS_TOKEN=  # Опционально, по умолчанию используется ESRI
```

### SSL сертификаты
Поместите ваши SSL сертификаты в папку `ssl/`:
- `ssl/fullchain.pem` - Публичный сертификат
- `ssl/privkey.pem` - Приватный ключ

## 🎮 Игровой процесс

1. **Начало игры:** Игрок начинает новую сессию
2. **Показ снимка:** Отображается квадрат спутникового снимка
3. **Поиск на карте:** Игрок ищет это место на карте OpenStreetMap
4. **Отметка точки:** Игрок отмечает предполагаемый центр снимка
5. **Результат:** Система вычисляет расстояние и начисляет очки

## 📊 Особенности

### Для игроков
- Система рейтингов ELO
- Уровни и опыт
- Ежедневные челленджи
- Таблицы лидеров
- Детальная статистика

### Для разработчиков
- Профессиональная архитектура
- Полная документация API
- Автоматические миграции БД
- Готовность к продакшену
- Масштабируемость

## 🔐 Безопасность

- HTTPS с правильными security headers
- Аутентификация через Keycloak
- Валидация всех входных данных
- Защита от распространенных атак

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь в наличии SSL сертификатов
3. Проверьте конфигурацию в `.env` файле

## 📄 Лицензия

MIT License

---

**Удачи с Location King!** 🦁