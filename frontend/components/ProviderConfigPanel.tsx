"use client";

import { useEffect, useState } from "react";
import { UseFormRegister, FieldErrors } from "react-hook-form";
import type { JobCreateRequest } from "@/types/job";
import { getProviders } from "@/lib/config";

interface Props {
  register: UseFormRegister<JobCreateRequest>;
  errors: FieldErrors<JobCreateRequest>;
}

interface ProviderState {
  llmProviders: string[];
  imageProviders: string[];
  loading: boolean;
  error: string | null;
}

const INITIAL_STATE: ProviderState = {
  llmProviders: [],
  imageProviders: [],
  loading: true,
  error: null,
};

export function ProviderConfigPanel({ register, errors }: Props) {
  const [state, setState] = useState<ProviderState>(INITIAL_STATE);

  useEffect(() => {
    let cancelled = false;

    getProviders()
      .then((providers) => {
        if (!cancelled) {
          setState({
            llmProviders: Object.keys(providers.llm_providers),
            imageProviders: Object.keys(providers.image_providers),
            loading: false,
            error: null,
          });
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Failed to load providers";
          setState((prev) => ({ ...prev, loading: false, error: message }));
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-4 border border-gray-700 rounded-lg p-4 bg-gray-800">
      <h3 className="text-white font-semibold">Provider Configuration</h3>

      {state.error && (
        <p className="text-red-400 text-sm" role="alert">
          {state.error}
        </p>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">LLM Provider</label>
          <select
            {...register("llm.provider", { required: "LLM provider is required" })}
            disabled={state.loading}
            className="w-full bg-gray-700 text-white rounded px-3 py-2 border border-gray-600 disabled:opacity-50"
          >
            {state.loading ? (
              <option value="">Loading providers…</option>
            ) : (
              state.llmProviders.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))
            )}
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
            disabled={state.loading}
            className="w-full bg-gray-700 text-white rounded px-3 py-2 border border-gray-600 disabled:opacity-50"
          >
            {state.loading ? (
              <option value="">Loading providers…</option>
            ) : (
              state.imageProviders.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))
            )}
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
