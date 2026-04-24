# Logic Centralization Audit - Book Generation Engine

**Date:** 2026-04-24  
**Scope:** Full codebase analysis for logic duplication and scattered responsibilities  
**Key Finding:** 10 significant issues identified, 4 classified as CRITICAL/HIGH priority  

---

## Executive Summary

The codebase exhibits a clear separation of concerns between frontend (rendering) and backend (business logic), but **logic is NOT exclusively in the backend**. Multiple instances of:

- **Duplicated validation** rules (frontend + backend)
- **Hardcoded configuration** lists in frontend components
- **Scattered database access** patterns across 5 route files
- **Inconsistent error handling** with no unified format
- **Desynchronized API contracts** between frontend and backend

This audit identifies 10 distinct areas of concern with severity ratings and remediation guidance.

---

## CRITICAL FINDINGS

### 1. ⚠️ PROVIDER LISTS HARDCODED IN FRONTEND (CRITICAL)

**Status:** ❌ VIOLATION - Frontend contains business logic  
**Risk Level:** CRITICAL  
**Priority:** Must fix before adding new providers

#### The Problem

Frontend component maintains hardcoded lists of supported LLM and image providers:

**File:** `frontend/components/ProviderConfigPanel.tsx` (Lines 11-12)
```typescript
const LLM_PROVIDERS = ["anthropic", "openai", "google", "ollama", "openai-compatible"] as const;
const IMAGE_PROVIDERS = ["dall-e-3", "replicate-flux"] as const;
```

**Backend Definition:** `app/models/job.py` (Lines 10, 17)
```python
provider: Literal["anthropic", "openai", "google", "ollama", "openai-compatible"]
provider: Literal["dall-e-3", "replicate-flux"]
```

#### Why This Is Wrong

1. **Provider addition requires dual updates:** Backend + frontend both need changes
2. **Silent desynchronization:** If backend adds provider without updating frontend, users can't select it
3. **Deployment coordination:** Must coordinate frontend & backend releases
4. **Source of truth split:** Two places maintain the same data

#### Real-world Scenario

- Suppose you want to support `anthropic-legacy` model
- Backend is updated to accept `"anthropic-legacy"` in the Literal
- Frontend still shows only 5 options (anthropic, openai, google, ollama, openai-compatible)
- User can't see the new provider option despite backend supporting it
- OR user finds workaround and submits raw JSON, bypassing form entirely

#### What Should Happen

Backend serves as single source of truth:

**Frontend fetches on app load:**
```typescript
// lib/config.ts
const { llm_providers, image_providers } = await fetch('/v1/config/providers').then(r => r.json());
```

**Backend serves:**
```python
# api/config.py
@router.get("/config/providers")
async def get_providers():
    return {
        "llm_providers": ["anthropic", "openai", "google", "ollama", "openai-compatible"],
        "image_providers": ["dall-e-3", "replicate-flux"]
    }
```

---

### 2. ⚠️ VALIDATION LOGIC DUPLICATED IN FRONTEND & BACKEND (HIGH)

**Status:** ❌ VIOLATION - Validation enforced in two places with gaps  
**Risk Level:** HIGH  
**Impact:** Users get late error feedback instead of immediate client validation

#### The Problem

Validation rules defined separately in frontend form and backend Pydantic models:

**Frontend - JobCreatorForm.tsx (Lines 54, 64, 83):**
```typescript
// Validates:
<input {...register("title", { required: "Title is required", maxLength: { value: 500, ... } })} />
<textarea {...register("topic", { required: "Topic is required", maxLength: { value: 2000, ... } })} />
<input {...register("target_chapters", { min: 3, max: 50, valueAsNumber: true })} />
// ❌ Missing: audience, tone minimum length validation
// ❌ Missing: LLM/image API key length constraints
```

**Backend - app/models/job.py (Lines 22-27):**
```python
title: str = Field(min_length=1, max_length=500)
topic: str = Field(min_length=1, max_length=2000)
audience: str = Field(min_length=1, max_length=500)  # ← Not validated in frontend!
tone: str = Field(min_length=1, max_length=200)      # ← Not validated in frontend!
target_chapters: int = Field(ge=3, le=50, default=12)
llm: LLMProviderConfig  # model: min_length=1, max_length=200
image: ImageProviderConfig  # api_key: min_length=1, max_length=500
```

#### Validation Gaps Identified

| Field | Frontend | Backend | Gap |
|-------|----------|---------|-----|
| `title` | max 500 ✓ | min 1, max 500 | Missing min validation |
| `topic` | max 2000 ✓ | min 1, max 2000 | Missing min validation |
| `audience` | ❌ Not validated | min 1, max 500 | Field can be empty despite requirement |
| `tone` | ❌ Not validated | min 1, max 200 | Field can be empty despite requirement |
| `target_chapters` | min 3, max 50 ✓ | min 3, max 50 | ✓ Aligned |
| `llm.provider` | Required ✓ | Required | ✓ Aligned |
| `llm.model` | Required | min 1, max 200 | Length constraints missing |
| `llm.api_key` | Required, password | min 1, max 500 | Length constraints missing |
| `image.provider` | Required ✓ | Required | ✓ Aligned |
| `image.api_key` | Required, password | min 1, max 500 | Length constraints missing |

#### User Experience Impact

1. User submits form with empty `audience` field
2. Frontend shows no error (validation not enforced)
3. Form submits to backend
4. Backend rejects with 422 Unprocessable Entity
5. User sees generic error (no field-specific feedback)
6. User retries without knowing which field was invalid

#### Code Locations Where Validation Rules Live

- **Rule definition #1:** `frontend/types/job.ts` (interface, no validation)
- **Rule definition #2:** `frontend/components/JobCreatorForm.tsx` (form register calls)
- **Rule definition #3:** `app/models/job.py` (Pydantic Field constraints)

**Result:** 3 different places = 3 different sources of truth

#### What Should Happen

Single validation schema generates both frontend form rules and backend validators:

```typescript
// lib/validation.ts (single source of truth)
export const JobCreateSchema = z.object({
  title: z.string().min(1).max(500),
  topic: z.string().min(1).max(2000),
  audience: z.string().min(1).max(500),
  tone: z.string().min(1).max(200),
  target_chapters: z.number().int().min(3).max(50),
  llm: z.object({
    provider: z.enum(["anthropic", "openai", "google", "ollama", "openai-compatible"]),
    model: z.string().min(1).max(200),
    api_key: z.string().min(1).max(500),
    base_url: z.string().optional(),
  }),
  image: z.object({
    provider: z.enum(["dall-e-3", "replicate-flux"]),
    api_key: z.string().min(1).max(500),
  }),
  notification_email: z.string().email().optional(),
});

// In frontend: useForm({ resolver: zodResolver(JobCreateSchema) })
// In backend: Use zodToJsonSchema for Pydantic equivalents
```

---

### 3. ⚠️ SUPABASE CLIENT CREATION DUPLICATED IN 5 FILES (MEDIUM)

**Status:** ❌ VIOLATION - Single function copied 5 times  
**Risk Level:** MEDIUM  
**Maintenance Burden:** High

#### The Problem

Identical `_client()` function exists in multiple route files:

**File 1:** `app/api/jobs.py` (Lines 41-46)
```python
def _client():
    import os
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    return create_client(url, key)
```

**File 2:** `app/api/chapters.py` (Lines 19-20)
```python
def _client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
```

**File 3:** `app/api/cover.py` (Lines 19-20)
```python
def _client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
```

**File 4:** `app/api/templates.py` (Lines 19-20)
```python
def _client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
```

**File 5:** `app/api/batch.py` (Lines 41-42)
```python
def _supabase():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
```

#### Variations Between Implementations

| Aspect | jobs.py | chapters.py | cover.py | templates.py | batch.py |
|--------|---------|-------------|----------|------------|----------|
| Function name | `_client()` | `_client()` | `_client()` | `_client()` | `_supabase()` |
| Loads env at | Module level | Module level | Module level | Module level | Module level |
| Imports at | Function level | Module level | Module level | Module level | Module level |
| Caching | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| Error handling | ❌ None | ❌ None | ❌ None | ❌ None | ❌ None |

#### Risks

1. **Propagates bugs:** If one file has a fix (e.g., timeout added), must update 5 places
2. **Inconsistent behavior:** Some might have error handling, others don't
3. **No pooling:** Each call creates new client instance (no connection reuse)
4. **Environment variable loading:** Happens 5 different ways (some at module load, some at runtime)
5. **Testability:** Can't inject mock client for testing without modifying each route file

#### Real-world Scenario

Decision: "Add 30-second timeout to all Supabase calls"

Without centralization:
```python
# Must edit jobs.py
client = create_client(url, key, timeout=30)

# Must edit chapters.py
client = create_client(url, key, timeout=30)

# Must edit cover.py
client = create_client(url, key, timeout=30)

# Must edit templates.py
client = create_client(url, key, timeout=30)

# Must edit batch.py
client = create_client(url, key, timeout=30)
```

With centralization:
```python
# Edit infrastructure/supabase_client.py (1 place)
client = create_client(url, key, timeout=30)
# All 5 routes automatically get the timeout
```

#### What Should Happen

**File:** `app/infrastructure/supabase_client.py` (NEW)
```python
"""Centralized Supabase client management."""
from functools import lru_cache
import os
from supabase import create_client, Client

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get singleton Supabase client instance.
    
    Uses lru_cache for connection pooling and reuse.
    Raises RuntimeError if credentials not configured.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise RuntimeError("Supabase credentials not configured")
    
    return create_client(url, key)
```

**Usage in all route files:**
```python
from app.infrastructure.supabase_client import get_supabase_client

@router.get("/chapters")
async def list_chapters():
    client = get_supabase_client()  # Reuses cached instance
    result = client.table("chapters").select("*").execute()
```

**Benefits:**
- ✅ Single definition
- ✅ Connection pooling (lru_cache)
- ✅ Centralized error handling
- ✅ Easy to add logging/monitoring
- ✅ Testable (can mock the function)

---

### 4. ⚠️ ERROR RESPONSE FORMAT INCONSISTENT (MEDIUM)

**Status:** ❌ VIOLATION - Frontend error handling fragile  
**Risk Level:** MEDIUM  
**Impact:** Frontend must handle multiple error formats

#### The Problem

Inconsistent error detail structures across endpoints:

**Standardized format (structured error):**

`app/api/jobs.py` (Lines 34-37):
```python
raise HTTPException(
    status_code=404,
    detail={"error": "Job not found", "code": "JOB_NOT_FOUND"},
)
```

**Non-standardized format (simple string):**

`app/api/jobs.py` (Line 110):
```python
raise HTTPException(status_code=404, detail="Job not found")
```

#### Inconsistency Mapping

| Endpoint | Format | Example |
|----------|--------|---------|
| `POST /jobs` | Structured | `{"error": "...", "code": "..."}` |
| `GET /jobs/{id}` | String | `"Job not found"` |
| `PATCH /jobs/{id}/pause` | Structured | `{"error": "...", "code": "INVALID_STATE_TRANSITION"}` |
| `GET /jobs/{id}/chapters` | Structured | `{"error": "Chapter not found", "code": "CHAPTER_NOT_FOUND"}` |
| `POST /jobs/{id}/cover/approve` | Structured | `{"error": "No cover awaiting approval", "code": "NO_PENDING_COVER"}` |

#### Frontend Error Handling (JobCreatorForm.tsx Lines 35-36)

```typescript
try {
  const response = await createJob(data);
  router.push(`/jobs/${response.job_id}`);
} catch (err: unknown) {
  // Defensive: assumes nested structure might exist
  const e = err as { detail?: { detail?: string } };
  setApiError(e?.detail?.detail || "Submission failed. Check your inputs and try again.");
  setSubmitting(false);
}
```

**Problem:** Frontend guesses at error structure with `?.detail?.detail` fallback

#### Real-world Scenario

1. Backend returns `{ detail: "Job not found" }` (string)
2. Frontend code tries to access `.detail` on string → throws error
3. Whole error handling breaks → `setApiError` never called
4. User sees no error feedback, form stays in submitting state
5. User has to refresh page manually

#### What Should Happen

**Standard error response envelope:**

```python
# app/infrastructure/http_exceptions.py (NEW)
"""Standardized exception handling for all endpoints."""
from fastapi import HTTPException
from typing import Any

class AppException(HTTPException):
    """Standard exception with error code and structured detail."""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        detail: dict[str, Any] | None = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error": message,
                "code": error_code,
                **(detail or {})
            }
        )

# Usage:
class JobNotFoundError(AppException):
    def __init__(self):
        super().__init__(
            status_code=404,
            error_code="JOB_NOT_FOUND",
            message="Job not found"
        )

class InvalidStateTransitionError(AppException):
    def __init__(self, current: str, target: str):
        super().__init__(
            status_code=409,
            error_code="INVALID_STATE_TRANSITION",
            message=f"Cannot transition from {current} to {target}"
        )
```

**Usage in all routes:**
```python
from app.infrastructure.http_exceptions import JobNotFoundError

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    if not job:
        raise JobNotFoundError()  # Always returns structured error
```

**Frontend expectation (type-safe):**
```typescript
interface ApiErrorResponse {
  error: string
  code: string
}

try {
  await createJob(data)
} catch (err: unknown) {
  const response = err as { detail?: ApiErrorResponse }
  setApiError(response.detail?.error || "Unknown error")
}
```

---

### 5. ⚠️ JOB STATE VALIDATION SCATTERED (HIGH)

**Status:** ❌ VIOLATION - State machine logic not centralized  
**Risk Level:** HIGH  
**Impact:** Hard to add new states, duplicate state checks

#### The Problem

State transition validation duplicated across multiple endpoints with no central definition:

**cover.py (Lines 47-50 & 63-66) - Identical check twice:**
```python
# In approve_cover():
if job.get("cover_status") != "awaiting_approval":
    raise HTTPException(status_code=409, ...)

# In revise_cover():
if job.get("cover_status") != "awaiting_approval":
    raise HTTPException(status_code=409, ...)
```

**jobs.py (Lines 150-156) - Different pattern:**
```python
TERMINAL_STATES = {"complete", "cancelled"}

if job["status"] in TERMINAL_STATES:
    raise HTTPException(status_code=409, ...)
```

#### No Single Source of Truth for Valid Transitions

Current system has these states:
- `queued`, `generating`, `paused`, `complete`, `cancelled`, `failed`
- `cover_status`: `awaiting_approval`, `approved`, `revising`

But **nowhere documents:**
- What transitions ARE valid
- What causes each transition
- What states are terminal

#### Risk Scenario

New requirement: "Add ability to resume a failed job"

Without centralization:
1. Add `"failed": "queued"` transition logic in jobs.py
2. Check if cover.py needs similar logic — update if needed
3. Check if chapters.py has state logic — update if needed
4. Check batch.py — might also need updates
5. Update admin.py if it shows state info
6. Result: Same change in 4-5 places, easy to miss one

With centralization:
1. Update state machine definition in ONE place
2. All endpoints automatically respect new transitions

#### Duplicate State Checks

Code duplication in `cover.py`:

```python
@router.post("/{job_id}/cover/approve")
async def approve_cover(job_id: str):
    job = _get_job_or_404(job_id)
    if job.get("cover_status") != "awaiting_approval":  # CHECK 1
        raise HTTPException(status_code=409, ...)
    # ... update database

@router.post("/{job_id}/cover/revise")
async def revise_cover(job_id: str, body: ReviseRequest):
    job = _get_job_or_404(job_id)
    if job.get("cover_status") != "awaiting_approval":  # CHECK 2 (identical)
        raise HTTPException(status_code=409, ...)
    # ... update database
```

Both checks are identical — violates DRY principle.

#### What Should Happen

**File:** `app/domain/state_machine.py` (NEW)
```python
"""Job state machine definition.

Defines all valid state transitions and provides validation.
Single source of truth for workflow logic.
"""
from enum import Enum
from typing import Set

class JobStatus(str, Enum):
    """Valid job statuses."""
    QUEUED = "queued"
    GENERATING = "generating"
    PAUSED = "paused"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    FAILED = "failed"
    ASSEMBLING = "assembling"

class CoverStatus(str, Enum):
    """Valid cover statuses."""
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REVISING = "revising"

class JobStateMachine:
    """Defines valid state transitions for job workflow."""
    
    # What transitions are valid FROM each state
    VALID_TRANSITIONS: dict[str, Set[str]] = {
        JobStatus.QUEUED: {
            JobStatus.GENERATING,
            JobStatus.PAUSED,
            JobStatus.CANCELLED,
        },
        JobStatus.GENERATING: {
            JobStatus.COMPLETE,
            JobStatus.FAILED,
            JobStatus.PAUSED,
        },
        JobStatus.PAUSED: {
            JobStatus.QUEUED,
            JobStatus.CANCELLED,
        },
        JobStatus.FAILED: {
            JobStatus.QUEUED,  # Restart
        },
        # Terminal states (no outgoing transitions)
        JobStatus.COMPLETE: set(),
        JobStatus.CANCELLED: set(),
        JobStatus.ASSEMBLING: {
            JobStatus.COMPLETE,
            JobStatus.FAILED,
        },
    }
    
    TERMINAL_STATES = {JobStatus.COMPLETE, JobStatus.CANCELLED, JobStatus.FAILED}
    
    @staticmethod
    def can_transition(current: str, target: str) -> bool:
        """Check if transition from current → target is valid."""
        return target in JobStateMachine.VALID_TRANSITIONS.get(current, set())
    
    @staticmethod
    def validate_transition(current: str, target: str) -> None:
        """Raise exception if transition invalid."""
        if not JobStateMachine.can_transition(current, target):
            valid = JobStateMachine.VALID_TRANSITIONS.get(current, set())
            raise InvalidStateTransitionError(
                current=current,
                target=target,
                valid_transitions=list(valid)
            )
    
    @staticmethod
    def is_terminal(status: str) -> bool:
        """Check if status is terminal (no further transitions)."""
        return status in JobStateMachine.TERMINAL_STATES

class CoverStateMachine:
    """State machine for cover approval flow."""
    
    VALID_TRANSITIONS = {
        CoverStatus.AWAITING_APPROVAL: {
            CoverStatus.APPROVED,
            CoverStatus.REVISING,
        },
        CoverStatus.REVISING: {
            CoverStatus.AWAITING_APPROVAL,  # After revision completes
        },
        CoverStatus.APPROVED: set(),  # Terminal
    }
    
    @staticmethod
    def can_transition(current: str, target: str) -> bool:
        return target in CoverStateMachine.VALID_TRANSITIONS.get(current, set())
    
    @staticmethod
    def validate_transition(current: str, target: str) -> None:
        if not CoverStateMachine.can_transition(current, target):
            valid = CoverStateMachine.VALID_TRANSITIONS.get(current, set())
            raise InvalidStateTransitionError(
                current=current,
                target=target,
                valid_transitions=list(valid)
            )
```

**Usage in routes:**
```python
from app.domain.state_machine import JobStateMachine, CoverStateMachine

@router.patch("/jobs/{job_id}/pause")
async def pause_job(job_id: str, request: Request):
    job = _get_job_or_404(request.app.state.supabase, job_id)
    current_status = job["status"]
    
    # Single line replaces manual state checks
    JobStateMachine.validate_transition(current_status, "paused")
    
    # Update to new state
    supabase.table("jobs").update({"status": "paused"}).eq("id", job_id).execute()

@router.post("/jobs/{job_id}/cover/approve")
async def approve_cover(job_id: str):
    job = _get_job_or_404(job_id)
    current_cover_status = job.get("cover_status")
    
    # Replaces duplicated checks
    CoverStateMachine.validate_transition(current_cover_status, CoverStatus.APPROVED)
    
    _client().table("jobs").update({
        "cover_status": CoverStatus.APPROVED,
        "status": JobStatus.ASSEMBLING,
    }).eq("id", job_id).execute()
```

---

## HIGH-PRIORITY FINDINGS

### 6. API ENDPOINT ROUTES DESYNCHRONIZED

**File:** `frontend/lib/api.ts`

**Issue:** Frontend assumes backend endpoints that don't exist

Problematic functions in `api.ts`:
```typescript
// Line 28-34: Assumes endpoint `/v1/chapters/{chapterId}`
export async function updateChapter(chapterId: string, content: string): Promise<void> {
  await fetch(`${API_BASE}/v1/chapters/${chapterId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

// Line 36-38: Assumes endpoint `/v1/chapters/{chapterId}/lock`
export async function lockChapter(chapterId: string): Promise<void> {
  await fetch(`${API_BASE}/v1/chapters/${chapterId}/lock`, { method: "POST" });
}

// Line 40-42: Assumes endpoint `/v1/chapters/{chapterId}/regenerate`
export async function regenerateChapter(chapterId: string): Promise<void> {
  await fetch(`${API_BASE}/v1/chapters/${chapterId}/regenerate`, { method: "POST" });
}
```

**Actual backend endpoints (chapters.py):**
```python
# Line 27: Routes are at /jobs/{job_id}/chapters
@router.get("/{job_id}/chapters")
async def list_chapters(job_id: str):

# Line 50: Get single chapter needs job_id + index
@router.get("/{job_id}/chapters/{index}")
async def get_chapter(job_id: str, index: int):

# Line 70: Edit chapter needs job_id + index
@router.patch("/{job_id}/chapters/{index}")
async def edit_chapter(job_id: str, index: int, body: ChapterEditRequest):
```

**Result:** These API calls will 404 at runtime because the routes don't exist with that path structure.

**Fix:** Either adjust backend routes to match frontend expectations, or update frontend API calls to match backend.

Recommend: Update frontend to use `job_id`:
```typescript
export async function updateChapter(jobId: string, index: number, content: string): Promise<void> {
  await fetch(`${API_BASE}/v1/jobs/${jobId}/chapters/${index}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}
```

---

### 7. SECRET REDACTION INCONSISTENTLY APPLIED

**Status:** ❌ VIOLATION - API keys exposed in some endpoints  
**Risk Level:** MEDIUM  
**Security Issue:** Potential secret exposure

#### The Problem

`job_service.py` implements config redaction, but it's not applied everywhere.

**Protected:** `job_service.py` (Lines 11-21)
```python
def _redact_config(config: dict) -> dict:
    """Remove API keys from config dict before returning to client."""
    safe = dict(config)
    for key in ("api_key", "llm_api_key", "image_api_key"):
        if key in safe:
            safe[key] = "***"
    # ... recursively redacts nested dicts
    return safe
```

**Applied in:** `jobs.py` Line 108
```python
job["config"] = _redact_config(job.get("config", {}))
return job
```

**NOT applied in:** `chapters.py`, `cover.py`, `templates.py`

#### Risk

If chapter, cover, or template responses ever include config data, API keys would be exposed.

#### What Should Happen

**Centralize in infrastructure/security.py:**
```python
"""Security utilities including secret redaction."""

def redact_sensitive_fields(obj: dict) -> dict:
    """Recursively redact API keys and secrets from object.
    
    Redacts:
    - api_key, llm_api_key, image_api_key
    - password, token, secret
    - bearer tokens in Authorization headers
    """
    if not isinstance(obj, dict):
        return obj
    
    redacted = {}
    for key, value in obj.items():
        if key.lower() in ('api_key', 'llm_api_key', 'image_api_key', 'password', 'token', 'secret'):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive_fields(value)
        elif isinstance(value, list):
            redacted[key] = [redact_sensitive_fields(v) if isinstance(v, dict) else v for v in value]
        else:
            redacted[key] = value
    
    return redacted
```

**Apply consistently:**
```python
from app.infrastructure.security import redact_sensitive_fields

@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request):
    supabase = request.app.state.supabase
    job = job_service.get_job(supabase, job_id)
    # Redact before returning
    return redact_sensitive_fields(job)
```

---

## MEDIUM-PRIORITY FINDINGS

### 8. FRONTEND VALIDATION GAPS

**Issue:** Multiple validation rules only enforced on backend, not shown in frontend form

Missing frontend validation:
- `audience` field: Backend requires min 1 char, max 500; frontend has no constraints shown
- `tone` field: Backend requires min 1 char, max 200; frontend has no constraints shown
- All `llm.*` fields: Backend enforces lengths; frontend just marks as required
- All `image.*` fields: Backend enforces lengths; frontend just marks as required

**Impact:** Poor user experience; users get validation errors from server instead of helpful client-side guidance

**Fix:** Apply validation schema (see Finding #2 remediation) to all fields

---

### 9. INCONSISTENT DATABASE ACCESS PATTERNS

**Issue:** Some routes use dependency injection (request.app.state), others create clients on-demand

**Using DI (better for testing):**
```python
# jobs.py
async def create_job(body: JobCreate, request: Request):
    supabase = request.app.state.supabase
```

**Creating on-demand (less testable):**
```python
# chapters.py
async def list_chapters(job_id: str):
    client = _client()
```

**Recommendation:** Standardize on DI via FastAPI dependency injection:

```python
# app/api/deps.py
from fastapi import Depends, Request
from supabase import Client

def get_supabase(request: Request) -> Client:
    """Get Supabase client from app state."""
    return request.app.state.supabase

# In all routes:
@router.get("/chapters")
async def list_chapters(job_id: str, supabase: Client = Depends(get_supabase)):
    result = supabase.table("chapters").select(...).execute()
```

---

### 10. LOGGING INCONSISTENCY

**Issue:** Some routes try/catch logging errors, others don't

Less defensive (might silently fail):
```python
# jobs.py lines 99-101
log.info("api.job.created", job_id=job_id, has_template=body.template_id is not None)
```

More defensive (catches errors):
```python
try:
    log.info("api.job.created", ...)
except ValueError:
    pass
```

**Impact:** Low (doesn't affect business logic), but indicates inconsistent error handling

---

## RECOMMENDED REFACTORING PLAN

### Phase 1: Critical Fixes (1-2 days)

1. ✅ **Centralize Supabase Client** → Create `infrastructure/supabase_client.py`
2. ✅ **Create Provider Config Endpoint** → Add `/v1/config/providers` route
3. ✅ **Standardize Error Responses** → Create `infrastructure/http_exceptions.py`

### Phase 2: High-Priority Fixes (2-3 days)

4. ✅ **Centralize Validation Schema** → Create shared `validation.ts` for both frontend & backend
5. ✅ **Implement State Machine** → Create `domain/state_machine.py`
6. ✅ **Centralize Secret Redaction** → Create `infrastructure/security.py`

### Phase 3: Medium-Priority Fixes (1-2 days)

7. ✅ **Fix API Route Desynchronization** → Align frontend api.ts with backend routes
8. ✅ **Standardize DB Access** → Use FastAPI dependency injection everywhere
9. ✅ **Complete Frontend Validation** → Apply validation schema to all fields

---

## PROPOSED DIRECTORY STRUCTURE

```
app/
├── core/
│   └── logging.py  (existing)
│
├── infrastructure/  (NEW)
│   ├── __init__.py
│   ├── supabase_client.py       # Centralized Supabase client
│   ├── http_exceptions.py        # Standardized error responses
│   └── security.py               # Secret redaction & security utilities
│
├── domain/  (NEW)
│   ├── __init__.py
│   ├── state_machine.py          # Job state transitions
│   ├── validation_schemas.py      # Pydantic validators
│   └── models/
│       ├── job.py  (existing - refactor to use state_machine)
│       └── chapter.py
│
├── api/
│   ├── __init__.py
│   ├── deps.py  (NEW)            # FastAPI dependency injection
│   ├── config.py  (NEW)          # Provider lists endpoint
│   ├── jobs.py  (refactor to use infrastructure)
│   ├── chapters.py  (refactor to use infrastructure)
│   ├── cover.py  (refactor to use infrastructure)
│   ├── templates.py  (refactor to use infrastructure)
│   ├── batch.py  (refactor to use infrastructure)
│   └── admin.py
│
├── services/
│   ├── job_service.py  (refactor to use centralized security)
│   ├── token_tracker.py
│   └── progress.py
│
└── main.py

frontend/
├── lib/
│   ├── api.ts  (refactor URLs)
│   ├── config.ts  (NEW)          # Fetch provider lists on load
│   └── validation.ts  (NEW)      # Zod schema shared with backend
├── types/
│   └── job.ts  (update to use validation schema)
├── components/
│   ├── JobCreatorForm.tsx  (refactor to use config/validation)
│   └── ProviderConfigPanel.tsx  (refactor to use fetched providers)
└── app/
    └── page.tsx
```

---

## Summary Table

| Finding | Severity | Type | Files | Fix Time | Risk if Ignored |
|---------|----------|------|-------|----------|-----------------|
| Provider lists hardcoded | CRITICAL | Frontend has logic | ProviderConfigPanel + job.py | 2 hrs | New providers don't appear in UI |
| Validation duplicated | HIGH | Multiple sources of truth | Frontend + Backend | 3 hrs | Data validity gaps, bad UX |
| Supabase client duplicated 5x | MEDIUM | DRY violation | 5 route files | 1 hr | Hard to maintain, no connection pooling |
| Error format inconsistent | MEDIUM | Brittleness | All routes + frontend | 1.5 hrs | Frontend error handling fails |
| State validation scattered | HIGH | No centralization | cover.py, jobs.py | 1.5 hrs | Can't add new states easily |
| Secret redaction incomplete | MEDIUM | Security gap | Multiple routes | 0.5 hrs | API key exposure risk |
| API routes misaligned | HIGH | Contract drift | api.ts + routes | 1 hr | 404 errors in production |
| Frontend validation gaps | MEDIUM | Missing rules | JobCreatorForm | 1 hr | Poor UX, late error feedback |
| DB access patterns mixed | LOW | Code consistency | Multiple routes | 1 hr | Testing difficulty |
| Logging inconsistent | LOW | Error handling | Various routes | 0.5 hr | Debug difficulty |

**Total remediation time: ~13.5 hours**

---

## Key Principle Violations

This codebase violates the stated principle:

> "The frontend is only for rendering and display; no logic should come from multiple locations; everything is modular and singular."

Specific violations:
1. ❌ Provider lists (business configuration) defined in frontend component
2. ❌ Validation rules defined in 3 different places
3. ❌ Database client creation duplicated 5 times
4. ❌ State transition logic scattered across routes
5. ❌ Secret redaction not applied consistently

---

## Next Steps

1. **Read this audit** and identify which findings align with current priorities
2. **Start with Phase 1** (Critical) fixes for maximum impact
3. **Create feature branch** for each finding or group related findings
4. **Update tests** as you refactor to ensure no regressions
5. **After refactoring**, re-run audit to verify all issues resolved

This document serves as the authoritative reference for logic centralization issues. As features are added, refer back to the patterns established in remediation to avoid new duplications.
