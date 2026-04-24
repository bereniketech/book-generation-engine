/**
 * Unit tests for frontend/lib/api.ts
 *
 * Tests verify:
 *   1. Correct URL construction for every endpoint
 *   2. Correct HTTP method for every endpoint
 *   3. Correct request body serialisation
 *   4. ApiError is thrown with structured detail on non-OK responses
 *   5. 204 No Content (cancelJob) handled without body parsing
 *   6. Legacy alias (getChapters) unwraps the chapters array
 *
 * fetch is mocked globally; each test resets the mock.
 */

// Polyfill Response.ok (available in node 18+ via undici, but ts-jest node env
// may not have it). We build a minimal mock instead.
const makeFetchResponse = (
  body: unknown,
  status = 200,
  headers: Record<string, string> = {},
): Response => {
  const bodyText = body === null ? "" : JSON.stringify(body);
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (k: string) => headers[k] ?? null },
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(bodyText),
  } as unknown as Response;
};

const mockFetch = jest.fn<Promise<Response>, [RequestInfo | URL, RequestInit?]>();

beforeAll(() => {
  global.fetch = mockFetch as typeof fetch;
  // Ensure environment variable is set for all tests
  process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
});

afterEach(() => {
  mockFetch.mockReset();
});

// Dynamically import to pick up the env variable set above
import {
  ApiError,
  handleApiError,
  fetcher,
  createJob,
  getJob,
  listJobs,
  pauseJob,
  resumeJob,
  cancelJob,
  restartJob,
  listChapters,
  getChapter,
  updateChapter,
  getCover,
  approveCover,
  reviseCover,
  getProviders,
  getChapters,
} from "./api";

// ---------------------------------------------------------------------------
// ApiError
// ---------------------------------------------------------------------------

describe("ApiError", () => {
  it("exposes code, statusCode, and detail", () => {
    const detail = { error: "Not found", code: "JOB_NOT_FOUND" };
    const err = new ApiError(detail, 404);
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("ApiError");
    expect(err.message).toBe("Not found");
    expect(err.code).toBe("JOB_NOT_FOUND");
    expect(err.statusCode).toBe(404);
    expect(err.detail).toEqual(detail);
  });
});

// ---------------------------------------------------------------------------
// handleApiError
// ---------------------------------------------------------------------------

describe("handleApiError", () => {
  it("throws ApiError from FastAPI detail envelope", async () => {
    const resp = makeFetchResponse(
      { detail: { error: "Job not found", code: "JOB_NOT_FOUND" } },
      404,
    );
    await expect(handleApiError(resp)).rejects.toMatchObject({
      code: "JOB_NOT_FOUND",
      statusCode: 404,
    });
  });

  it("throws ApiError from direct error body", async () => {
    const resp = makeFetchResponse({ error: "Conflict", code: "STATE_CONFLICT" }, 409);
    await expect(handleApiError(resp)).rejects.toMatchObject({
      code: "STATE_CONFLICT",
      statusCode: 409,
    });
  });

  it("synthesises HTTP_ERROR when body cannot be parsed as structured error", async () => {
    const resp = makeFetchResponse({ message: "oops" }, 500);
    await expect(handleApiError(resp)).rejects.toMatchObject({
      code: "HTTP_ERROR",
      statusCode: 500,
    });
  });

  it("synthesises HTTP_ERROR when body is not JSON", async () => {
    const resp = {
      ok: false,
      status: 502,
      json: () => Promise.reject(new SyntaxError("not json")),
    } as unknown as Response;
    await expect(handleApiError(resp)).rejects.toMatchObject({
      code: "HTTP_ERROR",
      statusCode: 502,
    });
  });
});

// ---------------------------------------------------------------------------
// fetcher
// ---------------------------------------------------------------------------

describe("fetcher", () => {
  it("returns parsed JSON on 200", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ hello: "world" }, 200));
    const result = await fetcher("http://localhost:8000/test");
    expect(result).toEqual({ hello: "world" });
  });

  it("throws ApiError on non-OK response", async () => {
    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({ error: "Forbidden", code: "FORBIDDEN" }, 403),
    );
    await expect(fetcher("http://localhost:8000/test")).rejects.toBeInstanceOf(ApiError);
  });

  it("forwards options to fetch", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({}, 200));
    await fetcher("http://localhost:8000/test", { method: "POST" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/test",
      { method: "POST" },
    );
  });
});

// ---------------------------------------------------------------------------
// Jobs — createJob
// ---------------------------------------------------------------------------

describe("createJob", () => {
  it("posts to /v1/jobs", async () => {
    const response = { job_id: "abc", status: "queued", ws_url: "ws://..." };
    mockFetch.mockResolvedValueOnce(makeFetchResponse(response, 201));

    const body = {
      title: "My Book",
      topic: "AI",
      mode: "non_fiction" as const,
      audience: "Engineers",
      tone: "Formal",
      target_chapters: 10,
      llm: { provider: "anthropic" as const, model: "claude-sonnet-4-6", api_key: "sk-x" },
      image: { provider: "dall-e-3" as const, api_key: "sk-img" },
    };

    await createJob(body);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/jobs",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("serialises body as JSON", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ job_id: "x", status: "queued", ws_url: "" }, 201));
    const body = {
      title: "T",
      topic: "Top",
      mode: "fiction" as const,
      audience: "All",
      tone: "Casual",
      target_chapters: 3,
      llm: { provider: "openai" as const, model: "gpt-4o", api_key: "k" },
      image: { provider: "replicate-flux" as const, api_key: "r" },
    };
    await createJob(body);
    const [, options] = mockFetch.mock.calls[0];
    expect(options?.body).toBe(JSON.stringify(body));
  });
});

// ---------------------------------------------------------------------------
// Jobs — getJob
// ---------------------------------------------------------------------------

describe("getJob", () => {
  it("calls GET /v1/jobs/{jobId}", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ id: "job-1" }, 200));
    await getJob("job-1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/jobs/job-1",
      undefined,
    );
  });
});

// ---------------------------------------------------------------------------
// Jobs — listJobs
// ---------------------------------------------------------------------------

describe("listJobs", () => {
  it("calls GET /v1/jobs without params", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ jobs: [], total: 0, page: 1, limit: 20 }));
    await listJobs();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/jobs",
      undefined,
    );
  });

  it("appends status query parameter", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ jobs: [], total: 0, page: 1, limit: 20 }));
    await listJobs({ status: "running" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/jobs?status=running",
      undefined,
    );
  });

  it("appends page and limit query parameters", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ jobs: [], total: 0, page: 2, limit: 10 }));
    await listJobs({ page: 2, limit: 10 });
    const [url] = mockFetch.mock.calls[0];
    expect(String(url)).toContain("page=2");
    expect(String(url)).toContain("limit=10");
  });
});

// ---------------------------------------------------------------------------
// Jobs — pauseJob
// ---------------------------------------------------------------------------

describe("pauseJob", () => {
  it("calls PATCH /v1/jobs/{jobId}/pause", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ id: "j1", status: "paused" }));
    await pauseJob("j1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/jobs/j1/pause",
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});

// ---------------------------------------------------------------------------
// Jobs — resumeJob
// ---------------------------------------------------------------------------

describe("resumeJob", () => {
  it("calls PATCH /v1/jobs/{jobId}/resume", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ id: "j1", status: "queued" }));
    await resumeJob("j1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/jobs/j1/resume",
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});

// ---------------------------------------------------------------------------
// Jobs — cancelJob
// ---------------------------------------------------------------------------

describe("cancelJob", () => {
  it("calls DELETE /v1/jobs/{jobId}", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204 } as Response);
    await cancelJob("j1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/jobs/j1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("does not attempt to parse the 204 body", async () => {
    const jsonSpy = jest.fn();
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204, json: jsonSpy } as unknown as Response);
    await cancelJob("j1");
    expect(jsonSpy).not.toHaveBeenCalled();
  });

  it("throws ApiError on non-OK response", async () => {
    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({ error: "Job not found", code: "JOB_NOT_FOUND" }, 404),
    );
    await expect(cancelJob("j1")).rejects.toBeInstanceOf(ApiError);
  });
});

// ---------------------------------------------------------------------------
// Jobs — restartJob
// ---------------------------------------------------------------------------

describe("restartJob", () => {
  it("calls POST /v1/jobs/{jobId}/restart", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ new_job_id: "j2" }, 201));
    await restartJob("j1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/jobs/j1/restart",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("returns new_job_id in response", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ new_job_id: "j99" }, 201));
    const result = await restartJob("j1");
    expect(result.new_job_id).toBe("j99");
  });
});

// ---------------------------------------------------------------------------
// Chapters — listChapters
// ---------------------------------------------------------------------------

describe("listChapters", () => {
  it("calls GET /jobs/{jobId}/chapters (no /v1 prefix)", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ chapters: [] }));
    await listChapters("job-1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/jobs/job-1/chapters",
      undefined,
    );
  });

  it("returns chapters array", async () => {
    const chapters = [{ index: 0, status: "complete", qa_score: 4.2, content_preview: "..." }];
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ chapters }));
    const result = await listChapters("job-1");
    expect(result.chapters).toEqual(chapters);
  });
});

// ---------------------------------------------------------------------------
// Chapters — getChapter
// ---------------------------------------------------------------------------

describe("getChapter", () => {
  it("calls GET /jobs/{jobId}/chapters/{index} (no /v1 prefix)", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ index: 0, content: "text", status: "complete", job_id: "j1", qa_score: null, flesch_kincaid_grade: null, flesch_reading_ease: null }));
    await getChapter("j1", 0);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/jobs/j1/chapters/0",
      undefined,
    );
  });

  it("uses the integer index in the path, not a UUID", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ index: 3, content: "c", status: "locked", job_id: "j2", qa_score: null, flesch_kincaid_grade: null, flesch_reading_ease: null }));
    await getChapter("j2", 3);
    const [url] = mockFetch.mock.calls[0];
    expect(String(url)).toMatch(/\/chapters\/3$/);
  });
});

// ---------------------------------------------------------------------------
// Chapters — updateChapter
// ---------------------------------------------------------------------------

describe("updateChapter", () => {
  it("calls PATCH /jobs/{jobId}/chapters/{index} (PATCH, not PUT; no /v1 prefix)", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ job_id: "j1", index: 2, status: "locked" }));
    await updateChapter("j1", 2, "new content");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/jobs/j1/chapters/2",
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("sends content in request body", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ job_id: "j1", index: 0, status: "locked" }));
    await updateChapter("j1", 0, "hello world");
    const [, options] = mockFetch.mock.calls[0];
    expect(options?.body).toBe(JSON.stringify({ content: "hello world" }));
  });

  it("sends Content-Type: application/json", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ job_id: "j1", index: 0, status: "locked" }));
    await updateChapter("j1", 0, "text");
    const [, options] = mockFetch.mock.calls[0];
    expect((options?.headers as Record<string, string>)?.["Content-Type"]).toBe("application/json");
  });
});

// ---------------------------------------------------------------------------
// Cover — getCover
// ---------------------------------------------------------------------------

describe("getCover", () => {
  it("calls GET /jobs/{jobId}/cover (no /v1 prefix)", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ job_id: "j1", cover_url: null, cover_status: null }));
    await getCover("j1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/jobs/j1/cover",
      undefined,
    );
  });
});

// ---------------------------------------------------------------------------
// Cover — approveCover
// ---------------------------------------------------------------------------

describe("approveCover", () => {
  it("calls POST /jobs/{jobId}/cover/approve (no /v1 prefix)", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ job_id: "j1", status: "assembling" }));
    await approveCover("j1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/jobs/j1/cover/approve",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

// ---------------------------------------------------------------------------
// Cover — reviseCover
// ---------------------------------------------------------------------------

describe("reviseCover", () => {
  it("calls POST /jobs/{jobId}/cover/revise (no /v1 prefix)", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ job_id: "j1", cover_status: "revising" }));
    await reviseCover("j1", "darker background");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/jobs/j1/cover/revise",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("sends feedback in request body", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ job_id: "j1", cover_status: "revising" }));
    await reviseCover("j1", "more trees");
    const [, options] = mockFetch.mock.calls[0];
    expect(options?.body).toBe(JSON.stringify({ feedback: "more trees" }));
  });
});

// ---------------------------------------------------------------------------
// Config — getProviders
// ---------------------------------------------------------------------------

describe("getProviders", () => {
  it("calls GET /v1/config/providers", async () => {
    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({ llm_providers: ["anthropic"], image_providers: ["dall-e-3"] }),
    );
    await getProviders();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/config/providers",
      undefined,
    );
  });

  it("returns provider lists", async () => {
    const providers = { llm_providers: ["anthropic", "openai"], image_providers: ["dall-e-3"] };
    mockFetch.mockResolvedValueOnce(makeFetchResponse(providers));
    const result = await getProviders();
    expect(result).toEqual(providers);
  });
});

// ---------------------------------------------------------------------------
// Legacy alias — getChapters
// ---------------------------------------------------------------------------

describe("getChapters (legacy alias)", () => {
  it("unwraps the chapters array from the response envelope", async () => {
    const chapters = [{ index: 0, status: "complete", qa_score: null, content_preview: "..." }];
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ chapters }));
    const result = await getChapters("j1");
    expect(result).toEqual(chapters);
  });

  it("uses the same /jobs/{jobId}/chapters path as listChapters", async () => {
    mockFetch.mockResolvedValueOnce(makeFetchResponse({ chapters: [] }));
    await getChapters("j2");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/jobs/j2/chapters",
      undefined,
    );
  });
});

// ---------------------------------------------------------------------------
// Error propagation on network failure
// ---------------------------------------------------------------------------

describe("network failure handling", () => {
  it("propagates fetch rejection as-is (not wrapped in ApiError)", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(getJob("j1")).rejects.toBeInstanceOf(TypeError);
  });
});
