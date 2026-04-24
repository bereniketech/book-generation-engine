/**
 * Single source of truth for job creation validation on the frontend.
 *
 * Constraints here MUST match app/domain/validation_schemas.py exactly.
 * When changing limits, update both files simultaneously.
 */
import { z } from "zod";

// ---------------------------------------------------------------------------
// Sub-schemas
// ---------------------------------------------------------------------------

export const LLM_PROVIDERS = [
  "anthropic",
  "openai",
  "google",
  "ollama",
  "openai-compatible",
] as const;

export const IMAGE_PROVIDERS = ["dall-e-3", "replicate-flux"] as const;

export const LLMProviderSchema = z.object({
  provider: z.enum(LLM_PROVIDERS, {
    error: "Provider must be one of: anthropic, openai, google, ollama, openai-compatible",
  }),
  model: z
    .string()
    .min(1, "Model name is required")
    .max(200, "Model name must be at most 200 characters"),
  api_key: z
    .string()
    .min(1, "API key is required")
    .max(500, "API key must be at most 500 characters"),
  base_url: z
    .string()
    .max(500, "Base URL must be at most 500 characters")
    .optional(),
});

export const ImageProviderSchema = z.object({
  provider: z.enum(IMAGE_PROVIDERS, {
    error: "Image provider must be one of: dall-e-3, replicate-flux",
  }),
  api_key: z
    .string()
    .min(1, "API key is required")
    .max(500, "API key must be at most 500 characters"),
});

// ---------------------------------------------------------------------------
// Main schema
// ---------------------------------------------------------------------------

export const JobCreateSchema = z.object({
  title: z
    .string()
    .min(1, "Title is required")
    .max(500, "Title must be at most 500 characters"),
  topic: z
    .string()
    .min(1, "Topic is required")
    .max(2000, "Topic must be at most 2000 characters"),
  mode: z.enum(["fiction", "non_fiction"], {
    error: "Mode must be fiction or non_fiction",
  }),
  audience: z
    .string()
    .min(1, "Target audience is required")
    .max(500, "Target audience must be at most 500 characters"),
  tone: z
    .string()
    .min(1, "Tone is required")
    .max(200, "Tone must be at most 200 characters"),
  target_chapters: z
    .number({ error: "Target chapters must be a number" })
    .int("Target chapters must be a whole number")
    .min(3, "Minimum 3 chapters")
    .max(50, "Maximum 50 chapters"),
  llm: LLMProviderSchema,
  image: ImageProviderSchema,
  notification_email: z
    .string()
    .email("Must be a valid email address")
    .optional()
    .or(z.literal("")),
});

// ---------------------------------------------------------------------------
// Derived TypeScript types — import these instead of re-declaring interfaces
// ---------------------------------------------------------------------------

export type LLMProviderInput = z.infer<typeof LLMProviderSchema>;
export type ImageProviderInput = z.infer<typeof ImageProviderSchema>;
export type JobCreateInput = z.infer<typeof JobCreateSchema>;
