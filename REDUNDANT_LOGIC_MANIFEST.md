# Redundant Logic Manifest
**Book Generation Engine — Architecture & Logic Centralization Review**
**Review Date:** 2026-04-24
**Reviewer Role:** Senior Software Engineer / Code Reviewer
**Scope:** Full-stack logic placement, separation of concerns, modularity, and duplication analysis

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Layer Map](#2-system-layer-map)
3. [Correctly Placed Logic — Confirmed](#3-correctly-placed-logic--confirmed)
4. [Redundant or Misplaced Logic — Flagged](#4-redundant-or-misplaced-logic--flagged)
5. [Recommendations for Consolidation](#5-recommendations-for-consolidation)
6. [Overall Adherence Assessment](#6-overall-adherence-assessment)

---

## 1. Executive Summary

The book generation engine is a well-structured, multi-layered system with clear separation between its domain, service, API, worker, and frontend layers. The pipeline engine design is particularly strong — business logic is encapsulated in discrete, pluggable engine classes within the worker, the domain layer contains pure state transition and validation logic, and the API layer is mostly a thin HTTP orchestration shell.

However, **three structural violations** undermine the principle of a single source of truth for business logic:

| Severity | Issue | Location |
|----------|-------|----------|
| **HIGH** | Validation logic duplicated verbatim between backend and frontend | `app/domain/validation_schemas.py` ↔ `frontend/lib/validation.ts` |
| **HIGH** | Job creation logic scattered across multiple routes | `app/api/jobs.py`, `app/api/batch.py`, `app/api/templates.py` |
| **MEDIUM** | Email body template embedded in service class | `app/services/email_service.py` |
| **MEDIUM** | Cover revision audit state stored in wrong data structure | `app/api/cover.py` |
| **MEDIUM** | Batch row schema is a strict subset of the canonical job schema | `app/api/batch.py` ↔ `app/domain/validation_schemas.py` |
| **LOW** | Default model name hardcoded in React component | `frontend/components/JobCreatorForm.tsx` |
| **LOW** | Chapter preview truncation limit hardcoded in API route | `app/api/chapters.py` |

---

## 2. System Layer Map

```
┌─────────────────────────────────────────────────────┐
│  FRONTEND (Next.js / React)                         │
│  Responsibility: Presentation only                  │
│  Files: frontend/app/**, frontend/components/**     │
│         frontend/lib/api.ts, frontend/hooks/**      │
├─────────────────────────────────────────────────────┤
│  API LAYER (FastAPI routes)                         │
│  Responsibility: HTTP translation, orchestration    │
│  Files: app/api/**                                  │
├─────────────────────────────────────────────────────┤
│  SERVICE LAYER                                      │
│  Responsibility: Business operations, CRUD, I/O     │
│  Files: app/services/**                             │
├─────────────────────────────────────────────────────┤
│  DOMAIN LAYER                                       │
│  Responsibility: Pure business rules, state logic   │
│  Files: app/domain/state_machine.py                 │
│         app/domain/validation_schemas.py            │
├─────────────────────────────────────────────────────┤
│  WORKER LAYER (RabbitMQ consumer)                   │
│  Responsibility: Book generation pipeline           │
│  Files: worker/pipeline/**, worker/clients/**       │
│         worker/memory/**, worker/main.py            │
├─────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                     │
│  Responsibility: Adapters, cross-cutting concerns   │
│  Files: app/infrastructure/**, app/queue/**         │
│         app/config.py, app/core/**                  │
└─────────────────────────────────────────────────────┘
```

**Frontend/Backend boundary:** The frontend must not perform business logic decisions. It may perform UX-optimistic validation (i.e., show errors before network round-trip) **only if that validation is derived from the backend as a single source of truth.**

---

## 3. Correctly Placed Logic — Confirmed

The following logic placements are architecturally correct and adhere to separation-of-concerns principles.

### 3.1 Domain Layer — State Machine (`app/domain/state_machine.py`)

**Status: CORRECT**

All job and cover lifecycle transition rules are defined exclusively in `JobStateMachine` and `CoverStateMachine`. The `VALID_TRANSITIONS` table is the single authoritative definition of what state changes are legal. No other layer re-implements this logic.

```
JobStateMachine.VALID_TRANSITIONS = {
    JobStatus.QUEUED: {JobStatus.GENERATING, ...},
    ...
}
```

Routes that trigger state changes (`/pause`, `/resume`, `/cancel`, `/approve`) all call `JobStateMachine.transition()` and map the resulting `InvalidStateTransitionError` to HTTP 409. This is the correct pattern.

### 3.2 Domain Layer — Validation Schema (`app/domain/validation_schemas.py`)

**Status: CORRECT PLACEMENT, but DUPLICATED (see Section 4.1)**

Business constraints on job fields (title length, chapter count, temperature range) are declared as a Pydantic `JobCreateRequest` model in the domain layer. The placement is correct — this is the right location. The problem is that an identical copy exists in the frontend (see issue #1).

### 3.3 Service Layer — Chapter Lock (`app/services/chapter_service.py`)

**Status: CORRECT**

The rule "a locked chapter cannot be modified" is enforced in `update_chapter_content()` before the DB write. This guard is in exactly one place:

```python
# app/services/chapter_service.py
if chapter["locked"]:
    raise ChapterLockedError(chapter_index)
```

No route or frontend component re-implements this check.

### 3.4 Service Layer — Sensitive Field Redaction (`app/infrastructure/security.py`)

**Status: CORRECT**

The `redact_sensitive_fields()` function is the sole location for determining which fields are sensitive (`api_key`, `password`, `token`, `secret`, etc.) and replacing them with `"***REDACTED***"`. All API responses that include job config pass through this function. The frontend receives only already-redacted data.

### 3.5 Service Layer — Progress Broadcasting (`app/services/progress.py`)

**Status: CORRECT**

All progress event publishing passes through `publish_progress()`. The pipeline runner uses this function exclusively; no worker engine directly writes to Redis. The frontend consumes events passively via WebSocket without interpreting or recalculating progress percentages.

### 3.6 Worker Layer — LLM and Image Client Abstraction (`worker/clients/`)

**Status: CORRECT**

Provider-specific SDK calls (Anthropic, OpenAI, Replicate, Google) are encapsulated entirely within `LLMClient` and `ImageClient`. No pipeline engine imports a provider SDK directly. The single `complete()` / `generate()` interface shields all engines from provider implementation details, retry logic, and token tracking.

### 3.7 Worker Layer — Pipeline Orchestration (`worker/pipeline/runner.py`)

**Status: CORRECT**

The branching decision between the fiction path and the non-fiction path is made once, inside `PipelineRunner`, based on the `genre` field of `JobConfig`. No route, service, or frontend component contains genre-based conditional logic.

```python
# worker/pipeline/runner.py
if job_config.genre in FICTION_GENRES:
    await self._run_fiction_path(ctx)
else:
    await self._run_non_fiction_path(ctx)
```

### 3.8 Worker Layer — QA Scoring Threshold (`worker/pipeline/generation.py`)

**Status: CORRECT**

The minimum acceptable QA score (6/10) and the max chapter retry count (`MAX_CHAPTER_RETRIES = 2`) are defined once in `runner.py` and `generation.py` respectively. The frontend only displays a score value; it makes no pass/fail decisions.

### 3.9 Infrastructure — HTTP Error Envelope (`app/infrastructure/http_exceptions.py`)

**Status: CORRECT**

The error response shape `{"error": string, "code": string}` is defined in one place. The frontend `api.ts` parses this shape via `handleApiError()` — it reads the backend's definition, it does not define one of its own.

### 3.10 Infrastructure — Configuration (`app/config.py`)

**Status: CORRECT**

All environment-sensitive values (Supabase URL, SMTP credentials, RabbitMQ URL, CORS origin) are read exactly once via `pydantic-settings`. No route or service directly reads `os.environ`. The `Settings` instance is imported by modules that need it.

---

## 4. Redundant or Misplaced Logic — Flagged

---

### Issue #1 — VALIDATION LOGIC DUPLICATED BETWEEN BACKEND AND FRONTEND

**Severity: HIGH**
**Principle Violated:** Single Source of Truth for Business Rules

#### Locations

| Instance | File | Lines |
|----------|------|-------|
| **Source of truth** | `app/domain/validation_schemas.py` | Full file |
| **Duplicate** | `frontend/lib/validation.ts` | Full file |

#### Description

The field constraints that govern job creation are defined twice — once as Pydantic models (Python) and once as Zod schemas (TypeScript). Both files contain the same numeric limits:

```python
# app/domain/validation_schemas.py
title: str = Field(..., min_length=1, max_length=500)
topic: str = Field(..., min_length=1, max_length=2000)
num_chapters: int = Field(..., ge=3, le=50)
temperature: float = Field(0.7, ge=0.0, le=1.0)
```

```typescript
// frontend/lib/validation.ts
title: z.string().min(1).max(500),
topic: z.string().min(1).max(2000),
num_chapters: z.number().int().min(3).max(50),
temperature: z.number().min(0).max(1),
```

Both files contain the comment: *"Constraints here MUST match [the other file] exactly. When changing limits, update both files simultaneously."*

This comment is an admission of duplication. Manual synchronization is error-prone: a developer who changes a limit in one file without updating the other will produce a frontend that accepts values the backend rejects (or vice versa), with no automated enforcement.

#### Impact

- A business rule change (e.g., raising the max chapter count) requires edits in two files across two languages.
- If synchronization lapses, users see confusing silent failures: the frontend form submits, the backend rejects, and no clear validation error is shown.
- The "source of truth" cannot be definitively identified from code alone.

#### Recommendation

See Section 5, Recommendation #1.

---

### Issue #2 — JOB CREATION LOGIC FRAGMENTED ACROSS MULTIPLE ROUTES

**Severity: HIGH**
**Principle Violated:** DRY / Single Responsibility

#### Locations

| Instance | File | Route |
|----------|------|-------|
| **Canonical** | `app/api/jobs.py` | `POST /v1/jobs` |
| **Duplicate A** | `app/api/jobs.py` | `POST /v1/jobs/{template_id}/create` |
| **Duplicate B** | `app/api/batch.py` | `POST /batch` (per-row creation) |
| **Duplicate C** | `app/api/batch.py` | `POST /batch/csv` (per-row creation) |

#### Description

The act of creating a job — validating config, inserting a DB record, enqueuing a RabbitMQ message — happens in at least four code paths. The template-based creation route in `jobs.py` has its own config-merging logic that differs from the canonical `POST /v1/jobs` path. The batch routes use a `JobConfigSchema` that only validates `title` and `genre`, skipping the full `JobCreateRequest` validation entirely.

#### Impact

- A change to job creation business rules (e.g., adding a mandatory new field) must be replicated in all four paths.
- Batch jobs bypass full validation, so invalid LLM/image configurations are only caught at pipeline execution time, surfacing as cryptic worker failures rather than clean API validation errors.
- The template merge strategy is defined inline and untested in isolation.

#### Recommendation

See Section 5, Recommendation #2.

---

### Issue #3 — EMAIL BODY TEMPLATE EMBEDDED IN SERVICE CLASS

**Severity: MEDIUM**
**Principle Violated:** Separation of Content from Logic

#### Location

| Instance | File | Lines |
|----------|------|-------|
| **Violation** | `app/services/email_service.py` | ~49–65 |

#### Description

The email notification content (plain-text body and HTML body) is constructed as multi-line f-string literals inside the `_send()` method of `EmailService`. This couples the presentation content of the email with the delivery mechanism.

```python
# app/services/email_service.py
plain = f"Your book '{title}' is ready.\nDownload: {url}"
html  = f"<h1>{title}</h1><p>Download: <a href='{url}'>{url}</a></p>"
```

#### Impact

- Changing the email wording requires a code edit, not a content edit.
- HTML email content cannot be previewed or tested independently of the service.
- Multi-language or white-label use cases are harder to support.

#### Recommendation

See Section 5, Recommendation #3.

---

### Issue #4 — COVER REVISION FEEDBACK STORED IN JOB CONFIG (WRONG DATA STRUCTURE)

**Severity: MEDIUM**
**Principle Violated:** Data Integrity / Audit Trail

#### Location

| Instance | File | Route |
|----------|------|-------|
| **Violation** | `app/api/cover.py` | `POST /jobs/{job_id}/cover/revise` |

#### Description

When a user requests a cover revision, the feedback text is written into the `job.config` JSON column:

```python
# app/api/cover.py
await supabase.table("jobs").update({
    "config": {**job["config"], "cover_revision_feedback": feedback}
}).eq("id", job_id).execute()
```

This overwrites any previous revision feedback (only one revision can ever be "on record" at a time), does not record who requested it or when, and conflates pipeline configuration with operational audit data. The `job.config` column is intended to hold the original generation parameters, not a running log of user interactions.

#### Impact

- Revision history is lost: each new revision request silently replaces the previous feedback.
- `job.config` is propagated to the worker as generation parameters — revision feedback leaks into pipeline context where it may or may not be used intentionally.
- No timestamp or identity is recorded with the feedback.

#### Recommendation

See Section 5, Recommendation #4.

---

### Issue #5 — BATCH ROW VALIDATION IS A STRICT SUBSET OF CANONICAL JOB VALIDATION

**Severity: MEDIUM**
**Principle Violated:** Single Source of Truth for Business Rules

#### Locations

| Instance | File | Schema Used |
|----------|------|-------------|
| **Canonical** | `app/domain/validation_schemas.py` | `JobCreateRequest` (full schema) |
| **Reduced copy** | `app/api/batch.py` | `JobConfigSchema` (title + genre only) |

#### Description

The batch submission endpoints accept a `JobConfigSchema` that only requires `title` and `genre`. All other job fields — `num_chapters`, `temperature`, `llm_provider`, `image_provider`, `topic` — are unvalidated on ingestion. They are stored and enqueued as-is, and validation only occurs when the worker attempts to construct a `JobConfig` from the message payload. By that point, the error surfaces as a worker failure rather than an API validation error, and the job is moved to the dead-letter queue.

#### Impact

- Bad batch rows produce confusing DLQ failures instead of clean 400 responses at submission time.
- Operators must inspect the DLQ to understand why a batch job failed, rather than seeing an immediate validation error.
- The batch path effectively has a different (weaker) contract than the single-job path for the same underlying operation.

#### Recommendation

See Section 5, Recommendation #5.

---

### Issue #6 — DEFAULT MODEL NAME HARDCODED IN REACT COMPONENT

**Severity: LOW**
**Principle Violated:** Configuration Belongs in Backend

#### Location

| Instance | File | Line |
|----------|------|------|
| **Violation** | `frontend/components/JobCreatorForm.tsx` | ~25 |

#### Description

The default LLM model name is hardcoded in the frontend React component:

```typescript
// frontend/components/JobCreatorForm.tsx
defaultValues: { model: "claude-sonnet-4-6" }
```

The backend exposes a `/v1/config/providers` endpoint precisely to communicate available providers and their defaults to the frontend. The frontend ignores this for default initialization and instead hard-codes a specific model version string.

#### Impact

- When the backend's supported model list changes (e.g., a model is deprecated or a new default is set), the frontend does not automatically reflect this.
- A stale model name in the frontend form will either be silently accepted (producing unexpected behavior) or rejected by the backend with a cryptic validation error.

#### Recommendation

See Section 5, Recommendation #6.

---

### Issue #7 — CHAPTER PREVIEW TRUNCATION LIMIT HARDCODED IN API ROUTE

**Severity: LOW**
**Principle Violated:** Magic Numbers Belong in Domain Constants

#### Location

| Instance | File | Line |
|----------|------|------|
| **Violation** | `app/api/chapters.py` | ~41 |

#### Description

The character count used to generate chapter previews is a hard-coded integer literal in the route handler:

```python
# app/api/chapters.py
"preview": chapter["content"][:200]
```

#### Impact

- The number `200` is a business decision (how much content to expose in a list view) but is expressed as an anonymous magic number inside HTTP routing code.
- Changing it requires finding this specific line; it is not discoverable as a named constant.
- There is no word-boundary awareness, so previews may truncate mid-word.

#### Recommendation

See Section 5, Recommendation #7.

---

## 5. Recommendations for Consolidation

---

### Recommendation #1 — Eliminate Validation Duplication via Schema Endpoint

**Addresses:** Issue #1

**Approach:** Promote the backend Python schema as the single source of truth and derive the frontend Zod schema from it programmatically rather than maintaining it manually.

**Option A — Code Generation (Preferred):**
Use `pydantic-to-typescript` or a custom script to emit a TypeScript types file and a Zod schema from `JobCreateRequest` at build time. The frontend imports the generated schema instead of maintaining its own copy. A CI step regenerates and diffs the output, failing the build if the schema is stale.

```
# Build step (makefile / CI)
python scripts/generate_schema.py \
  --model app.domain.validation_schemas.JobCreateRequest \
  --out frontend/lib/generated/job_schema.ts
```

**Option B — Runtime Schema Endpoint:**
Extend `/v1/config` to return the field constraints as JSON:

```json
{
  "job_constraints": {
    "title": {"min": 1, "max": 500},
    "num_chapters": {"min": 3, "max": 50},
    ...
  }
}
```

The frontend fetches this once on mount and constructs Zod refinements dynamically. Validation is always consistent with the backend without a build step, at the cost of an extra network call.

**Files to change:**
- Delete `frontend/lib/validation.ts`
- Add `scripts/generate_schema.py` (Option A) or extend `app/api/config.py` (Option B)
- Update `frontend/lib/api.ts` to import generated types

---

### Recommendation #2 — Create a Single `JobCreationService` Used by All Routes

**Addresses:** Issue #2

**Approach:** Extract the canonical job creation flow into `app/services/job_creation_service.py`. All routes that create jobs call this service, passing a fully-validated `JobCreateRequest`.

```python
# app/services/job_creation_service.py
async def create_job(
    request: JobCreateRequest,
    supabase: Client,
    publisher: QueuePublisher,
    email: Optional[str] = None,
) -> JobCreateResult:
    job_id = await job_service.create_job(supabase, request, email)
    await publisher.publish_job(job_id, request.model_dump())
    return JobCreateResult(job_id=job_id, ws_url=f"/v1/ws/{job_id}")
```

The batch route must validate each row against `JobCreateRequest` (not `JobConfigSchema`) before calling `create_job()`. Template merging (merging template defaults with request overrides) becomes a pure function in this service:

```python
def merge_template(template: dict, overrides: JobCreateRequest) -> JobCreateRequest:
    base = JobCreateRequest(**template["config"])
    return base.model_copy(update=overrides.model_dump(exclude_unset=True))
```

**Files to change:**
- Create `app/services/job_creation_service.py`
- Refactor `app/api/jobs.py` (`POST /v1/jobs`, `POST /v1/jobs/{template_id}/create`)
- Refactor `app/api/batch.py` (replace `JobConfigSchema` with `JobCreateRequest`)

---

### Recommendation #3 — Externalize Email Templates to Jinja2 Files

**Addresses:** Issue #3

**Approach:** Move email body construction out of `EmailService._send()` into Jinja2 template files. The service renders the template; it does not own the content.

```
app/
  templates/
    email/
      completion_plain.txt.j2
      completion_html.html.j2
```

```python
# app/services/email_service.py
from jinja2 import Environment, FileSystemLoader

_env = Environment(loader=FileSystemLoader("app/templates/email"))

def _render(template_name: str, **ctx) -> str:
    return _env.get_template(template_name).render(**ctx)
```

This change also makes it straightforward to add new notification types (e.g., cover approval requests, failure alerts) without touching the service class.

**Files to change:**
- Create `app/templates/email/completion_plain.txt.j2`
- Create `app/templates/email/completion_html.html.j2`
- Refactor `app/services/email_service.py`

---

### Recommendation #4 — Create a `cover_revisions` Table for Audit Trail

**Addresses:** Issue #4

**Approach:** Replace the pattern of storing revision feedback in `job.config` with a dedicated `cover_revisions` table. Each revision request inserts a new row; history is preserved.

```sql
-- supabase/migrations/XXXX_cover_revisions.sql
CREATE TABLE cover_revisions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id      uuid REFERENCES jobs(id),
  feedback    text NOT NULL,
  requested_at timestamptz NOT NULL DEFAULT now(),
  revision_number int NOT NULL
);
```

The cover route inserts a row instead of patching `job.config`. The worker reads the latest revision feedback from this table rather than from `job.config`.

**Files to change:**
- Add `supabase/migrations/XXXX_cover_revisions.sql`
- Refactor `app/api/cover.py` (revise endpoint)
- Refactor `app/services/` (add `cover_revision_service.py`)
- Update worker's `CoverEngine` to query latest revision feedback

---

### Recommendation #5 — Use `JobCreateRequest` for Batch Row Validation

**Addresses:** Issue #5

**Approach:** Replace `JobConfigSchema` in the batch endpoints with `JobCreateRequest`. Validation errors are collected per-row and returned immediately in the API response, matching the behavior already documented in the batch endpoint's error array.

```python
# app/api/batch.py (revised)
from app.domain.validation_schemas import JobCreateRequest

for i, row in enumerate(rows):
    try:
        validated = JobCreateRequest(**row)
    except ValidationError as e:
        errors.append({"row": i, "errors": e.errors()})
        continue
    await job_creation_service.create_job(validated, supabase, publisher)
```

**Files to change:**
- `app/api/batch.py` — replace `JobConfigSchema` with `JobCreateRequest`
- Remove `JobConfigSchema` class if it has no other uses

---

### Recommendation #6 — Fetch Default Model from `/v1/config/providers`

**Addresses:** Issue #6

**Approach:** The `JobCreatorForm` should initialize its `model` default from the providers config API response rather than a hardcoded string.

```typescript
// frontend/components/JobCreatorForm.tsx
const { data: config } = useSWR("/v1/config/providers", fetcher);
const defaultModel = config?.llm_providers?.[0]?.default_model ?? "";

const form = useForm({
  defaultValues: { model: defaultModel, ... }
});
```

If `useForm` requires synchronous defaults, initialize with an empty string and call `form.reset(defaults)` once the config response arrives.

**Files to change:**
- `frontend/components/JobCreatorForm.tsx`
- Verify `app/api/config.py` returns `default_model` per provider

---

### Recommendation #7 — Name the Preview Truncation Constant

**Addresses:** Issue #7

**Approach:** Move the magic number to a named constant in the domain or API layer.

```python
# app/domain/constants.py  (new file, or add to existing)
CHAPTER_PREVIEW_CHARS = 200

# app/api/chapters.py
from app.domain.constants import CHAPTER_PREVIEW_CHARS
...
"preview": chapter["content"][:CHAPTER_PREVIEW_CHARS]
```

Consider also truncating at the nearest word boundary to avoid mid-word cuts:

```python
content = chapter["content"]
preview = content if len(content) <= CHAPTER_PREVIEW_CHARS else content[:CHAPTER_PREVIEW_CHARS].rsplit(" ", 1)[0] + "…"
```

**Files to change:**
- `app/domain/constants.py` (create or extend)
- `app/api/chapters.py`

---

## 6. Overall Adherence Assessment

### Scorecard

| Principle | Status | Notes |
|-----------|--------|-------|
| **Business logic in backend only** | MOSTLY MET | Validation duplicated in frontend (Issue #1) |
| **Frontend is presentation-only** | MOSTLY MET | No decision logic in React components; form validation is the only gap |
| **Single source of truth per rule** | PARTIALLY MET | Validation (Issue #1), job creation (Issue #2), batch schema (Issue #5) are exceptions |
| **Modularity / pluggability** | MET | Pipeline engines, LLM clients, image clients are well-factored |
| **Separation of concerns** | MOSTLY MET | Email body in service class (Issue #3), revision data in config column (Issue #4) |
| **State transition centralization** | MET | `JobStateMachine` / `CoverStateMachine` are the sole arbiters |
| **Configuration centralization** | MOSTLY MET | Default model name hardcoded in frontend (Issue #6) |
| **No magic numbers in routing code** | PARTIALLY MET | Chapter preview limit (Issue #7) |

### Strengths

- The domain layer (`state_machine.py`, `validation_schemas.py`) is clean, pure, and dependency-free — ideal for unit testing.
- The pipeline engine pattern (`BaseEngine` → pluggable subclasses) is an excellent design that makes the worker extensible without touching the orchestrator.
- `LLMClient` and `ImageClient` successfully abstract all provider-specific details behind a single interface.
- `security.py` ensures sensitive fields are redacted in a single location, not scattered across routes.
- Error handling is consistent: domain exceptions flow cleanly to HTTP exceptions via a centralized mapping.
- The WebSocket progress stream correctly sends a snapshot first and then live events — the frontend never needs to compute job progress independently.

### Areas Requiring Immediate Action

1. **Issue #1 (Validation Duplication)** — Highest risk; implement Recommendation #1 before the next schema change.
2. **Issue #2 (Job Creation Fragmentation)** — Second highest; batch jobs silently bypass validation and produce DLQ failures.
3. **Issue #5 (Batch Schema)** — Can be addressed as part of Issue #2's fix.

### Deferred / Low Priority

4. **Issue #3 (Email Templates)** — Cosmetic for now; becomes important when multi-language or white-label is required.
5. **Issue #4 (Cover Revisions)** — Requires schema migration; acceptable short-term if revision count is low.
6. **Issue #6 (Default Model)** — Low risk; backend will reject invalid model names anyway.
7. **Issue #7 (Magic Number)** — Trivial rename; can be included in any near-term PR.

---

*End of Redundant Logic Manifest*
*Generated by: Code Review Agent | Book Generation Engine*
