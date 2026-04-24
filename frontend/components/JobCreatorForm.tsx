"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { JobCreateSchema, type JobCreateInput } from "@/lib/validation";
import { createJob } from "@/lib/api";
import { getProviders } from "@/lib/config";
import { ProviderConfigPanel } from "./ProviderConfigPanel";

export function JobCreatorForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<JobCreateInput>({
    resolver: zodResolver(JobCreateSchema),
    defaultValues: {
      mode: "fiction",
      target_chapters: 12,
      llm: { provider: "anthropic", model: "" },
      image: { provider: "dall-e-3" },
    },
  });

  // Initialize model defaults from config endpoint
  useEffect(() => {
    getProviders()
      .then((providers) => {
        reset({
          mode: "fiction",
          target_chapters: 12,
          llm: {
            provider: "anthropic",
            model: providers.llm_providers.anthropic?.default_model || "claude-sonnet-4-6",
          },
          image: {
            provider: "dall-e-3",
          },
        });
      })
      .catch(() => {
        // If config fails, form stays with empty model field
        // User will see placeholder and can enter manually
      });
  }, [reset]);

  const onSubmit = async (data: JobCreateInput) => {
    setSubmitting(true);
    setApiError(null);
    // Normalise empty notification_email string to undefined before sending.
    const payload = {
      ...data,
      notification_email: data.notification_email || undefined,
    };
    try {
      const response = await createJob(payload);
      router.push(`/jobs/${response.job_id}`);
    } catch (err: unknown) {
      const e = err as { detail?: { detail?: string } };
      setApiError(e?.detail?.detail || "Submission failed. Check your inputs and try again.");
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-white">Create a New Book</h1>

      {apiError && (
        <div className="bg-red-900 border border-red-500 text-red-200 rounded p-3 text-sm">
          {apiError}
        </div>
      )}

      <div>
        <label className="block text-sm text-gray-300 mb-1">Book Title</label>
        <input
          {...register("title")}
          className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
          placeholder="The Iron Path"
        />
        {errors.title && (
          <p className="text-red-400 text-xs mt-1">{errors.title.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm text-gray-300 mb-1">Topic / Idea</label>
        <textarea
          {...register("topic")}
          className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600 h-24"
          placeholder="A warrior's journey toward redemption through stoic philosophy..."
        />
        {errors.topic && (
          <p className="text-red-400 text-xs mt-1">{errors.topic.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Mode</label>
          <select
            {...register("mode")}
            className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
          >
            <option value="fiction">Fiction</option>
            <option value="non_fiction">Non-Fiction</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-300 mb-1">Target Chapters</label>
          <input
            type="number"
            {...register("target_chapters", { valueAsNumber: true })}
            className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
          />
          {errors.target_chapters && (
            <p className="text-red-400 text-xs mt-1">{errors.target_chapters.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Target Audience</label>
          <input
            {...register("audience")}
            className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
            placeholder="Adults aged 30-50"
          />
          {errors.audience && (
            <p className="text-red-400 text-xs mt-1">{errors.audience.message}</p>
          )}
        </div>
        <div>
          <label className="block text-sm text-gray-300 mb-1">Tone</label>
          <input
            {...register("tone")}
            className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
            placeholder="Authoritative yet accessible"
          />
          {errors.tone && (
            <p className="text-red-400 text-xs mt-1">{errors.tone.message}</p>
          )}
        </div>
      </div>

      <ProviderConfigPanel register={register} errors={errors} />

      <div>
        <label className="block text-sm text-gray-300 mb-1">Notification Email (optional)</label>
        <input
          {...register("notification_email")}
          type="email"
          className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
          placeholder="you@example.com"
        />
        {errors.notification_email && (
          <p className="text-red-400 text-xs mt-1">{errors.notification_email.message}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="w-full bg-red-600 hover:bg-red-700 disabled:bg-gray-600 text-white font-semibold py-3 rounded transition-colors"
      >
        {submitting ? "Submitting..." : "Generate Book"}
      </button>
    </form>
  );
}
