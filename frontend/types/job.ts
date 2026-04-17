export type LLMProvider = "anthropic" | "openai" | "google" | "ollama" | "openai-compatible";
export type ImageProvider = "dall-e-3" | "replicate-flux";
export type JobMode = "fiction" | "non_fiction";

export interface LLMProviderConfig {
  provider: LLMProvider;
  model: string;
  api_key: string;
  base_url?: string;
}

export interface ImageProviderConfig {
  provider: ImageProvider;
  api_key: string;
}

export interface JobCreateRequest {
  title: string;
  topic: string;
  mode: JobMode;
  audience: string;
  tone: string;
  target_chapters: number;
  llm: LLMProviderConfig;
  image: ImageProviderConfig;
  notification_email?: string;
}

export interface JobCreateResponse {
  job_id: string;
  status: string;
  ws_url: string;
}
