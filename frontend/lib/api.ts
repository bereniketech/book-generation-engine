/**
 * API client utilities for the book-generation-engine backend.
 *
 * All error handling is standardized around the backend's
 * ``{"error": string, "code": string}`` detail envelope.  Every failed
 * response is converted into an ``ApiError`` instance so that callers can
 * branch on ``error.code`` instead of parsing message strings.
 *
 * Backend route prefix notes:
 *   - Jobs and WebSocket routes:  /v1/*
 *   - Chapters routes:            /jobs/* (no /v1 prefix — chapters router mounts at /jobs)
 *   - Cover routes:               /jobs/* (no /v1 prefix — cover router mounts at /jobs)
 *   - Config routes:              /v1/config/*
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Structured error type
// ---------------------------------------------------------------------------

export interface ApiErrorDetail {
  error: string;
  code: string;
  [key: string]: unknown;
}

export class ApiError extends Error {
  readonly code: string;
  readonly statusCode: number;
  readonly detail: ApiErrorDetail;

  constructor(detail: ApiErrorDetail, statusCode: number) {
    super(detail.error);
    this.name = "ApiError";
    this.code = detail.code;
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

// ---------------------------------------------------------------------------
// Core fetch helpers
// ---------------------------------------------------------------------------

/**
 * Parse a non-OK HTTP response into an ``ApiError``.
 *
 * Handles three shapes:
 * 1. ``{ "detail": { "error": ..., "code": ... } }`` — FastAPI HTTPException
 * 2. ``{ "error": ..., "code": ... }``               — direct structured body
 * 3. Unparseable body                                — synthesise from status
 */
export async function handleApiError(response: Response): Promise<never> {
  let detail: ApiErrorDetail;

  try {
    const body = (await response.json()) as Record<string, unknown>;

    // FastAPI wraps HTTPException details under "detail"
    const candidate = body["detail"] ?? body;

    if (
      candidate !== null &&
      typeof candidate === "object" &&
      typeof (candidate as Record<string, unknown>)["error"] === "string" &&
      typeof (candidate as Record<string, unknown>)["code"] === "string"
    ) {
      detail = candidate as ApiErrorDetail;
    } else {
      detail = {
        error: `HTTP ${response.status}`,
        code: "HTTP_ERROR",
      };
    }
  } catch {
    detail = {
      error: `HTTP ${response.status}`,
      code: "HTTP_ERROR",
    };
  }

  throw new ApiError(detail, response.status);
}

/**
 * Generic fetch wrapper.  Throws ``ApiError`` on any non-OK response.
 */
export async function fetcher<T = unknown>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(url, options);

  if (!response.ok) {
    await handleApiError(response);
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface JobSummary {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  config: Record<string, unknown>;
}

export interface JobListResponse {
  jobs: JobSummary[];
  total: number;
  page: number;
  limit: number;
}

export interface JobStatusTransitionResponse {
  id: string;
  status: string;
}

export interface RestartJobResponse {
  new_job_id: string;
}

export interface ChapterSummary {
  index: number;
  status: string;
  qa_score: number | null;
  content_preview: string;
}

export interface ChapterListResponse {
  chapters: ChapterSummary[];
}

export interface ChapterDetail {
  job_id: string;
  index: number;
  content: string;
  status: string;
  qa_score: number | null;
  flesch_kincaid_grade: number | null;
  flesch_reading_ease: number | null;
}

export interface ChapterEditResponse {
  job_id: string;
  index: number;
  status: string;
}

export interface CoverResponse {
  job_id: string;
  cover_url: string | null;
  cover_status: string | null;
}

export interface CoverApproveResponse {
  job_id: string;
  status: string;
}

export interface CoverReviseResponse {
  job_id: string;
  cover_status: string;
}

export interface ProvidersResponse {
  llm_providers: string[];
  image_providers: string[];
}

// ---------------------------------------------------------------------------
// Jobs API  (prefix: /v1)
// ---------------------------------------------------------------------------

export async function createJob(
  body: import("@/types/job").JobCreateRequest,
): Promise<import("@/types/job").JobCreateResponse> {
  return fetcher(`${API_BASE}/v1/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getJob(jobId: string): Promise<Record<string, unknown>> {
  return fetcher(`${API_BASE}/v1/jobs/${jobId}`);
}

export async function listJobs(params?: {
  status?: string;
  page?: number;
  limit?: number;
}): Promise<JobListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.page !== undefined) query.set("page", String(params.page));
  if (params?.limit !== undefined) query.set("limit", String(params.limit));

  const qs = query.toString();
  return fetcher(`${API_BASE}/v1/jobs${qs ? `?${qs}` : ""}`);
}

export async function pauseJob(
  jobId: string,
): Promise<JobStatusTransitionResponse> {
  return fetcher(`${API_BASE}/v1/jobs/${jobId}/pause`, { method: "PATCH" });
}

export async function resumeJob(
  jobId: string,
): Promise<JobStatusTransitionResponse> {
  return fetcher(`${API_BASE}/v1/jobs/${jobId}/resume`, { method: "PATCH" });
}

export async function cancelJob(jobId: string): Promise<void> {
  // Backend returns 204 No Content — no JSON body to parse.
  const response = await fetch(`${API_BASE}/v1/jobs/${jobId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    await handleApiError(response);
  }
}

export async function restartJob(
  jobId: string,
): Promise<RestartJobResponse> {
  return fetcher(`${API_BASE}/v1/jobs/${jobId}/restart`, { method: "POST" });
}

// ---------------------------------------------------------------------------
// Chapters API  (prefix: /jobs — no /v1)
//
// The chapters router mounts at /jobs, not /v1/jobs.
// Chapter lookups use the 0-based `index` integer, not a UUID.
// ---------------------------------------------------------------------------

export async function listChapters(
  jobId: string,
): Promise<ChapterListResponse> {
  return fetcher(`${API_BASE}/jobs/${jobId}/chapters`);
}

export async function getChapter(
  jobId: string,
  index: number,
): Promise<ChapterDetail> {
  return fetcher(`${API_BASE}/jobs/${jobId}/chapters/${index}`);
}

/**
 * Update chapter content.  Backend sets status to "locked" on save.
 *
 * @param jobId  - UUID of the parent job
 * @param index  - 0-based chapter index (NOT a chapter UUID)
 * @param content - Full replacement chapter text
 */
export async function updateChapter(
  jobId: string,
  index: number,
  content: string,
): Promise<ChapterEditResponse> {
  return fetcher(`${API_BASE}/jobs/${jobId}/chapters/${index}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

// ---------------------------------------------------------------------------
// Cover API  (prefix: /jobs — no /v1)
// ---------------------------------------------------------------------------

export async function getCover(jobId: string): Promise<CoverResponse> {
  return fetcher(`${API_BASE}/jobs/${jobId}/cover`);
}

export async function approveCover(
  jobId: string,
): Promise<CoverApproveResponse> {
  return fetcher(`${API_BASE}/jobs/${jobId}/cover/approve`, { method: "POST" });
}

export async function reviseCover(
  jobId: string,
  feedback: string,
): Promise<CoverReviseResponse> {
  return fetcher(`${API_BASE}/jobs/${jobId}/cover/revise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback }),
  });
}

// ---------------------------------------------------------------------------
// Config API  (prefix: /v1/config)
// ---------------------------------------------------------------------------

export async function getProviders(): Promise<ProvidersResponse> {
  return fetcher(`${API_BASE}/v1/config/providers`);
}

// ---------------------------------------------------------------------------
// NOT YET IMPLEMENTED — backend endpoints do not exist
//
// These functions map to routes that have not been built on the backend yet.
// They will throw ApiError (or a network error) at runtime, which callers
// must handle gracefully.  They are kept here so that components that reference
// them continue to compile while the backend is being built.
//
//   lockChapter       — POST /v1/chapters/{id}/lock    (no such route)
//   regenerateChapter — POST /v1/chapters/{id}/regenerate (no such route)
//   getExport         — GET  /v1/jobs/{id}/export      (no such route)
// ---------------------------------------------------------------------------

/** @notImplemented Backend endpoint does not exist yet. */
export async function lockChapter(_chapterId: string): Promise<void> {
  throw new ApiError(
    { error: "lockChapter is not implemented on the backend", code: "NOT_IMPLEMENTED" },
    501,
  );
}

/** @notImplemented Backend endpoint does not exist yet. */
export async function regenerateChapter(_chapterId: string): Promise<void> {
  throw new ApiError(
    { error: "regenerateChapter is not implemented on the backend", code: "NOT_IMPLEMENTED" },
    501,
  );
}

/** @notImplemented Backend endpoint does not exist yet. */
export async function getExport(
  _jobId: string,
): Promise<{ download_url: string; files: string[] }> {
  throw new ApiError(
    { error: "getExport is not implemented on the backend", code: "NOT_IMPLEMENTED" },
    501,
  );
}

// ---------------------------------------------------------------------------
// Legacy alias kept for backward-compat during migration
// getChapters() was the old name — callers are being updated to listChapters()
// ---------------------------------------------------------------------------

/** @deprecated Use listChapters(jobId) instead. */
export async function getChapters(
  jobId: string,
): Promise<ChapterSummary[]> {
  const result = await listChapters(jobId);
  return result.chapters;
}
