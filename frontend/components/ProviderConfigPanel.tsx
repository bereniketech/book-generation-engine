"use client";

import { UseFormRegister, FieldErrors } from "react-hook-form";
import type { JobCreateRequest } from "@/types/job";

interface Props {
  register: UseFormRegister<JobCreateRequest>;
  errors: FieldErrors<JobCreateRequest>;
}

const LLM_PROVIDERS = ["anthropic", "openai", "google", "ollama", "openai-compatible"] as const;
const IMAGE_PROVIDERS = ["dall-e-3", "replicate-flux"] as const;

export function ProviderConfigPanel({ register, errors }: Props) {
  return (
    <div className="space-y-4 border border-gray-700 rounded-lg p-4 bg-gray-800">
      <h3 className="text-white font-semibold">Provider Configuration</h3>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">LLM Provider</label>
          <select
            {...register("llm.provider", { required: "LLM provider is required" })}
            className="w-full bg-gray-700 text-white rounded px-3 py-2 border border-gray-600"
          >
            {LLM_PROVIDERS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          {errors.llm?.provider && (
            <p className="text-red-400 text-xs mt-1">{errors.llm.provider.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm text-gray-300 mb-1">Model</label>
          <input
            {...register("llm.model", { required: "Model name is required" })}
            placeholder="claude-sonnet-4-6"
            className="w-full bg-gray-700 text-white rounded px-3 py-2 border border-gray-600"
          />
          {errors.llm?.model && (
            <p className="text-red-400 text-xs mt-1">{errors.llm.model.message}</p>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm text-gray-300 mb-1">LLM API Key</label>
        <input
          {...register("llm.api_key", { required: "LLM API key is required" })}
          type="password"
          placeholder="sk-..."
          className="w-full bg-gray-700 text-white rounded px-3 py-2 border border-gray-600"
        />
        {errors.llm?.api_key && (
          <p className="text-red-400 text-xs mt-1">{errors.llm.api_key.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Image Provider</label>
          <select
            {...register("image.provider", { required: "Image provider is required" })}
            className="w-full bg-gray-700 text-white rounded px-3 py-2 border border-gray-600"
          >
            {IMAGE_PROVIDERS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-300 mb-1">Image API Key</label>
          <input
            {...register("image.api_key", { required: "Image API key is required" })}
            type="password"
            placeholder="API key"
            className="w-full bg-gray-700 text-white rounded px-3 py-2 border border-gray-600"
          />
          {errors.image?.api_key && (
            <p className="text-red-400 text-xs mt-1">{errors.image.api_key.message}</p>
          )}
        </div>
      </div>
    </div>
  );
}
