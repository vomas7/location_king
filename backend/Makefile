.PHONY: help install lint format test clean build run

help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  lint       - Run ruff linting"
	@echo "  format     - Format code with ruff"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean cache files"
	@echo "  build      - Build Docker image"
	@echo "  run        - Run application locally"

install:
	pip install -r requirements.txt

lint:
	ruff check app/

format:
	ruff format app/

test:
	pytest tests/ -v

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache .ruff_cache

build:
	docker build -t location-king-backend .

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload