# Implementation Plan: Book Generation Engine

- [x] 1. Project structure, environment, and Supabase schema
  - Create directory layout: `app/`, `worker/`, `frontend/`, `supabase/migrations/`
  - Write `pyproject.toml` with all Python dependencies (fastapi, uvicorn, aio-pika, supabase-py, pydantic, anthropic, openai, google-generativeai, httpx, ebooklib, reportlab, python-dotenv, pytest, ruff, mypy)
  - Write `docker-compose.yml` for local RabbitMQ + Supabase local
  - Write Supabase migration: `jobs`, `chapters`, `artifacts` tables with indexes
  - Write `.env.example` (already done in bootstrap)
  - _Requirements: 1, 3_
  - _Skills: .kit/skills/languages/python-patterns/SKILL.md, .kit/skills/data-backend/postgres-patterns/SKILL.md_
  - **AC:** `docker-compose up` starts broker and DB. Migration applies without error. All Python imports resolve in a venv.

- [ ] 2. LLMClient abstraction (all providers)
  - Write `worker/clients/llm_client.py`: `LLMClient` class routing to anthropic, openai, google, ollama, openai-compatible
  - Write `UnsupportedProviderError`, `ProviderRateLimitError` exceptions
  - Implement exponential backoff retry (max 3) on rate-limit errors
  - Write unit tests: `tests/unit/test_llm_client.py` — mock all provider SDKs
  - _Requirements: 2_
  - _Skills: .kit/skills/data-science-ml/ai-engineer/SKILL.md, .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** All 5 provider routes covered by tests. Rate-limit retry tested. Unsupported provider raises at construction.

- [ ] 3. ImageClient abstraction (DALL-E 3, Replicate Flux)
  - Write `worker/clients/image_client.py`: `ImageClient` routing to dall-e-3 and replicate-flux
  - Write unit tests: `tests/unit/test_image_client.py` — mock HTTP calls
  - _Requirements: 2_
  - _Skills: .kit/skills/data-science-ml/ai-engineer/SKILL.md_
  - **AC:** Both providers route correctly. Returns `bytes`. Unsupported provider raises `UnsupportedProviderError`.

- [ ] 4. NotebookLM client
  - Write `worker/clients/notebooklm_client.py`: create notebook, add source, trigger generation, fetch summary
  - Implement graceful fallback: if API unavailable, return `None` (caller synthesises via LLM)
  - Write unit tests with mocked HTTP responses
  - _Requirements: 5_
  - _Skills: .kit/skills/ai-platform/notebooklm/SKILL.md_
  - **AC:** Happy path returns summary string. Unavailable API returns None without raising.

- [ ] 5. MemoryStore (fiction + non-fiction variants)
  - Write `worker/memory/store.py`: `MemoryStore` with `update()`, `get()`, `snapshot()` methods
  - Implement `FictionMemory` (tracks characters, timeline, world rules) and `NonFictionMemory` (tracks concepts, frameworks, repetition control) as subclasses
  - Write unit tests
  - _Requirements: 4, 5, 6_
  - _Skills: .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** Snapshot returns consistent dict. Fiction/non-fiction schemas validated.

- [ ] 6. Shared Core engines (Entry Gate, Intent, Audience, Positioning, Blueprint Selector)
  - Write `worker/pipeline/shared_core.py` with 5 engine classes extending `BaseEngine`
  - Entry Gate: validates input, writes `validated_input.json` to Supabase Storage
  - Blueprint Selector: returns `fiction` or `non_fiction` branch
  - Write integration tests with stub LLM responses
  - _Requirements: 3_
  - _Skills: .kit/skills/data-science-ml/ai-engineer/SKILL.md, .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** Pipeline runs Entry Gate → Blueprint Selector in sequence. Mode branching correct. validated_input.json written.

- [ ] 7. Fiction path engines (F1–F7)
  - Write `worker/pipeline/fiction_path.py` with F1–F7 engine classes
  - F7 Story Memory: initialises FictionMemory and persists snapshot to Supabase
  - Write unit tests per engine with stub LLM
  - _Requirements: 4_
  - _Skills: .kit/skills/data-science-ml/ai-engineer/SKILL.md_
  - **AC:** F1–F7 execute in sequence. F7 persists memory. LLM empty response triggers retry then `fiction_planning_failed`.

- [ ] 8. Non-fiction path engines (N1–N5) + NotebookLM integration
  - Write `worker/pipeline/non_fiction_path.py` with N1–N5 engine classes
  - Orchestrate: NotebookLM research → N1–N5 engines
  - N5 Knowledge Memory: initialises NonFictionMemory and persists to Supabase
  - Write unit tests with stubbed NotebookLM (success + fallback)
  - _Requirements: 5_
  - _Skills: .kit/skills/data-science-ml/ai-engineer/SKILL.md, .kit/skills/ai-platform/notebooklm/SKILL.md_
  - **AC:** NotebookLM research runs first. Fallback path exercised in tests. N5 persists memory.

- [ ] 9. Chapter Generator, Continuity Engine, QA Engine, Style Enforcer
  - Write `worker/pipeline/generation.py` with 4 engine classes
  - Implement per-chapter loop: generate → continuity check → QA score → style check → lock or retry (max 2)
  - On lock: call `chapter_service.lock_chapter()` and update MemoryStore snapshot
  - On QA fail after 2 retries: set chapter status `qa_failed`, pause job
  - Emit progress dict (not WebSocket here — runner handles WebSocket)
  - Write unit tests covering: happy path lock, QA fail retry, QA fail exhaust
  - _Requirements: 6_
  - _Skills: .kit/skills/data-science-ml/ai-engineer/SKILL.md, .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** Chapter locked after passing QA. 2 retries on fail. `qa_failed` status set after exhaustion. Memory updated per chapter.

- [ ] 10. Final Assembly, Packaging, Cover, and Formatting engines
  - Write `worker/pipeline/assembly.py` with 4 engine classes
  - Final Assembly: concatenate locked chapters → `manuscript_final.txt` in Supabase Storage
  - Packaging Engine: produce `description.txt` + `metadata.json` via LLM
  - Cover Engine: produce `cover-brief.txt` via LLM + `cover.jpg` via ImageClient
  - Formatting Engine: produce `manuscript.epub` (ebooklib) + `manuscript.pdf` (ReportLab)
  - Bundle zip and upload to Supabase Storage; update job status to `complete`
  - Write unit tests with stub LLM + stub ImageClient
  - _Requirements: 7_
  - _Skills: .kit/skills/data-science-ml/ai-engineer/SKILL.md, .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** All 6 artifacts exist in Supabase Storage after assembly. Job status = `complete`. Zip bundle downloadable.

- [ ] 11. Pipeline runner and RabbitMQ worker
  - Write `worker/pipeline/runner.py`: orchestrates shared core → branch path → chapter loop → assembly
  - Emit progress events via a callback (injected by worker main)
  - Write `worker/main.py`: connect to RabbitMQ, consume jobs, call runner, broadcast WebSocket events
  - Write `app/queue/publisher.py`: publish job message with job_id + config
  - Write integration test: worker consumes a stub job and calls runner
  - _Requirements: 1, 3, 4, 5, 6, 7_
  - _Skills: .kit/skills/devops/terminal-cli-devops/SKILL.md, .kit/skills/agents-orchestration/agent-orchestrator/SKILL.md_
  - **AC:** Worker starts, consumes job, calls all pipeline stages in correct order. Progress events emitted. Job status updated at each stage.

- [ ] 12. FastAPI backend — jobs and WebSocket
  - Write `app/main.py`, `app/api/jobs.py`, `app/ws/manager.py`
  - `POST /v1/jobs`: validate with Pydantic, create DB record, publish to RabbitMQ, return job_id + ws URL
  - `GET /v1/jobs/{job_id}`: return job status + config (redact API keys in response)
  - `WS /v1/ws/{job_id}`: accept connection, register in manager, broadcast events from worker
  - Write integration tests for all endpoints
  - _Requirements: 1, 6_
  - _Skills: .kit/skills/frameworks-backend/python-fastapi-development/SKILL.md, .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** POST /v1/jobs returns 201 with job_id. GET returns status. WebSocket client receives progress events. API keys not in GET response.

- [ ] 13. FastAPI backend — chapters and export
  - Write `app/api/chapters.py`, `app/api/export.py`
  - `GET /v1/jobs/{id}/chapters`: list chapters with status + content
  - `PUT /v1/chapters/{id}`: update content (unlocked chapters only)
  - `POST /v1/chapters/{id}/lock`: lock chapter
  - `POST /v1/chapters/{id}/regenerate`: publish regenerate task to RabbitMQ
  - `GET /v1/jobs/{id}/export`: return signed URL for zip bundle
  - Write integration tests
  - _Requirements: 10, 11_
  - _Skills: .kit/skills/frameworks-backend/python-fastapi-development/SKILL.md_
  - **AC:** All 5 endpoints return correct status codes. Locked chapter rejects PUT. Export returns signed URL only when job=complete.

- [ ] 14. Email delivery service
  - Write `app/services/email_service.py`: SMTP client, `send_completion_email(email, download_url)`
  - Implement retry once on failure after 60s; log failure without failing the job
  - Write unit tests with mocked SMTP
  - _Requirements: 8_
  - _Skills: .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** Email sends on job complete. SMTP failure logs error and retries once. Job status unaffected.

- [ ] 15. React/Next.js frontend — Job Creator
  - Scaffold Next.js app in `frontend/`
  - Write `JobCreatorForm` component: all fields, provider config panel, submit handler
  - On submit success: navigate to `/jobs/{id}`
  - Display inline validation errors from API 422 response
  - Write component tests (Jest/React Testing Library)
  - _Requirements: 9_
  - _Skills: .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** Form submits to POST /v1/jobs. 422 errors shown inline. Navigation to Book Editor on success.

- [ ] 16. React/Next.js frontend — Book Editor
  - Write `BookEditorView`, `ChapterCard`, `InlineEditor`, `ProgressBar` components
  - Connect WebSocket to `/v1/ws/{job_id}` and update state on `progress` and `chapter_ready` events
  - Inline edit saves on blur via PUT /v1/chapters/{id}
  - Regenerate button: POST to regenerate endpoint + loading state
  - Lock button: POST to lock endpoint + visual update
  - Write component tests
  - _Requirements: 10_
  - _Skills: .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** Progress bar updates on WebSocket events. Chapter content editable and saves. Regenerate triggers API call. Lock disables editor.

- [ ] 17. React/Next.js frontend — Export View
  - Write `ExportView` component: file list, StatusBadge, download button
  - Download button links to signed URL from GET /v1/jobs/{id}/export
  - Show file list: manuscript.epub, manuscript.pdf, cover.jpg, cover-brief.txt, description.txt, metadata.json
  - Write component tests
  - _Requirements: 11_
  - _Skills: .kit/skills/languages/python-patterns/SKILL.md_
  - **AC:** Export view visible when job=complete. Download button triggers browser download. File list correct.

- [ ] 18. End-to-end test and CI pipeline
  - Write e2e test: submit fiction job with stub LLM provider → poll until complete → verify all artifacts exist
  - Write GitHub Actions workflow: ruff lint → mypy → pytest → e2e test → Docker build
  - _Requirements: 1–11_
  - _Skills: .kit/skills/testing-quality/tdd-workflow/SKILL.md, .kit/skills/devops/terminal-cli-devops/SKILL.md_
  - **AC:** E2E test passes with stub provider. CI workflow green on main branch push.
