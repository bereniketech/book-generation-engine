# Bug Log

Format: date | what broke | root cause | fix | files

---

## 2026-04-24 | Integration tests failed with RuntimeError on Supabase credentials

**What broke:**
`tests/integration/test_jobs_api.py` — all 3 integration tests raised `RuntimeError: Supabase credentials not configured` when calling `POST /v1/jobs`, `GET /v1/jobs/{id}`, and related endpoints.

**Root cause:**
The integration test file created a standalone `_test_app = FastAPI(lifespan=_mock_lifespan)` and included `jobs_router`, but did not override the `get_supabase` FastAPI dependency. When route handlers called `Depends(get_supabase)`, the real `get_supabase_client()` was invoked and raised `RuntimeError` because `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` environment variables are not set in test environments.

The lifespan stub set `app.state.supabase` but the router's endpoints use `Depends(get_supabase)` (DI pattern), not `request.app.state.supabase`, so the state attribute was irrelevant.

Also, one test asserted `response.json()["detail"] == "Job not found"` (raw string), but after the standardized error refactoring (Finding 4), the detail is a structured dict `{"error": "...", "code": "JOB_NOT_FOUND"}`.

**Fix:**
1. Added `_test_app.dependency_overrides[get_supabase] = lambda: _mock_supabase` at module level.
2. Updated the 404 assertion to match the structured error envelope: `response.json()["detail"]["code"] == "JOB_NOT_FOUND"`.
3. Updated the redaction test to match the canonical `***REDACTED***` string rather than the abbreviated `***`.

**Files:**
- `tests/integration/test_jobs_api.py`
