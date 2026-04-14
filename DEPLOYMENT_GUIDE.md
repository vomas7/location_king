# 🚀 Руководство по деплою Location King

## 📋 Обзор

Это руководство описывает процесс развёртывания Location King в production окружении.

### Архитектура production:
- **Домен:** `locationking.ru`
- **Поддомены:**
  - `locationking.ru` - основное приложение
  - `auth.locationking.ru` - Keycloak (аутентификация)
- **Технологии:** Docker, Nginx, PostgreSQL, Redis, Keycloak
- **Спутниковые снимки:** ESRI World Imagery (бесплатно)

## 🔧 Предварительные требования

### 1. Сервер
- Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- 2+ ядра CPU
- 4+ GB RAM
- 20+ GB SSD
- Public IP адрес

### 2. Домены
- Зарегистрированный домен (например, `locationking.ru`)
- Возможность настройки DNS записей
- SSL сертификаты (Let's Encrypt или коммерческие)

### 3. Установленные пакеты
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io docker-compose curl git

# CentOS/RHEL
sudo yum install -y docker docker-compose curl git
sudo systemctl start docker
sudo systemctl enable docker

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
# Выйти и зайти снова
```

## 🚀 Быстрый деплой

### Шаг 1: Подготовка сервера
```bash
# Клонировать репозиторий
git clone <repository-url>
cd location_king

# Создать production конфигурацию
cp .env.production.example .env.production
nano .env.production  # Отредактировать настройки
```

### Шаг 2: Настройка доменов
В DNS настройте:
```
A запись:
  locationking.ru → IP_сервера
  auth.locationking.ru → IP_сервера

CNAME запись (опционально):
  www.locationking.ru → locationking.ru
```

### Шаг 3: Получение SSL сертификатов
```bash
# Установите certbot (Let's Encrypt)
sudo apt-get install -y certbot python3-certbot-nginx

# Получите сертификаты
sudo certbot certonly --nginx \
  -d locationking.ru \
  -d www.locationking.ru \
  -d auth.locationking.ru \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email

# Скопируйте сертификаты в нужные папки
mkdir -p ssl/locationking.ru ssl/auth.locationking.ru
sudo cp /etc/letsencrypt/live/locationking.ru/fullchain.pem ssl/locationking.ru/
sudo cp /etc/letsencrypt/live/locationking.ru/privkey.pem ssl/locationking.ru/
sudo cp /etc/letsencrypt/live/auth.locationking.ru/fullchain.pem ssl/auth.locationking.ru/
sudo cp /etc/letsencrypt/live/auth.locationking.ru/privkey.pem ssl/auth.locationking.ru/
```

### Шаг 4: Запуск деплоя
```bash
# Сделайте скрипт исполняемым
chmod +x deploy_production.sh

# Запустите деплой
./deploy_production.sh
```

## ⚙️ Конфигурация .env.production

### Основные настройки:
```bash
# Домены
DOMAIN=locationking.ru
KEYCLOAK_HOSTNAME=auth.locationking.ru

# База данных
POSTGRES_USER=locationking_prod
POSTGRES_PASSWORD=strong_password_here
POSTGRES_DB=location_king_prod

# Redis
REDIS_PASSWORD=strong_redis_password_here

# Keycloak
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=strong_admin_password_here
KEYCLOAK_REALM=location-king
KEYCLOAK_CLIENT_ID=location-king-client

# Безопасность
SECRET_KEY=generate_with_openssl_rand_hex_32
```

### Генерация SECRET_KEY:
```bash
openssl rand -hex 32
```

## 🔐 Настройка Keycloak

После деплоя:

1. **Войдите в админ-панель:**
   - URL: `https://auth.locationking.ru`
   - Username: `admin` (из .env.production)
   - Password: ваш пароль администратора

2. **Создайте realm:**
   - Нажмите "Create realm"
   - Имя: `location-king`
   - Enabled: ON

3. **Создайте клиента:**
   - Clients → Create
   - Client ID: `location-king-client`
   - Client Protocol: `openid-connect`
   - Root URL: `https://locationking.ru`
   - Valid Redirect URIs: `https://locationking.ru/*`
   - Web Origins: `https://locationking.ru`
   - Access Type: `public` или `confidential`

4. **Создайте пользователей:**
   - Users → Add user
   - Заполните username, email
   - Credentials → Set password
   - Temporary: OFF

## 🌐 Настройка Nginx

### Конфигурационные файлы:
- `nginx/production/locationking.ru.conf` - основное приложение
- `nginx/production/auth.locationking.ru.conf` - Keycloak

### Портирование:
- **80/tcp** → HTTP → HTTPS редирект
- **443/tcp** → HTTPS с SSL

### Безопасность:
- HSTS headers
- CSP headers
- X-Frame-Options
- Rate limiting (опционально)

## 🗄️ База данных

### Миграции:
Миграции применяются автоматически при деплое через:
```bash
docker-compose -f docker-compose.prod.yml exec backend python3 apply_migrations.py
```

### Резервное копирование:
```bash
# Резервная копия PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U locationking_prod location_king_prod > backup_$(date +%Y%m%d).sql

# Восстановление
cat backup.sql | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U locationking_prod location_king_prod
```

### Мониторинг:
```bash
# Проверка размера БД
docker-compose -f docker-compose.prod.yml exec postgres psql -U locationking_prod -d location_king_prod -c "SELECT pg_size_pretty(pg_database_size('location_king_prod'));"

# Активные соединения
docker-compose -f docker-compose.prod.yml exec postgres psql -U locationking_prod -d location_king_prod -c "SELECT count(*) FROM pg_stat_activity;"
```

## 🔄 Обновление

### Обновление кода:
```bash
# Остановить сервисы
docker-compose -f docker-compose.prod.yml down

# Обновить код
git pull origin main

# Пересобрать и запустить
docker-compose -f docker-compose.prod.yml up --build -d

# Применить миграции (если есть)
docker-compose -f docker-compose.prod.yml exec backend python3 apply_migrations.py
```

### Обновление SSL сертификатов:
```bash
# Let's Encrypt автоматически обновляет сертификаты
# Вручную:
sudo certbot renew

# Перезапустить Nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

## 🚨 Устранение проблем

### Сервисы не запускаются:
```bash
# Проверить логи
docker-compose -f docker-compose.prod.yml logs -f

# Проверить статус
docker-compose -f docker-compose.prod.yml ps

# Проверить здоровье
curl -f https://locationking.ru/health
```

### Проблемы с БД:
```bash
# Проверить подключение
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U locationking_prod

# Проверить логи PostgreSQL
docker-compose -f docker-compose.prod.yml logs postgres
```

### Проблемы с Keycloak:
```bash
# Проверить доступность
curl -f https://auth.locationking.ru

# Проверить логи
docker-compose -f docker-compose.prod.yml logs keycloak
```

### Проблемы с SSL:
```bash
# Проверить сертификаты
openssl s_client -connect locationking.ru:443 -servername locationking.ru

# Проверить конфигурацию Nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

## 📊 Мониторинг и логи

### Логи:
```bash
# Просмотр логов в реальном времени
docker-compose -f docker-compose.prod.yml logs -f

# Логи Nginx
tail -f /var/log/nginx/*.log

# Логи приложения
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Мониторинг ресурсов:
```bash
# Использование CPU/RAM
docker stats

# Использование диска
df -h

# Использование памяти
free -h
```

### Метрики:
```bash
# Health check
curl https://locationking.ru/health

# API статус
curl https://locationking.ru/api/health

# Проверка БД
docker-compose -f docker-compose.prod.yml exec postgres psql -U locationking_prod -d location_king_prod -c "SELECT 1;"
```

## 🔧 Дополнительные настройки

### Файрвол:
```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Автозапуск при перезагрузке:
```bash
# Создать systemd сервис
sudo nano /etc/systemd/system/location-king.service

[Unit]
Description=Location King Production
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/location_king
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target

# Включить автозапуск
sudo systemctl enable location-king
```

### Ротация логов:
```bash
# Для Docker контейнеров
docker-compose -f docker-compose.prod.yml logs --tail=100

# Для Nginx (в конфигурации уже настроено)
# max-size: "10m", max-file: "3"
```

## 🎯 Проверка работоспособности

После деплоя проверьте:

1. **Основной сайт:** https://locationking.ru
2. **Keycloak:** https://auth.locationking.ru
3. **API документация:** https://locationking.ru/api/docs
4. **Health check:** https://locationking.ru/health
5. **Игровой процесс:** Запустите тестовую игру

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте логи: `docker-compose -f docker-compose.prod.yml logs -f`
2. Проверьте конфигурацию: `.env.production`
3. Проверьте SSL сертификаты
4. Проверьте DNS настройки
5. Создайте issue в репозитории

## 🎉 Готово!

**Location King успешно развёрнут в production!**

- 🌐 Доступен по: https://locationking.ru
- 🔐 Аутентификация: https://auth.locationking.ru
- 📡 API: https://locationking.ru/api/docs
- 🛰️ Спутниковые снимки: ESRI World Imagery (бесплатно)

**Удачи с проектом!** 🦁

---

*Руководство создано: 14 апреля 2026 года*  
*Версия: 1.0.0*  
*Ассистент: Лев 🦁*