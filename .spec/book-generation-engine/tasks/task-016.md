---
task: 016
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: web-frontend-expert
depends_on: [015]
---

# Task 016: React/Next.js Frontend — Book Editor

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

Implement the Book Editor view: `BookEditorView`, `ChapterCard`, `InlineEditor`, `ProgressBar`, and `StatusBadge` components. Connect a WebSocket to `/v1/ws/{job_id}` for real-time progress, and wire up chapter edit-on-blur, regenerate, and lock actions.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `frontend/components/BookEditorView.tsx` | Container: chapter list + progress + WebSocket |
| `frontend/components/ChapterCard.tsx` | Chapter content card with edit/regenerate/lock |
| `frontend/components/InlineEditor.tsx` | Contenteditable div with save-on-blur |
| `frontend/components/ProgressBar.tsx` | Shows pipeline step + percentage |
| `frontend/components/StatusBadge.tsx` | Colour-coded status pill |
| `frontend/hooks/useWebSocket.ts` | WebSocket hook with auto-reconnect |

### Modify
| File | What to change |
|------|---------------|
| `frontend/app/jobs/[id]/page.tsx` | Replace stub with `BookEditorView` |

---

## Dependencies

```bash
# No new npm packages beyond what task-015 installed.
```

---

## Code Templates

### `frontend/hooks/useWebSocket.ts` (create this file exactly)
```typescript
"use client";

import { useEffect, useRef, useState } from "react";

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/^http/, "ws");

export interface ProgressEvent {
  type: "progress" | "chapter_ready" | "complete" | "error";
  job_id: string;
  status?: string;
  step?: string;
  progress?: number;
  chapter_id?: string;
  chapter_index?: number;
  download_url?: string;
  message?: string;
}

export function useWebSocket(jobId: string) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/v1/ws/${jobId}`);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onmessage = (e) => {
        try {
          const event: ProgressEvent = JSON.parse(e.data);
          setEvents((prev) => [...prev, event]);
        } catch {
          // ignore malformed messages
        }
      };
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000); // auto-reconnect after 3s
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [jobId]);

  const latestEvent = events[events.length - 1] ?? null;
  return { events, latestEvent, connected };
}
```

### `frontend/components/StatusBadge.tsx` (create this file exactly)
```typescript
interface Props {
  status: string;
}

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-gray-600 text-gray-200",
  planning: "bg-blue-700 text-blue-100",
  generating: "bg-yellow-700 text-yellow-100",
  assembling: "bg-purple-700 text-purple-100",
  complete: "bg-green-700 text-green-100",
  failed: "bg-red-700 text-red-100",
  paused: "bg-orange-700 text-orange-100",
  locked: "bg-green-800 text-green-200",
  pending: "bg-gray-700 text-gray-300",
  qa_failed: "bg-red-800 text-red-200",
};

export function StatusBadge({ status }: Props) {
  const cls = STATUS_COLORS[status] ?? "bg-gray-600 text-gray-200";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {status.replace("_", " ")}
    </span>
  );
}
```

### `frontend/components/ProgressBar.tsx` (create this file exactly)
```typescript
interface Props {
  progress: number;  // 0-100
  step: string;
  status: string;
}

export function ProgressBar({ progress, step, status }: Props) {
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>{step || "Waiting..."}</span>
        <span>{Math.round(progress)}%</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div
          className="bg-red-500 h-2 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 mt-1">{status}</p>
    </div>
  );
}
```

### `frontend/components/InlineEditor.tsx` (create this file exactly)
```typescript
"use client";

import { useRef } from "react";

interface Props {
  initialContent: string;
  onSave: (content: string) => void;
  disabled?: boolean;
}

export function InlineEditor({ initialContent, onSave, disabled = false }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const handleBlur = () => {
    if (ref.current) {
      onSave(ref.current.innerText);
    }
  };

  return (
    <div
      ref={ref}
      contentEditable={!disabled}
      suppressContentEditableWarning
      onBlur={handleBlur}
      className={`min-h-24 p-3 rounded bg-gray-700 text-gray-100 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-red-500 whitespace-pre-wrap ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
    >
      {initialContent}
    </div>
  );
}
```

### `frontend/components/ChapterCard.tsx` (create this file exactly)
```typescript
"use client";

import { useState } from "react";
import { InlineEditor } from "./InlineEditor";
import { StatusBadge } from "./StatusBadge";
import { lockChapter, regenerateChapter, updateChapter } from "@/lib/api";

interface Chapter {
  id: string;
  index: number;
  title?: string;
  content: string;
  status: string;
}

interface Props {
  chapter: Chapter;
  onUpdate: () => void;
}

export function ChapterCard({ chapter, onUpdate }: Props) {
  const [regenerating, setRegenerating] = useState(false);
  const [locking, setLocking] = useState(false);

  const isLocked = chapter.status === "locked";

  const handleSave = async (content: string) => {
    if (isLocked) return;
    await updateChapter(chapter.id, content);
  };

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      await regenerateChapter(chapter.id);
      setTimeout(onUpdate, 3000); // Poll for updated content after brief delay
    } finally {
      setRegenerating(false);
    }
  };

  const handleLock = async () => {
    setLocking(true);
    try {
      await lockChapter(chapter.id);
      onUpdate();
    } finally {
      setLocking(false);
    }
  };

  return (
    <div className="border border-gray-700 rounded-lg p-4 space-y-3 bg-gray-800">
      <div className="flex items-center justify-between">
        <h3 className="text-white font-medium">
          Chapter {chapter.index + 1}{chapter.title ? `: ${chapter.title}` : ""}
        </h3>
        <StatusBadge status={chapter.status} />
      </div>

      <InlineEditor
        initialContent={chapter.content}
        onSave={handleSave}
        disabled={isLocked}
      />

      <div className="flex gap-2">
        {!isLocked && (
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded disabled:opacity-50 transition-colors"
          >
            {regenerating ? "Regenerating..." : "Regenerate"}
          </button>
        )}
        {!isLocked && (
          <button
            onClick={handleLock}
            disabled={locking}
            className="px-3 py-1.5 text-sm bg-green-700 hover:bg-green-600 text-white rounded disabled:opacity-50 transition-colors"
          >
            {locking ? "Locking..." : "Lock"}
          </button>
        )}
        {isLocked && (
          <span className="text-xs text-green-400 self-center">Chapter locked — editing disabled</span>
        )}
      </div>
    </div>
  );
}
```

### `frontend/components/BookEditorView.tsx` (create this file exactly)
```typescript
"use client";

import { useCallback, useEffect, useState } from "react";
import { ChapterCard } from "./ChapterCard";
import { ProgressBar } from "./ProgressBar";
import { StatusBadge } from "./StatusBadge";
import { getChapters } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";

interface Props {
  jobId: string;
}

export function BookEditorView({ jobId }: Props) {
  const [chapters, setChapters] = useState<Record<string, unknown>[]>([]);
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState("Initialising...");
  const [status, setStatus] = useState("queued");
  const { latestEvent, connected } = useWebSocket(jobId);

  const fetchChapters = useCallback(async () => {
    try {
      const data = await getChapters(jobId);
      setChapters(data);
    } catch {
      // Chapters may not exist yet during planning phase
    }
  }, [jobId]);

  useEffect(() => {
    fetchChapters();
  }, [fetchChapters]);

  useEffect(() => {
    if (!latestEvent) return;
    if (latestEvent.progress !== undefined) setProgress(latestEvent.progress);
    if (latestEvent.step) setStep(latestEvent.step);
    if (latestEvent.status) setStatus(latestEvent.status);
    if (latestEvent.type === "chapter_ready") {
      fetchChapters();
    }
    if (latestEvent.type === "complete") {
      fetchChapters();
    }
  }, [latestEvent, fetchChapters]);

  return (
    <div className="space-y-6 max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Book Editor</h1>
        <div className="flex items-center gap-3">
          <StatusBadge status={status} />
          <span className="text-xs text-gray-500">{connected ? "Live" : "Reconnecting..."}</span>
        </div>
      </div>

      <ProgressBar progress={progress} step={step} status={status} />

      {chapters.length === 0 && status !== "complete" && (
        <p className="text-gray-400 text-sm">Chapters will appear as they are generated...</p>
      )}

      <div className="space-y-4">
        {(chapters as Array<{ id: string; index: number; title?: string; content: string; status: string }>).map((ch) => (
          <ChapterCard key={ch.id} chapter={ch} onUpdate={fetchChapters} />
        ))}
      </div>

      {status === "complete" && (
        <div className="bg-green-900 border border-green-600 rounded p-4 text-center">
          <p className="text-green-200 font-medium">Book generation complete!</p>
          <a
            href={`/jobs/${jobId}/export`}
            className="inline-block mt-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded text-sm"
          >
            Go to Export →
          </a>
        </div>
      )}
    </div>
  );
}
```

### `frontend/app/jobs/[id]/page.tsx` (overwrite — replace stub)
```typescript
import { BookEditorView } from "@/components/BookEditorView";

export default function BookEditorPage({ params }: { params: { id: string } }) {
  return (
    <main className="min-h-screen bg-gray-900">
      <BookEditorView jobId={params.id} />
    </main>
  );
}
```

---

## Codebase Context

### Key Code Snippets
```typescript
// frontend/lib/api.ts — API functions available for use
export async function getChapters(jobId: string): Promise<Record<string, unknown>[]>
export async function updateChapter(chapterId: string, content: string): Promise<void>
export async function lockChapter(chapterId: string): Promise<void>
export async function regenerateChapter(chapterId: string): Promise<void>
```

### Key Patterns in Use
- **`useWebSocket` hook with auto-reconnect:** Reconnects after 3s on close. Caller reads `latestEvent`.
- **`InlineEditor` saves on blur:** `onBlur` fires `onSave(ref.current.innerText)`. Disabled when `isLocked`.
- **`ChapterCard.onUpdate`:** Callback to `BookEditorView.fetchChapters` — re-fetches full chapter list from API.
- **Progress bar updates from WebSocket events:** `latestEvent.progress` → `setProgress()`. No polling.

### Architecture Decisions Affecting This Task
- WebSocket URL: `ws://localhost:8000/v1/ws/{job_id}` (uses `WS_BASE` derived from `NEXT_PUBLIC_API_URL`).
- Regenerate returns 202 Accepted — ChapterCard waits 3 seconds then calls `onUpdate()` to poll for updated content.

---

## Handoff from Previous Task

**Files changed by previous task:** `frontend/` scaffolded, `JobCreatorForm.tsx`, `ProviderConfigPanel.tsx`, `lib/api.ts`, `types/job.ts`.
**Decisions made:** Design tokens: `bg-gray-900` base, `bg-red-600` accent. `react-hook-form` for forms. `router.push()` for navigation.
**Context for this task:** Job Creator complete. Now implement the Book Editor with WebSocket progress.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `frontend/hooks/useWebSocket.ts` — paste template exactly.
2. Create `frontend/components/StatusBadge.tsx` — paste template exactly.
3. Create `frontend/components/ProgressBar.tsx` — paste template exactly.
4. Create `frontend/components/InlineEditor.tsx` — paste template exactly.
5. Create `frontend/components/ChapterCard.tsx` — paste template exactly.
6. Create `frontend/components/BookEditorView.tsx` — paste template exactly.
7. Overwrite `frontend/app/jobs/[id]/page.tsx` — paste template exactly.
8. Run: `cd C:/Users/Hp/Desktop/Experiment/book-generation-engine/frontend && npm run build` — verify zero build errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| Chapter status == "locked" | `InlineEditor disabled={true}`, hide Regenerate and Lock buttons, show "Chapter locked" text |
| WebSocket close event | `setTimeout(connect, 3000)` — auto-reconnect after 3 seconds |
| `latestEvent.type == "chapter_ready"` | Call `fetchChapters()` to reload chapter list |
| `latestEvent.type == "complete"` | Call `fetchChapters()` and show "Go to Export" banner |
| Regenerate API call succeeds | `setTimeout(onUpdate, 3000)` — poll for content after 3s |

---

## Acceptance Criteria

- [ ] WHEN the Book Editor mounts THEN WebSocket connects and progress bar shows
- [ ] WHEN a progress event arrives via WebSocket THEN progress bar updates without page reload
- [ ] WHEN a chapter is locked THEN InlineEditor is disabled and Regenerate/Lock buttons are hidden
- [ ] WHEN InlineEditor loses focus THEN `updateChapter` API call is made
- [ ] WHEN `npm run build` runs THEN zero errors

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_

Status: COMPLETE
Completed: 2026-04-17T00:00:00Z
