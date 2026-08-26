.PHONY: help install lint format fix test cov migrate seed run

help:
	@echo "install  — поставить зависимости для разработки"
	@echo "lint     — ruff check"
	@echo "format   — ruff format"
	@echo "fix      — ruff check --fix и ruff format"
	@echo "test     — pytest"
	@echo "cov      — pytest с отчётом о покрытии"
	@echo "migrate  — alembic upgrade head"
	@echo "seed     — загрузить игровые зоны"
	@echo "run      — uvicorn с автоперезагрузкой"

install:
	pip install -r requirements-dev.txt

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

fix:
	ruff check --fix .
	ruff format .

test:
	pytest -v

cov:
	pytest --cov=app --cov-report=term-missing

migrate:
	alembic upgrade head

seed:
	python scripts/seed.py

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
