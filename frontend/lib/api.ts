/**
 * API client utilities for the book-generation-engine backend.
 *
 * All error handling is standardized around the backend's
 * ``{"error": string, "code": string}`` detail envelope.  Every failed
 * response is converted into an ``ApiError`` instance so that callers can
 * branch on ``error.code`` instead of parsing message strings.
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
 * 2. ``{ "error": ..., "code": ... }``              — direct structured body
 * 3. Unparseable body                               — synthesise from status
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
// Domain API functions
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

export async function getChapters(
  jobId: string,
): Promise<Record<string, unknown>[]> {
  return fetcher(`${API_BASE}/v1/jobs/${jobId}/chapters`);
}

export async function updateChapter(
  chapterId: string,
  content: string,
): Promise<void> {
  await fetcher(`${API_BASE}/v1/chapters/${chapterId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

export async function lockChapter(chapterId: string): Promise<void> {
  await fetcher(`${API_BASE}/v1/chapters/${chapterId}/lock`, {
    method: "POST",
  });
}

export async function regenerateChapter(chapterId: string): Promise<void> {
  await fetcher(`${API_BASE}/v1/chapters/${chapterId}/regenerate`, {
    method: "POST",
  });
}

export async function getExport(
  jobId: string,
): Promise<{ download_url: string; files: string[] }> {
  return fetcher(`${API_BASE}/v1/jobs/${jobId}/export`);
}
