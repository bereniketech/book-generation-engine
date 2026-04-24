/**
 * Job-related TypeScript types.
 *
 * JobCreateInput and its sub-types are derived from the Zod schema in
 * frontend/lib/validation.ts — do not re-declare them here.
 */

// Re-export the canonical input types from the Zod schema.
export type {
  JobCreateInput as JobCreateRequest,
  LLMProviderInput as LLMProviderConfig,
  ImageProviderInput as ImageProviderConfig,
} from "@/lib/validation";

// Convenience type aliases for provider and mode literals.
export type LLMProvider =
  | "anthropic"
  | "openai"
  | "google"
  | "ollama"
  | "openai-compatible";

export type ImageProvider = "dall-e-3" | "replicate-flux";

export type JobMode = "fiction" | "non_fiction";

// Response shape returned by POST /v1/jobs.
export interface JobCreateResponse {
  job_id: string;
  status: string;
  ws_url: string;
}
