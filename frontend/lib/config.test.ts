/**
 * Tests for provider configuration fetching utility.
 */
import { getProviders, _clearProvidersCache, type ProvidersResponse } from "./config";

const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

jest.mock("node-fetch");

describe("config", () => {
  beforeEach(() => {
    _clearProvidersCache();
    jest.clearAllMocks();
  });

  describe("getProviders", () => {
    it("should fetch and return providers from backend", async () => {
      const mockResponse: ProvidersResponse = {
        llm_providers: {
          anthropic: {
            default_model: "claude-sonnet-4-6",
            models: ["claude-opus", "claude-sonnet-4-6", "claude-haiku"],
          },
          openai: {
            default_model: "gpt-4-turbo",
            models: ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
          },
        },
        image_providers: {
          "dall-e-3": {
            default_model: "dall-e-3",
          },
          "replicate-flux": {
            default_model: "flux",
          },
        },
      };

      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockResponse),
        } as Response)
      );

      const result = await getProviders();

      expect(result).toEqual(mockResponse);
      expect(result.llm_providers.anthropic.default_model).toBe(
        "claude-sonnet-4-6"
      );
      expect(result.image_providers["dall-e-3"].default_model).toBe(
        "dall-e-3"
      );
    });

    it("should cache providers after first fetch", async () => {
      const mockResponse: ProvidersResponse = {
        llm_providers: {
          anthropic: { default_model: "claude-sonnet-4-6" },
        },
        image_providers: {
          "dall-e-3": { default_model: "dall-e-3" },
        },
      };

      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockResponse),
        } as Response)
      );

      const result1 = await getProviders();
      const result2 = await getProviders();

      expect(result1).toBe(result2);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it("should throw error if response is not ok", async () => {
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: false,
          statusText: "Internal Server Error",
        } as Response)
      );

      await expect(getProviders()).rejects.toThrow(
        "Failed to fetch providers"
      );
    });

    it("should throw error if response has invalid shape", async () => {
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              llm_providers: "invalid",
              image_providers: [],
            }),
        } as Response)
      );

      await expect(getProviders()).rejects.toThrow(
        "Invalid providers response shape"
      );
    });
  });
});
