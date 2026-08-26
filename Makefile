.PHONY: help dev dev-build down down-v logs ps migrate seed shell-backend shell-db \
        prod prod-down lint test cov

help:
	@echo "Разработка:"
	@echo "  dev          — поднять окружение разработки (http://localhost:8080)"
	@echo "  dev-build    — то же с пересборкой образов"
	@echo "  migrate      — накатить миграции"
	@echo "  seed         — загрузить игровые зоны"
	@echo "  lint         — ruff check и ruff format --check"
	@echo "  test         — pytest"
	@echo "  cov          — pytest с отчётом о покрытии"
	@echo "  down         — остановить (down-v — вместе с данными)"
	@echo ""
	@echo "Прод:"
	@echo "  prod         — собрать и поднять прод-контур"
	@echo "  prod-down    — остановить прод-контур"
	@echo "  logs, ps     — логи и статус"

# ─── Разработка ───────────────────────────────────────────────────────
DEV := docker compose -f docker-compose.dev.yml

dev:
	$(DEV) up -d
	@echo "Игра: http://localhost:8080   API: http://localhost:8000/api/docs"

dev-build:
	$(DEV) up -d --build

migrate:
	$(DEV) exec backend alembic upgrade head

seed:
	$(DEV) exec backend python scripts/seed.py

shell-backend:
	$(DEV) exec backend bash

shell-db:
	$(DEV) exec postgres psql -U locationking -d location_king

down:
	$(DEV) down

down-v:
	$(DEV) down -v

logs:
	$(DEV) logs -f

ps:
	$(DEV) ps

# ─── Проверки (без Docker, из backend/) ───────────────────────────────
lint:
	$(MAKE) -C backend lint

test:
	$(MAKE) -C backend test

cov:
	$(MAKE) -C backend cov

# ─── Прод ─────────────────────────────────────────────────────────────
prod:
	docker compose up -d --build

prod-down:
	docker compose down
