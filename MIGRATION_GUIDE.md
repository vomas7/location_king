# 🚀 Руководство по миграциям Location King

## 📋 Быстрые команды

### 1. Проверить окружение:
```bash
./check_environment.sh
```

### 2. Запустить автоматическую накатку:
```bash
./run_migrations.sh
```

### 3. Просмотреть SQL миграции:
```bash
./show_migration_sql.sh
```

### 4. Симуляция миграций:
```bash
python3 simulate_migrations.py
```

## 🐳 Вариант 1: Docker (рекомендуется)

### Установка Docker:
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
# Выйдите и зайдите снова в терминал
```

### Запуск миграций через Docker:
```bash
cd /home/ilya/location_king

# 1. Запустить PostgreSQL
docker-compose up -d postgres

# 2. Подождать запуска (5 секунд)
sleep 5

# 3. Накатить миграции
docker-compose exec backend python3 apply_migrations.py

# 4. Инициализировать тестовые данные
docker-compose exec backend python3 scripts/init_test_data.py

# 5. Добавить дополнительные зоны
docker-compose exec backend python3 scripts/add_more_zones.py

# 6. Запустить всё приложение
docker-compose up --build
```

## 🖥️ Вариант 2: Локальный PostgreSQL

### Установка PostgreSQL:
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib postgis python3-pip
```

### Настройка базы данных:
```bash
# Создать пользователя
sudo -u postgres psql -c "CREATE USER locationking WITH PASSWORD 'locationking123';"

# Создать базу данных
sudo -u postgres psql -c "CREATE DATABASE location_king;"

# Дать права
sudo -u postgres psql -d location_king -c "GRANT ALL PRIVILEGES ON DATABASE location_king TO locationking;"

# Включить PostGIS
sudo -u postgres psql -d location_king -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -d location_king -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"
```

### Установка Python зависимостей:
```bash
cd /home/ilya/location_king/backend
pip3 install -r requirements.txt
```

### Накатка миграций:
```bash
cd /home/ilya/location_king/backend
python3 apply_migrations.py
```

### Инициализация тестовых данных:
```bash
python3 scripts/init_test_data.py
python3 scripts/add_more_zones.py
```

## 📊 Что создают миграции

### Таблица 1: `users` (игроки)
- **Базовые поля:** id, username, keycloak_id, total_score
- **Рейтинги:** elo_rating, rank, level, experience
- **Статистика:** games_played, average_score, best_score, worst_score
- **Профиль:** email, avatar_url, bio, country, timezone
- **Флаги:** is_active, is_verified, is_premium

### Таблица 2: `game_sessions` (игровые сессии)
- **Базовые поля:** id, user_id, mode, status, rounds_total
- **Статистика:** total_score, average_score, best_round_score
- **Время:** started_at, finished_at, last_activity_at
- **Метаданные:** title, description, is_public

### Таблица 3: `rounds` (раунды)
- **Геоданные:** target_lng/lat, guess_lng/lat, distance_km
- **Результаты:** score, accuracy_percentage, max_score
- **Статусы:** status (pending, active, guessed, skipped)
- **Время:** started_at, completed_at, time_limit_seconds
- **Метаданные:** satellite_image_url, hint_used, notes

### Таблица 4: `location_zones` (игровые зоны)
- **Геоданные:** polygon (PostGIS), center_point, area_sq_km
- **Категории:** category (12 типов), difficulty (1-7)
- **Статистика:** total_rounds, average_score, popularity
- **География:** country, region, tags
- **Флаги:** is_active, is_featured, is_premium

## 🔍 Проверка миграций

### Проверить текущую ревизию:
```bash
cd /home/ilya/location_king/backend
alembic current
```

### Просмотреть историю:
```bash
alembic history
```

### Просмотреть SQL без выполнения:
```bash
alembic upgrade head --sql
```

## 🚨 Устранение проблем

### Ошибка: "PostGIS extension not found"
```bash
# Войти в PostgreSQL
sudo -u postgres psql -d location_king

# Внутри psql:
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
\q
```

### Ошибка: "Permission denied"
```bash
# Дать права пользователю
sudo -u postgres psql -d location_king -c "GRANT ALL PRIVILEGES ON DATABASE location_king TO locationking;"
sudo -u postgres psql -d location_king -c "GRANT ALL PRIVILEGES ON SCHEMA public TO locationking;"
```

### Ошибка: "Python dependencies missing"
```bash
cd /home/ilya/location_king/backend
pip3 install -r requirements.txt --upgrade
```

### Ошибка: "Docker not found"
```bash
# Установить Docker
sudo apt-get install docker.io

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER

# Выйти и зайти снова
logout
# Затем снова войти в систему
```

## 📝 Ручное применение SQL

Если Alembic не работает, можно применить SQL вручную:

```bash
# Создать файл со всеми миграциями
./show_migration_sql.sh > all_migrations.sql

# Применить через psql
sudo -u postgres psql -d location_king -f all_migrations.sql
```

## 🧪 Тестирование

### Создать тестовую базу:
```bash
createdb location_king_test
psql -d location_king_test -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Применить миграции к тестовой базе
DATABASE_URL=postgresql+asyncpg://locationking:locationking123@localhost:5432/location_king_test \
cd backend && python3 apply_migrations.py
```

### Проверить структуру:
```sql
-- Войти в psql
psql -U locationking -d location_king

-- Показать таблицы
\dt

-- Показать структуру таблицы
\d+ users
\d+ game_sessions
\d+ rounds
\d+ location_zones

-- Показать индексы
\di
```

## 🎯 Быстрая команда для Ильи

```bash
# Если есть sudo доступ:
sudo apt-get install postgresql postgresql-contrib postgis python3-pip
sudo -u postgres psql -c "CREATE USER locationking WITH PASSWORD 'locationking123';"
sudo -u postgres psql -c "CREATE DATABASE location_king;"
sudo -u postgres psql -d location_king -c "GRANT ALL PRIVILEGES ON DATABASE location_king TO locationking;"
sudo -u postgres psql -d location_king -c "CREATE EXTENSION IF NOT EXISTS postgis;"
cd /home/ilya/location_king/backend
pip3 install -r requirements.txt
python3 apply_migrations.py
python3 scripts/init_test_data.py
python3 scripts/add_more_zones.py
echo "✅ Миграции накатаны! Запускай: uvicorn app.main:app --reload"
```

## 📞 Помощь

Если что-то не работает:
1. Запустите `./check_environment.sh`
2. Проверьте логи: `tail -f /var/log/postgresql/postgresql-*.log`
3. Создайте issue в репозитории

**Удачи с накаткой миграций!** 🦁

---

*Создано ассистентом Львом для проекта Location King*  
*14 апреля 2026 года*