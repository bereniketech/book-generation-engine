---
task: 015
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: web-frontend-expert
depends_on: [012]
---

# Task 015: React/Next.js Frontend — Job Creator

## Skills
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/rules/common/coding-style.md

## Agents
- @web-frontend-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Scaffold the Next.js frontend in `frontend/` and implement the Job Creator form — all fields, provider config panel, form submission to `POST /v1/jobs`, inline validation error display, and navigation to the Book Editor on success.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `frontend/package.json` | Next.js project dependencies |
| `frontend/next.config.js` | Next.js config with API proxy |
| `frontend/app/layout.tsx` | Root layout |
| `frontend/app/page.tsx` | Home page — renders JobCreatorForm |
| `frontend/app/jobs/[id]/page.tsx` | Book Editor page (stub — implemented in task-016) |
| `frontend/components/JobCreatorForm.tsx` | Full job creation form |
| `frontend/components/ProviderConfigPanel.tsx` | LLM + image provider dropdowns + model + API key |
| `frontend/lib/api.ts` | API client (fetch wrapper for /v1/* endpoints) |
| `frontend/types/job.ts` | TypeScript types for job API |

---

## Dependencies

```bash
cd frontend
npx create-next-app@14 . --typescript --tailwind --app --no-src-dir --import-alias "@/*"
npm install react-hook-form zod @hookform/resolvers
```

---

## Code Templates

### `frontend/types/job.ts` (create this file exactly)
```typescript
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
```

### `frontend/lib/api.ts` (create this file exactly)
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function createJob(body: import("@/types/job").JobCreateRequest): Promise<import("@/types/job").JobCreateResponse> {
  const res = await fetch(`${API_BASE}/v1/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const error = await res.json();
    throw { status: res.status, detail: error };
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/v1/jobs/${jobId}`);
  if (!res.ok) throw new Error("Job not found");
  return res.json();
}

export async function getChapters(jobId: string): Promise<Record<string, unknown>[]> {
  const res = await fetch(`${API_BASE}/v1/jobs/${jobId}/chapters`);
  if (!res.ok) throw new Error("Failed to fetch chapters");
  return res.json();
}

export async function updateChapter(chapterId: string, content: string): Promise<void> {
  await fetch(`${API_BASE}/v1/chapters/${chapterId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

export async function lockChapter(chapterId: string): Promise<void> {
  await fetch(`${API_BASE}/v1/chapters/${chapterId}/lock`, { method: "POST" });
}

export async function regenerateChapter(chapterId: string): Promise<void> {
  await fetch(`${API_BASE}/v1/chapters/${chapterId}/regenerate`, { method: "POST" });
}

export async function getExport(jobId: string): Promise<{ download_url: string; files: string[] }> {
  const res = await fetch(`${API_BASE}/v1/jobs/${jobId}/export`);
  if (!res.ok) throw new Error("Export not ready");
  return res.json();
}
```

### `frontend/components/ProviderConfigPanel.tsx` (create this file exactly)
```typescript
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
```

### `frontend/components/JobCreatorForm.tsx` (create this file exactly)
```typescript
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import type { JobCreateRequest } from "@/types/job";
import { createJob } from "@/lib/api";
import { ProviderConfigPanel } from "./ProviderConfigPanel";

export function JobCreatorForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<JobCreateRequest>({
    defaultValues: {
      mode: "fiction",
      target_chapters: 12,
      llm: { provider: "anthropic", model: "claude-sonnet-4-6" },
      image: { provider: "dall-e-3" },
    },
  });

  const onSubmit = async (data: JobCreateRequest) => {
    setSubmitting(true);
    setApiError(null);
    try {
      const response = await createJob(data);
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
          {...register("title", { required: "Title is required", maxLength: { value: 500, message: "Max 500 characters" } })}
          className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
          placeholder="The Iron Path"
        />
        {errors.title && <p className="text-red-400 text-xs mt-1">{errors.title.message}</p>}
      </div>

      <div>
        <label className="block text-sm text-gray-300 mb-1">Topic / Idea</label>
        <textarea
          {...register("topic", { required: "Topic is required", maxLength: { value: 2000, message: "Max 2000 characters" } })}
          className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600 h-24"
          placeholder="A warrior's journey toward redemption through stoic philosophy..."
        />
        {errors.topic && <p className="text-red-400 text-xs mt-1">{errors.topic.message}</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Mode</label>
          <select {...register("mode")} className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600">
            <option value="fiction">Fiction</option>
            <option value="non_fiction">Non-Fiction</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-300 mb-1">Target Chapters</label>
          <input
            type="number"
            {...register("target_chapters", { min: 3, max: 50, valueAsNumber: true })}
            className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Target Audience</label>
          <input
            {...register("audience", { required: "Audience is required" })}
            className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
            placeholder="Adults aged 30-50"
          />
          {errors.audience && <p className="text-red-400 text-xs mt-1">{errors.audience.message}</p>}
        </div>
        <div>
          <label className="block text-sm text-gray-300 mb-1">Tone</label>
          <input
            {...register("tone", { required: "Tone is required" })}
            className="w-full bg-gray-800 text-white rounded px-3 py-2 border border-gray-600"
            placeholder="Authoritative yet accessible"
          />
          {errors.tone && <p className="text-red-400 text-xs mt-1">{errors.tone.message}</p>}
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
```

### `frontend/app/page.tsx` (create this file exactly)
```typescript
import { JobCreatorForm } from "@/components/JobCreatorForm";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gray-900 py-12 px-4">
      <JobCreatorForm />
    </main>
  );
}
```

### `frontend/app/jobs/[id]/page.tsx` (create this file exactly — stub)
```typescript
export default function BookEditorPage({ params }: { params: { id: string } }) {
  return (
    <main className="min-h-screen bg-gray-900 p-8">
      <p className="text-white">Book Editor for job {params.id} — implemented in task-016.</p>
    </main>
  );
}
```

---

## Codebase Context

### Key Patterns in Use
- **`react-hook-form` for all form state:** No `useState` for individual field values. All field registration via `register()`.
- **Inline errors from `formState.errors`:** One `<p className="text-red-400">` per field directly below the input.
- **API error displayed as banner:** Global `apiError` state shown at top of form when API returns non-2xx.
- **Navigate on success:** `router.push(\`/jobs/${response.job_id}\`)` — never use `window.location.href`.
- **Design tokens:** Background `bg-gray-900`, surface `bg-gray-800`, accent `bg-red-600`, text `text-white`.

### Architecture Decisions Affecting This Task
- `NEXT_PUBLIC_API_URL` env var points to FastAPI backend. Default `http://localhost:8000` for development.
- API keys are transmitted over HTTPS. The form uses `type="password"` for all API key inputs to prevent shoulder-surfing.

---

## Handoff from Previous Task

**Files changed by previous task:** `app/services/email_service.py`, `app/config.py` (SMTP fields added).
**Decisions made:** Email retry pattern. Config via pydantic-settings.
**Context for this task:** Backend is feature-complete. Now build the React frontend starting with Job Creator.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Run: `cd C:/Users/Hp/Desktop/Experiment/book-generation-engine/frontend && npx create-next-app@14 . --typescript --tailwind --app --no-src-dir --import-alias "@/*" --yes`
2. Run: `cd C:/Users/Hp/Desktop/Experiment/book-generation-engine/frontend && npm install react-hook-form zod @hookform/resolvers`
3. Create `frontend/types/job.ts` — paste template exactly.
4. Create `frontend/lib/api.ts` — paste template exactly.
5. Create `frontend/components/ProviderConfigPanel.tsx` — paste template exactly.
6. Create `frontend/components/JobCreatorForm.tsx` — paste template exactly.
7. Overwrite `frontend/app/page.tsx` — paste template exactly.
8. Create `frontend/app/jobs/[id]/page.tsx` — paste template exactly.
9. Run: `cd C:/Users/Hp/Desktop/Experiment/book-generation-engine/frontend && npm run build` — verify zero build errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| API returns 422 | Display `apiError` banner at top of form with `"Submission failed. Check your inputs and try again."` |
| `createJob()` returns `job_id` | Call `router.push(\`/jobs/${response.job_id}\`)` |
| `target_chapters` outside range 3-50 | `react-hook-form` `min`/`max` validation — field-level error shown |
| LLM API key field is empty | `required` validation — error: `"LLM API key is required"` |

---

## Acceptance Criteria

- [ ] WHEN `npm run build` runs in `frontend/` THEN zero errors
- [ ] WHEN the form is submitted with missing required fields THEN inline errors appear
- [ ] WHEN the form submits successfully THEN navigation goes to `/jobs/{job_id}`
- [ ] WHEN API returns an error THEN error banner appears at top of form

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_
