/**
 * Unit tests for frontend/lib/generated/job_schema.ts (JobCreateSchema and sub-schemas).
 *
 * Constraint reference (auto-generated from app/domain/validation_schemas.py):
 *   title            : min 1, max 500
 *   topic            : min 1, max 2000
 *   mode             : fiction | non_fiction
 *   audience         : min 1, max 500
 *   tone             : min 1, max 200
 *   target_chapters  : int, min 3, max 50
 *   llm.model        : min 1, max 200
 *   llm.api_key      : min 1, max 500
 *   image.api_key    : min 1, max 500
 *   notification_email: optional valid email
 */
import {
  JobCreateSchema,
  LLMProviderSchema,
  ImageProviderSchema,
} from "./generated/job_schema";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function validLLM() {
  return { provider: "anthropic" as const, model: "claude-sonnet-4-6", api_key: "sk-test" };
}

function validImage() {
  return { provider: "dall-e-3" as const, api_key: "sk-img" };
}

function validPayload(overrides: Record<string, unknown> = {}) {
  return {
    title: "Test Book",
    topic: "A test topic",
    mode: "fiction" as const,
    audience: "Adults",
    tone: "Formal",
    target_chapters: 12,
    llm: validLLM(),
    image: validImage(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// LLMProviderSchema
// ---------------------------------------------------------------------------

describe("LLMProviderSchema", () => {
  it("accepts all valid providers", () => {
    const providers = ["anthropic", "openai", "google", "ollama", "openai-compatible"] as const;
    for (const provider of providers) {
      const result = LLMProviderSchema.safeParse({ ...validLLM(), provider });
      expect(result.success).toBe(true);
    }
  });

  it("rejects an unsupported provider", () => {
    const result = LLMProviderSchema.safeParse({ ...validLLM(), provider: "mistral" });
    expect(result.success).toBe(false);
  });

  it("rejects empty model string", () => {
    const result = LLMProviderSchema.safeParse({ ...validLLM(), model: "" });
    expect(result.success).toBe(false);
  });

  it("accepts model at max boundary (200 chars)", () => {
    const result = LLMProviderSchema.safeParse({ ...validLLM(), model: "m".repeat(200) });
    expect(result.success).toBe(true);
  });

  it("rejects model exceeding 200 chars", () => {
    const result = LLMProviderSchema.safeParse({ ...validLLM(), model: "m".repeat(201) });
    expect(result.success).toBe(false);
  });

  it("accepts api_key at max boundary (500 chars)", () => {
    const result = LLMProviderSchema.safeParse({ ...validLLM(), api_key: "k".repeat(500) });
    expect(result.success).toBe(true);
  });

  it("rejects api_key exceeding 500 chars", () => {
    const result = LLMProviderSchema.safeParse({ ...validLLM(), api_key: "k".repeat(501) });
    expect(result.success).toBe(false);
  });

  it("accepts base_url when omitted (optional)", () => {
    const { base_url: _removed, ...without } = { ...validLLM(), base_url: undefined };
    const result = LLMProviderSchema.safeParse(without);
    expect(result.success).toBe(true);
  });

  it("accepts base_url when provided", () => {
    const result = LLMProviderSchema.safeParse({ ...validLLM(), base_url: "http://localhost:11434" });
    expect(result.success).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// ImageProviderSchema
// ---------------------------------------------------------------------------

describe("ImageProviderSchema", () => {
  it("accepts dall-e-3", () => {
    const result = ImageProviderSchema.safeParse(validImage());
    expect(result.success).toBe(true);
  });

  it("accepts replicate-flux", () => {
    const result = ImageProviderSchema.safeParse({ provider: "replicate-flux", api_key: "r" });
    expect(result.success).toBe(true);
  });

  it("rejects unsupported image provider", () => {
    const result = ImageProviderSchema.safeParse({ provider: "midjourney", api_key: "k" });
    expect(result.success).toBe(false);
  });

  it("rejects empty api_key", () => {
    const result = ImageProviderSchema.safeParse({ provider: "dall-e-3", api_key: "" });
    expect(result.success).toBe(false);
  });

  it("accepts api_key at max boundary (500 chars)", () => {
    const result = ImageProviderSchema.safeParse({ provider: "dall-e-3", api_key: "k".repeat(500) });
    expect(result.success).toBe(true);
  });

  it("rejects api_key exceeding 500 chars", () => {
    const result = ImageProviderSchema.safeParse({ provider: "dall-e-3", api_key: "k".repeat(501) });
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// JobCreateSchema — title
// ---------------------------------------------------------------------------

describe("JobCreateSchema — title", () => {
  it("rejects empty title", () => {
    const result = JobCreateSchema.safeParse(validPayload({ title: "" }));
    expect(result.success).toBe(false);
  });

  it("accepts title at max boundary (500 chars)", () => {
    const result = JobCreateSchema.safeParse(validPayload({ title: "t".repeat(500) }));
    expect(result.success).toBe(true);
  });

  it("rejects title exceeding 500 chars", () => {
    const result = JobCreateSchema.safeParse(validPayload({ title: "t".repeat(501) }));
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// JobCreateSchema — topic
// ---------------------------------------------------------------------------

describe("JobCreateSchema — topic", () => {
  it("rejects empty topic", () => {
    const result = JobCreateSchema.safeParse(validPayload({ topic: "" }));
    expect(result.success).toBe(false);
  });

  it("accepts topic at max boundary (2000 chars)", () => {
    const result = JobCreateSchema.safeParse(validPayload({ topic: "t".repeat(2000) }));
    expect(result.success).toBe(true);
  });

  it("rejects topic exceeding 2000 chars", () => {
    const result = JobCreateSchema.safeParse(validPayload({ topic: "t".repeat(2001) }));
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// JobCreateSchema — audience
// ---------------------------------------------------------------------------

describe("JobCreateSchema — audience", () => {
  it("rejects empty audience", () => {
    const result = JobCreateSchema.safeParse(validPayload({ audience: "" }));
    expect(result.success).toBe(false);
  });

  it("accepts audience at max boundary (500 chars)", () => {
    const result = JobCreateSchema.safeParse(validPayload({ audience: "a".repeat(500) }));
    expect(result.success).toBe(true);
  });

  it("rejects audience exceeding 500 chars", () => {
    const result = JobCreateSchema.safeParse(validPayload({ audience: "a".repeat(501) }));
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// JobCreateSchema — tone
// ---------------------------------------------------------------------------

describe("JobCreateSchema — tone", () => {
  it("rejects empty tone", () => {
    const result = JobCreateSchema.safeParse(validPayload({ tone: "" }));
    expect(result.success).toBe(false);
  });

  it("accepts tone at max boundary (200 chars)", () => {
    const result = JobCreateSchema.safeParse(validPayload({ tone: "t".repeat(200) }));
    expect(result.success).toBe(true);
  });

  it("rejects tone exceeding 200 chars", () => {
    const result = JobCreateSchema.safeParse(validPayload({ tone: "t".repeat(201) }));
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// JobCreateSchema — target_chapters
// ---------------------------------------------------------------------------

describe("JobCreateSchema — target_chapters", () => {
  it("accepts minimum value of 3", () => {
    const result = JobCreateSchema.safeParse(validPayload({ target_chapters: 3 }));
    expect(result.success).toBe(true);
  });

  it("rejects value below minimum (2)", () => {
    const result = JobCreateSchema.safeParse(validPayload({ target_chapters: 2 }));
    expect(result.success).toBe(false);
  });

  it("accepts maximum value of 50", () => {
    const result = JobCreateSchema.safeParse(validPayload({ target_chapters: 50 }));
    expect(result.success).toBe(true);
  });

  it("rejects value above maximum (51)", () => {
    const result = JobCreateSchema.safeParse(validPayload({ target_chapters: 51 }));
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// JobCreateSchema — mode
// ---------------------------------------------------------------------------

describe("JobCreateSchema — mode", () => {
  it("accepts fiction", () => {
    const result = JobCreateSchema.safeParse(validPayload({ mode: "fiction" }));
    expect(result.success).toBe(true);
  });

  it("accepts non_fiction", () => {
    const result = JobCreateSchema.safeParse(validPayload({ mode: "non_fiction" }));
    expect(result.success).toBe(true);
  });

  it("rejects invalid mode", () => {
    const result = JobCreateSchema.safeParse(validPayload({ mode: "biography" }));
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// JobCreateSchema — notification_email
// ---------------------------------------------------------------------------

describe("JobCreateSchema — notification_email", () => {
  it("accepts missing notification_email (optional)", () => {
    const payload = validPayload();
    delete (payload as Record<string, unknown>).notification_email;
    const result = JobCreateSchema.safeParse(payload);
    expect(result.success).toBe(true);
  });

  it("accepts empty string for notification_email (treated as absent)", () => {
    const result = JobCreateSchema.safeParse(validPayload({ notification_email: "" }));
    expect(result.success).toBe(true);
  });

  it("accepts a valid email", () => {
    const result = JobCreateSchema.safeParse(validPayload({ notification_email: "user@example.com" }));
    expect(result.success).toBe(true);
  });

  it("rejects an invalid email string", () => {
    const result = JobCreateSchema.safeParse(validPayload({ notification_email: "not-an-email" }));
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Full valid payload
// ---------------------------------------------------------------------------

describe("JobCreateSchema — full valid payload", () => {
  it("parses a complete valid payload without errors", () => {
    const result = JobCreateSchema.safeParse(validPayload({ notification_email: "test@example.com" }));
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.title).toBe("Test Book");
      expect(result.data.llm.provider).toBe("anthropic");
      expect(result.data.image.provider).toBe("dall-e-3");
    }
  });
});
