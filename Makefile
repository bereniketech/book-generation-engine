.PHONY: up down migrate test lint type-check schema schema-check

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

schema:
	python scripts/generate_schema.py

schema-check:
	python scripts/generate_schema.py && git diff --exit-code frontend/lib/generated/job_schema.ts || (echo "ERROR: Schema out of sync. Run 'make schema' and commit changes." && exit 1)
