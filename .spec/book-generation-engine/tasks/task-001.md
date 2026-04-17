---
task: 001
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: software-developer-expert
depends_on: []
---

# Task 001: Project Structure, Dependencies, and Supabase Schema

## Skills
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/skills/data-backend/postgres-patterns/SKILL.md
- .kit/rules/common/development-workflow.md
- .kit/rules/python/coding-style.md

## Agents
- @software-developer-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else. Do not load context not listed here.

---

## Objective

Create the complete project scaffolding: directory layout, Python dependencies, Docker Compose for local services, and Supabase migration for the jobs/chapters/artifacts schema.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `pyproject.toml` | Python project config + all dependencies |
| `docker-compose.yml` | Local RabbitMQ + Supabase local services |
| `Makefile` | Dev shortcuts: up, down, migrate, test, lint |
| `app/__init__.py` | Empty package marker |
| `app/main.py` | FastAPI app skeleton (lifespan, router mounts) |
| `app/api/__init__.py` | Empty |
| `app/models/__init__.py` | Empty |
| `app/services/__init__.py` | Empty |
| `app/queue/__init__.py` | Empty |
| `app/ws/__init__.py` | Empty |
| `worker/__init__.py` | Empty |
| `worker/clients/__init__.py` | Empty |
| `worker/pipeline/__init__.py` | Empty |
| `worker/memory/__init__.py` | Empty |
| `frontend/.gitkeep` | Placeholder for Next.js app (created in task-015) |
| `supabase/migrations/001_initial_schema.sql` | Jobs, chapters, artifacts tables + indexes |
| `tests/__init__.py` | Empty |
| `tests/unit/__init__.py` | Empty |
| `tests/integration/__init__.py` | Empty |

---

## Dependencies

```bash
# Install Python deps (create venv first):
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Env vars this task introduces (names only — add values to .env):
# All already defined in .env.example from bootstrap
```

---

## API Contracts

_(none)_

---

## Code Templates

### `pyproject.toml` (create this file exactly)
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "book-generation-engine"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "aio-pika>=9.4.0",
    "supabase>=2.5.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "anthropic>=0.30.0",
    "openai>=1.35.0",
    "google-generativeai>=0.7.0",
    "httpx>=0.27.0",
    "ebooklib>=0.18",
    "reportlab>=4.2.0",
    "python-dotenv>=1.0.0",
    "aiosmtplib>=3.0.0",
    "python-multipart>=0.0.9",
    "websockets>=12.0",
    "cryptography>=42.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "httpx>=0.27.0",
    "anyio>=4.4.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### `docker-compose.yml` (create this file exactly)
```yaml
version: "3.9"
services:
  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  supabase-db:
    image: supabase/postgres:15.1.0.147
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    volumes:
      - supabase-db-data:/var/lib/postgresql/data

volumes:
  supabase-db-data:
```

### `Makefile` (create this file exactly)
```makefile
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
```

### `app/main.py` (create this file exactly)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialise RabbitMQ connection pool, Supabase client
    yield
    # Shutdown: close connections


app = FastAPI(title="Book Generation Engine", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # FILL: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers mounted in later tasks
```

### `supabase/migrations/001_initial_schema.sql` (create this file exactly)
```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued','planning','generating','assembling','complete','failed','paused')),
    config JSONB NOT NULL DEFAULT '{}',
    notification_email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jobs_status ON jobs(status) WHERE status != 'complete';

-- Chapters table
CREATE TABLE IF NOT EXISTS chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    index INTEGER NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','generating','locked','qa_failed')),
    memory_snapshot JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(job_id, index)
);

CREATE INDEX idx_chapters_job_index ON chapters(job_id, index);

-- Artifacts table
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL
        CHECK (artifact_type IN ('epub','pdf','cover','cover_brief','description','metadata','bundle')),
    storage_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_artifacts_job_type ON artifacts(job_id, artifact_type);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER chapters_updated_at BEFORE UPDATE ON chapters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## Codebase Context

> Greenfield project — no existing source to embed. Design decisions below.

### Key Patterns in Use
- **Pydantic v2 models everywhere:** All data validated at boundaries; no raw dicts passed between layers.
- **Async-first FastAPI:** All route handlers are `async def`. Use `asyncio`-compatible libraries only.
- **Supabase via `supabase-py` SDK:** Use `create_client(url, key)` with service role key for backend; anon key only in frontend.
- **No `@` imports:** All skill/agent references use `.kit/...` paths.
- **Config from environment:** Use `pydantic-settings` `BaseSettings` class; never `os.getenv()` directly in business logic.

### Architecture Decisions Affecting This Task
- **ADR-001:** Supabase (Postgres) as primary datastore. Migration via `supabase db push`. Files in `supabase/migrations/`.
- **Workers are stateless:** No in-process state between jobs. All state in Supabase.

---

## Handoff from Previous Task

**Files changed by previous task:** _(none — this is task-001)_
**Decisions made:** _(none yet)_
**Context for this task:** _(none yet)_
**Open questions left:** _(none yet)_

---

## Implementation Steps

1. Create `pyproject.toml` at `C:/Users/Hp/Desktop/Experiment/book-generation-engine/pyproject.toml` — paste template exactly.
2. Create `docker-compose.yml` at `C:/Users/Hp/Desktop/Experiment/book-generation-engine/docker-compose.yml` — paste template exactly.
3. Create `Makefile` at `C:/Users/Hp/Desktop/Experiment/book-generation-engine/Makefile` — paste template exactly.
4. Create all empty `__init__.py` files listed in ## Files: `app/__init__.py`, `app/api/__init__.py`, `app/models/__init__.py`, `app/services/__init__.py`, `app/queue/__init__.py`, `app/ws/__init__.py`, `worker/__init__.py`, `worker/clients/__init__.py`, `worker/pipeline/__init__.py`, `worker/memory/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`.
5. Create `app/main.py` — paste template exactly.
6. Create `supabase/migrations/001_initial_schema.sql` — paste template exactly.
7. Create `frontend/.gitkeep` — empty file.
8. Run: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` — verify zero errors.
9. Run: `docker-compose up -d` — verify rabbitmq and supabase-db containers start healthy.
10. Run: `ruff check app/ worker/` — verify zero lint errors.

---

## Test Cases

### File: `tests/unit/test_project_structure.py`
```python
"""Smoke test: verify all key modules are importable."""
import importlib


def test_app_main_importable():
    mod = importlib.import_module("app.main")
    assert hasattr(mod, "app")


def test_worker_package_importable():
    importlib.import_module("worker")


def test_app_api_package_importable():
    importlib.import_module("app.api")
```

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| `docker-compose up` fails | Check Docker Desktop is running; verify ports 5672 and 5432 are free |
| `pip install` fails on `ebooklib` | Run `pip install ebooklib==0.18` explicitly (pinned version) |
| `ruff check` finds errors | Fix all reported lines; do not disable rules without supervisor approval |

---

## Acceptance Criteria

- [ ] WHEN `docker-compose up -d` runs THEN both `rabbitmq` and `supabase-db` containers are healthy
- [ ] WHEN `pip install -e ".[dev]"` runs THEN zero errors and `import app.main` succeeds
- [ ] WHEN `ruff check app/ worker/` runs THEN zero lint errors
- [ ] WHEN the SQL migration is applied THEN `jobs`, `chapters`, `artifacts` tables exist with correct constraints
- [ ] All existing tests pass

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_
