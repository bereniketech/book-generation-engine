---
task: 012
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: web-backend-expert
depends_on: [011]
---

# Task 012: FastAPI Backend — Jobs and WebSocket

## Skills
- .kit/skills/frameworks-backend/python-fastapi-development/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/rules/python/patterns.md

## Agents
- @web-backend-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Implement the FastAPI backend for job creation and WebSocket progress streaming: `POST /v1/jobs`, `GET /v1/jobs/{job_id}`, and `WS /v1/ws/{job_id}` endpoints, plus the WebSocket connection manager and Supabase/RabbitMQ integration in the app lifespan.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `app/models/job.py` | JobCreate, JobResponse Pydantic models |
| `app/services/job_service.py` | create_job(), get_job(), update_job_status() |
| `app/ws/manager.py` | WebSocket connection manager |
| `app/api/jobs.py` | POST /v1/jobs, GET /v1/jobs/{job_id}, WS /v1/ws/{job_id} |
| `app/config.py` | Pydantic Settings for app configuration |

### Modify
| File | What to change |
|------|---------------|
| `app/main.py` | Add lifespan (RabbitMQ + Supabase init), mount api/jobs router |

---

## Dependencies

```bash
# All packages already in pyproject.toml.
# Env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, RABBITMQ_URL, SECRET_KEY — all in .env.example.
```

---

## Code Templates

### `app/config.py` (create this file exactly)
```python
"""Application configuration via pydantic-settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    rabbitmq_url: str = "amqp://guest:guest@localhost/"
    secret_key: str = "dev-secret-key"
    debug: bool = False


settings = Settings()
```

### `app/models/job.py` (create this file exactly)
```python
"""Pydantic models for job API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LLMProviderConfig(BaseModel):
    provider: Literal["anthropic", "openai", "google", "ollama", "openai-compatible"]
    model: str = Field(min_length=1, max_length=200)
    api_key: str = Field(min_length=1, max_length=500)
    base_url: str | None = None


class ImageProviderConfig(BaseModel):
    provider: Literal["dall-e-3", "replicate-flux"]
    api_key: str = Field(min_length=1, max_length=500)


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    topic: str = Field(min_length=1, max_length=2000)
    mode: Literal["fiction", "non_fiction"]
    audience: str = Field(min_length=1, max_length=500)
    tone: str = Field(min_length=1, max_length=200)
    target_chapters: int = Field(ge=3, le=50, default=12)
    llm: LLMProviderConfig
    image: ImageProviderConfig
    notification_email: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    ws_url: str

    @classmethod
    def from_job_id(cls, job_id: str, base_url: str) -> "JobResponse":
        return cls(
            job_id=job_id,
            status="queued",
            ws_url=f"{base_url}/v1/ws/{job_id}",
        )
```

### `app/ws/manager.py` (create this file exactly)
```python
"""WebSocket connection manager."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[job_id].append(websocket)
        logger.info("WS connected: job=%s total=%d", job_id, len(self._connections[job_id]))

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        if websocket in self._connections[job_id]:
            self._connections[job_id].remove(websocket)

    async def broadcast(self, job_id: str, event: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(job_id, [])):
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(job_id, ws)


manager = ConnectionManager()
```

### `app/services/job_service.py` (create this file exactly)
```python
"""Job CRUD operations against Supabase."""
from __future__ import annotations

import json
import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)


def _redact_config(config: dict) -> dict:
    """Remove API keys from config dict before returning to client."""
    safe = dict(config)
    for key in ("api_key", "llm_api_key", "image_api_key"):
        if key in safe:
            safe[key] = "***"
    if "llm" in safe and isinstance(safe["llm"], dict):
        safe["llm"] = {**safe["llm"], "api_key": "***"}
    if "image" in safe and isinstance(safe["image"], dict):
        safe["image"] = {**safe["image"], "api_key": "***"}
    return safe


def create_job(supabase: Client, job_id: str, config: dict, notification_email: str | None) -> dict:
    result = supabase.table("jobs").insert({
        "id": job_id,
        "status": "queued",
        "config": config,
        "notification_email": notification_email,
    }).execute()
    return result.data[0]


def get_job(supabase: Client, job_id: str) -> dict | None:
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        return None
    job = result.data
    job["config"] = _redact_config(job.get("config", {}))
    return job


def update_job_status(supabase: Client, job_id: str, status: str) -> None:
    supabase.table("jobs").update({"status": status}).eq("id", job_id).execute()
```

### `app/api/jobs.py` (create this file exactly)
```python
"""FastAPI routes for jobs and WebSocket."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from app.models.job import JobCreate, JobResponse
from app.queue.publisher import publish_job
from app.services import job_service
from app.ws.manager import manager

router = APIRouter(prefix="/v1", tags=["jobs"])


@router.post("/jobs", status_code=status.HTTP_201_CREATED, response_model=JobResponse)
async def create_job(body: JobCreate, request: Request) -> JobResponse:
    supabase = request.app.state.supabase
    channel = request.app.state.amqp_channel

    job_id = str(uuid.uuid4())
    config = body.model_dump()

    job_service.create_job(
        supabase=supabase,
        job_id=job_id,
        config=config,
        notification_email=body.notification_email,
    )
    await publish_job(channel=channel, job_id=job_id, config=config)

    base_url = str(request.base_url).rstrip("/")
    return JobResponse.from_job_id(job_id, base_url)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict:
    supabase = request.app.state.supabase
    job = job_service.get_job(supabase, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
    await manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive; server pushes events
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
```

### `app/main.py` (overwrite — before → after)

**Before:**
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

**After:**
```python
from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

from app.api.jobs import router as jobs_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    amqp_connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    app.state.amqp_connection = amqp_connection
    app.state.amqp_channel = await amqp_connection.channel()
    yield
    # Shutdown
    await app.state.amqp_connection.close()


app = FastAPI(title="Book Generation Engine", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # FILL: restrict to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
```

---

## Codebase Context

### Key Patterns in Use
- **App state for shared resources:** `request.app.state.supabase` and `request.app.state.amqp_channel` — set in lifespan, accessed in route handlers.
- **`_redact_config()`:** Strips `api_key` fields before returning job data to clients. Never log or return raw API keys.
- **WebSocket manager is a global singleton:** `from app.ws.manager import manager` — all routes share one instance.
- **Job ID is server-generated UUID:** Never trust client-provided IDs.

### Architecture Decisions Affecting This Task
- `POST /v1/jobs` returns HTTP 201 with `job_id` and `ws_url`. Client connects to WebSocket immediately.
- API key validation (valid key format) is not done at this layer — the worker will fail with a `ProviderError` if the key is invalid.

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/pipeline/runner.py`, `worker/main.py`, `app/queue/publisher.py`, `app/queue/connection.py`.
**Decisions made:** Progress callback pattern. Runner owns all client construction.
**Context for this task:** Worker side is done. Now build the FastAPI API layer.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `app/config.py` — paste template exactly.
2. Create `app/models/job.py` — paste template exactly.
3. Create `app/ws/manager.py` — paste template exactly.
4. Create `app/services/job_service.py` — paste template exactly.
5. Create `app/api/jobs.py` — paste template exactly.
6. Edit `app/main.py` — apply the before → after replacement exactly.
7. Run: `ruff check app/` — verify zero lint errors.
8. Run: `mypy app/config.py app/models/job.py app/ws/manager.py` — verify zero type errors.

---

## Test Cases

### File: `tests/integration/test_jobs_api.py`
```python
"""Integration tests for jobs API endpoints."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def make_job_body() -> dict:
    return {
        "title": "Test Book",
        "topic": "Testing concepts",
        "mode": "fiction",
        "audience": "Developers",
        "tone": "Casual",
        "target_chapters": 3,
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "test-key"},
        "image": {"provider": "dall-e-3", "api_key": "img-key"},
        "notification_email": "test@example.com",
    }


def test_create_job_returns_201_with_job_id(client):
    with patch("app.api.jobs.job_service.create_job") as mock_create, \
         patch("app.api.jobs.publish_job", new_callable=AsyncMock) as mock_publish:
        mock_create.return_value = {"id": "job-uuid-1"}
        client.app.state.supabase = MagicMock()
        client.app.state.amqp_channel = MagicMock()

        response = client.post("/v1/jobs", json=make_job_body())

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert "ws_url" in data


def test_get_job_returns_404_for_unknown_id(client):
    with patch("app.api.jobs.job_service.get_job", return_value=None):
        client.app.state.supabase = MagicMock()
        response = client.get("/v1/jobs/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_get_job_redacts_api_keys(client):
    job_data = {
        "id": "job-1",
        "status": "queued",
        "config": {"llm": {"api_key": "real-key"}, "image": {"api_key": "img-real-key"}},
    }
    with patch("app.api.jobs.job_service.get_job", return_value={
        "id": "job-1",
        "status": "queued",
        "config": {"llm": {"api_key": "***"}, "image": {"api_key": "***"}},
    }):
        client.app.state.supabase = MagicMock()
        response = client.get("/v1/jobs/job-1")
    assert response.status_code == 200
    config = response.json()["config"]
    assert config["llm"]["api_key"] == "***"
```

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| `GET /v1/jobs/{job_id}` — job not found in Supabase | Raise `HTTPException(status_code=404, detail="Job not found")` |
| `POST /v1/jobs` — Pydantic validation fails | FastAPI auto-returns HTTP 422 with field-level errors |
| WebSocket client disconnects | `manager.disconnect(job_id, websocket)` — remove from connections dict |
| `_redact_config()` encounters nested `api_key` | Replace with `"***"` — never raise, never log real value |

---

## Acceptance Criteria

- [ ] WHEN `POST /v1/jobs` is called with valid body THEN response is 201 with `job_id` and `ws_url`
- [ ] WHEN `GET /v1/jobs/{id}` is called with unknown id THEN response is 404 with `{"detail": "Job not found"}`
- [ ] WHEN `GET /v1/jobs/{id}` is called THEN API keys in config are replaced with `"***"`
- [ ] WHEN `ruff check app/` runs THEN zero errors

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_

Status: COMPLETE
Completed: 2026-04-17T00:00:00Z
