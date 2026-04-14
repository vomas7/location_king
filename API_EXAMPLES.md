# 📡 API Examples - Location King

Примеры запросов к API для тестирования и разработки.

## 🔧 Перед началом

Убедитесь, что бэкенд запущен:
```bash
cd /home/ilya/location_king/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Или через Docker:
```bash
cd /home/ilya/location_king
docker-compose up backend
```

## 🌐 Базовые запросы

### 1. Проверка здоровья API
```bash
curl -X GET "http://localhost:8000/api/health" -H "accept: application/json"
```

**Ответ:**
```json
{
  "status": "ok",
  "service": "location-king-backend",
  "version": "0.1.0",
  "debug": true
}
```

### 2. Корневой эндпоинт
```bash
curl -X GET "http://localhost:8000/" -H "accept: application/json"
```

## 🎮 Игровые сессии

### 1. Начать новую сессию
```bash
curl -X POST "http://localhost:8000/api/sessions/start" \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id": null,
    "difficulty": 2,
    "category": "city",
    "rounds_total": 3
  }'
```

**Ответ:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "mode": "solo",
  "status": "active",
  "rounds_total": 3,
  "rounds_done": 0,
  "total_score": 0,
  "started_at": "2024-01-15T10:30:00Z",
  "finished_at": null,
  "current_round": {
    "id": 1,
    "zone": {
      "id": 1,
      "name": "Москва, центр",
      "description": "Центральная часть Москвы...",
      "difficulty": 1,
      "category": "city"
    },
    "satellite_image_url": "",
    "view_extent_km": 5,
    "created_at": "2024-01-15T10:30:00Z",
    "guess_point": null,
    "distance_km": null,
    "score": null,
    "guessed_at": null
  }
}
```

### 2. Получить информацию о сессии
```bash
curl -X GET "http://localhost:8000/api/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -H "accept: application/json"
```

### 3. Завершить сессию досрочно
```bash
curl -X POST "http://localhost:8000/api/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/finish" \
  -H "accept: application/json"
```

## 🎯 Раунды

### 1. Получить информацию о раунде
```bash
curl -X GET "http://localhost:8000/api/rounds/1" \
  -H "accept: application/json"
```

### 2. Отправить догадку
```bash
curl -X POST "http://localhost:8000/api/rounds/1/guess" \
  -H "Content-Type: application/json" \
  -d '{
    "longitude": 37.6173,
    "latitude": 55.7558
  }'
```

**Ответ:**
```json
{
  "round_id": 1,
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "distance_km": 12.34,
  "score": 4380,
  "total_session_score": 4380,
  "rounds_done": 1,
  "rounds_total": 3,
  "next_round": {
    "id": 2,
    "zone": {
      "id": 2,
      "name": "Санкт-Петербург",
      "description": "Исторический центр...",
      "difficulty": 1,
      "category": "city"
    },
    "satellite_image_url": "",
    "view_extent_km": 5,
    "created_at": "2024-01-15T10:31:00Z",
    "guess_point": null,
    "distance_km": null,
    "score": null,
    "guessed_at": null
  },
  "is_session_finished": false
}
```

### 3. Получить подсказку
```bash
curl -X GET "http://localhost:8000/api/rounds/1/hint" \
  -H "accept: application/json"
```

**Ответ:**
```json
{
  "zone_name": "Москва, центр",
  "difficulty": 1,
  "category": "city",
  "hint": "Это местность в зоне 'Москва, центр'. Сложность: 1/5."
}
```

## 🗺️ Игровые зоны

### 1. Получить список всех зон
```bash
curl -X GET "http://localhost:8000/api/zones/" \
  -H "accept: application/json"
```

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "Москва, центр",
    "description": "Центральная часть Москвы...",
    "difficulty": 1,
    "category": "city"
  },
  {
    "id": 2,
    "name": "Санкт-Петербург",
    "description": "Исторический центр...",
    "difficulty": 1,
    "category": "city"
  }
]
```

### 2. Получить случайную зону
```bash
curl -X GET "http://localhost:8000/api/zones/random?difficulty=2&category=city" \
  -H "accept: application/json"
```

### 3. Получить информацию о конкретной зоне
```bash
curl -X GET "http://localhost:8000/api/zones/1" \
  -H "accept: application/json"
```

### 4. Получить превью зоны
```bash
curl -X GET "http://localhost:8000/api/zones/1/preview" \
  -H "accept: application/json"
```

**Ответ:**
```json
{
  "zone": {
    "id": 1,
    "name": "Москва, центр",
    "description": "Центральная часть Москвы...",
    "difficulty": 1,
    "category": "city"
  },
  "statistics": {
    "total_rounds": 0,
    "average_score": 0.0,
    "average_distance_km": 0.0
  },
  "example_point": [37.6173, 55.7558],
  "preview_note": "Для получения реального превью-снимка требуется интеграция с провайдером карт."
}
```

## 🐍 Примеры на Python

### 1. Базовый клиент
```python
import httpx
import asyncio

API_BASE = "http://localhost:8000/api"

async def test_api():
    async with httpx.AsyncClient() as client:
        # Проверка здоровья
        health = await client.get(f"{API_BASE}/health")
        print("Health:", health.json())
        
        # Получить список зон
        zones = await client.get(f"{API_BASE}/zones/")
        print("Zones:", len(zones.json()), "available")
        
        # Начать сессию
        session_resp = await client.post(
            f"{API_BASE}/sessions/start",
            json={"rounds_total": 3}
        )
        session = session_resp.json()
        print("Session started:", session["id"])
        
        # Отправить догадку для первого раунда
        round_id = session["current_round"]["id"]
        guess_resp = await client.post(
            f"{API_BASE}/rounds/{round_id}/guess",
            json={"longitude": 37.6173, "latitude": 55.7558}
        )
        guess_result = guess_resp.json()
        print("Guess result:", guess_result["distance_km"], "km, score:", guess_result["score"])

if __name__ == "__main__":
    asyncio.run(test_api())
```

### 2. Полный игровой цикл
```python
import httpx
import asyncio
import random

class LocationKingClient:
    def __init__(self, base_url="http://localhost:8000/api"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.session_id = None
        
    async def start_game(self, rounds=3):
        """Начать новую игру"""
        resp = await self.client.post(
            f"{self.base_url}/sessions/start",
            json={"rounds_total": rounds}
        )
        resp.raise_for_status()
        session = resp.json()
        self.session_id = session["id"]
        return session
    
    async def submit_guess(self, round_id, lng, lat):
        """Отправить догадку"""
        resp = await self.client.post(
            f"{self.base_url}/rounds/{round_id}/guess",
            json={"longitude": lng, "latitude": lat}
        )
        resp.raise_for_status()
        return resp.json()
    
    async def play_random_game(self):
        """Сыграть случайную игру"""
        print("🎮 Starting random game...")
        
        # Начинаем игру
        session = await self.start_game(rounds=3)
        print(f"Session: {session['id']}")
        
        total_score = 0
        
        # Играем все раунды
        while True:
            current_round = session.get("current_round")
            if not current_round:
                print("No current round, game might be finished")
                break
            
            round_id = current_round["id"]
            zone_name = current_round["zone"]["name"]
            
            print(f"\n🎯 Round {session['rounds_done'] + 1}/{session['rounds_total']}")
            print(f"Zone: {zone_name}")
            
            # Случайная догадка (в реальной игре здесь был бы анализ снимка)
            guess_lng = random.uniform(-180, 180)
            guess_lat = random.uniform(-90, 90)
            
            print(f"Guess: {guess_lng:.4f}, {guess_lat:.4f}")
            
            # Отправляем догадку
            result = await self.submit_guess(round_id, guess_lng, guess_lat)
            
            print(f"Distance: {result['distance_km']:.2f} km")
            print(f"Score: {result['score']}")
            
            total_score += result["score"]
            
            if result["is_session_finished"]:
                print("\n🏁 Game finished!")
                print(f"Total score: {total_score}")
                break
            
            # Обновляем информацию о сессии для следующего раунда
            if result.get("next_round"):
                session["current_round"] = result["next_round"]
                session["rounds_done"] = result["rounds_done"]
                session["total_score"] = result["total_session_score"]
        
        return total_score
    
    async def close(self):
        await self.client.aclose()

async def main():
    client = LocationKingClient()
    try:
        score = await client.play_random_game()
        print(f"\n🎉 Final score: {score}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🐚 Примеры на Bash

### 1. Скрипт для тестирования API
```bash
#!/bin/bash

API_BASE="http://localhost:8000/api"

echo "=== Testing Location King API ==="

# Проверка здоровья
echo -e "\n1. Health check:"
curl -s "$API_BASE/health" | jq .

# Список зон
echo -e "\n2. Available zones:"
curl -s "$API_BASE/zones/" | jq '.[] | {id, name, difficulty}' | head -5

# Начало игры
echo -e "\n3. Starting game..."
SESSION_JSON=$(curl -s -X POST "$API_BASE/sessions/start" \
  -H "Content-Type: application/json" \
  -d '{"rounds_total": 2}')

SESSION_ID=$(echo $SESSION_JSON | jq -r '.id')
ROUND_ID=$(echo $SESSION_JSON | jq -r '.current_round.id')

echo "Session ID: $SESSION_ID"
echo "Round ID: $ROUND_ID"

# Отправка догадки
echo -e "\n4. Submitting guess..."
GUESS_RESULT=$(curl -s -X POST "$API_BASE/rounds/$ROUND_ID/guess" \
  -H "Content-Type: application/json" \
  -d '{"longitude": 37.6173, "latitude": 55.7558}')

echo "Guess result:"
echo $GUESS_RESULT | jq '{distance_km, score, rounds_done, rounds_total}'

# Завершение игры
echo -e "\n5. Finishing game..."
curl -s -X POST "$API_BASE/sessions/$SESSION_ID/finish" | jq .

echo -e "\n=== Test completed ==="
```

## 🔍 Отладка с помощью Swagger UI

Откройте в браузере: http://localhost:8000/api/docs

Swagger UI позволяет:
1. Видеть все доступные эндпоинты
2. Отправлять тестовые запросы прямо из браузера
3. Видеть схемы запросов и ответов
4. Тестировать аутентификацию (когда она будет реализована)

## 🐳 Docker-специфичные запросы

Если используете Docker Compose:

```bash
# Внутри контейнера бэкенда
docker-compose exec backend curl http://localhost:8000/api/health

# С хоста (если порт проброшен)
curl http://localhost:8000/api/health
```

## 📊 Мониторинг и логи

### Логи бэкенда:
```bash
# При запуске через uvicorn
tail -f backend.log  # или смотрите вывод в консоли

# В Docker
docker-compose logs -f backend
```

### Метрики (когда будут добавлены):
```bash
curl http://localhost:8000/metrics
```

## 🚨 Ошибки и их решение

### 1. "Connection refused"
```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```
**Решение:** Убедитесь, что бэкенд запущен.

### 2. "404 Not Found"
```json
{"detail": "Сессия не найдена"}
```
**Решение:** Проверьте правильность ID сессии.

### 3. "422 Unprocessable Entity"
```json
{
  "detail": [
    {
      "type": "float_parsing",
      "loc": ["body", "longitude"],
      "msg": "Input should be a valid number"
    }
  ]
}
```
**Решение:** Проверьте формат данных в запросе.

### 4. "500 Internal Server Error"
**Решение:** Проверьте логи бэкенда для деталей ошибки.

---

**Примечание:** Для работы с космическими снимками нужен Mapbox токен. Добавьте его в `backend/.env` как `MAPBOX_ACCESS_TOKEN=ваш_токен`.

Удачи в тестировании! 🦁