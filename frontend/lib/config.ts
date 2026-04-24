/**
 * Provider configuration fetching utility.
 * Fetches the canonical list of supported LLM and image providers from the backend.
 * Results are cached in-module after the first successful fetch.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ProviderConfig {
  default_model: string;
  models?: string[];
}

export interface ProvidersResponse {
  llm_providers: Record<string, ProviderConfig>;
  image_providers: Record<string, ProviderConfig>;
}

let cachedProviders: ProvidersResponse | null = null;

/**
 * Fetch supported providers from the backend and cache the result.
 * Subsequent calls return the cached value without making a network request.
 * Throws if the request fails — callers should handle the error.
 */
export async function getProviders(): Promise<ProvidersResponse> {
  if (cachedProviders !== null) {
    return cachedProviders;
  }

  const response = await fetch(`${API_BASE}/v1/config/providers`);
  if (!response.ok) {
    throw new Error(`Failed to fetch providers: ${response.statusText}`);
  }

  const data = (await response.json()) as ProvidersResponse;

  if (!data.llm_providers || typeof data.llm_providers !== "object" ||
      !data.image_providers || typeof data.image_providers !== "object") {
    throw new Error("Invalid providers response shape from server");
  }

  cachedProviders = data;
  return cachedProviders;
}

/**
 * Clear the in-module provider cache.
 * Exposed for testing purposes only.
 */
export function _clearProvidersCache(): void {
  cachedProviders = null;
}
