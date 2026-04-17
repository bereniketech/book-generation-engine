.PHONY: up down migrate test lint type-check

up:
	docker-compose up -d

down:
	docker-compose down

migrate:
	supabase db push

test:
	pytest tests/ -v --cov=app --cov=worker --cov-report=term-missing

lint:
	ruff check app/ worker/ tests/

type-check:
	mypy app/ worker/
