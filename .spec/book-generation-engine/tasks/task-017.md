---
task: 017
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: web-frontend-expert
depends_on: [016]
---

# Task 017: React/Next.js Frontend — Export View

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

Implement the Export View — a page that shows the KDP bundle file list, a StatusBadge, and a "Download KDP Bundle" button that triggers a browser download via the signed Supabase URL from `GET /v1/jobs/{id}/export`.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `frontend/components/ExportView.tsx` | File list + download button |
| `frontend/app/jobs/[id]/export/page.tsx` | Export page route |

---

## Dependencies

```bash
# No new packages.
```

---

## Code Templates

### `frontend/components/ExportView.tsx` (create this file exactly)
```typescript
"use client";

import { useEffect, useState } from "react";
import { getExport } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

interface Props {
  jobId: string;
}

const FILE_DESCRIPTIONS: Record<string, string> = {
  "manuscript.epub": "EPUB ebook file for Kindle Direct Publishing",
  "manuscript.pdf": "PDF print interior file",
  "cover.jpg": "AI-generated cover image (1024×1536px)",
  "cover-brief.txt": "Cover design brief for human designer",
  "description.txt": "Book description / blurb for KDP listing",
  "metadata.json": "KDP metadata: title, subtitle, keywords, categories",
};

export function ExportView({ jobId }: Props) {
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [files, setFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getExport(jobId)
      .then((data) => {
        setDownloadUrl(data.download_url);
        setFiles(data.files);
      })
      .catch(() => {
        setError("Export not ready. Your book may still be generating.");
      })
      .finally(() => setLoading(false));
  }, [jobId]);

  if (loading) {
    return (
      <div className="text-gray-400 text-sm animate-pulse">Loading export...</div>
    );
  }

  if (error || !downloadUrl) {
    return (
      <div className="bg-yellow-900 border border-yellow-600 rounded p-4">
        <p className="text-yellow-200 text-sm">{error || "Export not available yet."}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold text-white">Export KDP Bundle</h1>
        <StatusBadge status="complete" />
      </div>

      <div className="border border-gray-700 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-800 text-gray-400">
              <th className="text-left px-4 py-2">File</th>
              <th className="text-left px-4 py-2">Description</th>
            </tr>
          </thead>
          <tbody>
            {files.map((filename) => (
              <tr key={filename} className="border-t border-gray-700 hover:bg-gray-800">
                <td className="px-4 py-2 text-gray-100 font-mono text-xs">{filename}</td>
                <td className="px-4 py-2 text-gray-400">
                  {FILE_DESCRIPTIONS[filename] ?? "Included in bundle"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <a
        href={downloadUrl}
        download="kdp-bundle.zip"
        className="block text-center w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded transition-colors"
      >
        Download KDP Bundle
      </a>

      <p className="text-gray-500 text-xs text-center">
        Download link valid for 7 days. Contains all files in a single .zip archive.
      </p>
    </div>
  );
}
```

### `frontend/app/jobs/[id]/export/page.tsx` (create this file exactly)
```typescript
import { ExportView } from "@/components/ExportView";

export default function ExportPage({ params }: { params: { id: string } }) {
  return (
    <main className="min-h-screen bg-gray-900">
      <ExportView jobId={params.id} />
    </main>
  );
}
```

---

## Codebase Context

### Key Code Snippets
```typescript
// frontend/lib/api.ts — getExport signature
export async function getExport(jobId: string): Promise<{ download_url: string; files: string[] }>
```

### Key Patterns in Use
- **`<a href={downloadUrl} download="kdp-bundle.zip">`:** Browser-native download trigger. Never use `window.location.href` or `fetch` for binary downloads.
- **`StatusBadge status="complete"`:** Always shows green "complete" badge on this page.
- **Error state for non-complete jobs:** If `getExport()` throws (404 or 400), show yellow warning — not a crash.

### Architecture Decisions Affecting This Task
- Requirement 11.2: "WHEN the author clicks download THEN the system SHALL redirect to the signed Supabase Storage URL."
- Signed URL is valid for 7 days (604,800 seconds) — stated explicitly in UI copy.

---

## Handoff from Previous Task

**Files changed by previous task:** `frontend/hooks/useWebSocket.ts`, `frontend/components/BookEditorView.tsx`, `frontend/components/ChapterCard.tsx`, `frontend/components/InlineEditor.tsx`, `frontend/components/ProgressBar.tsx`, `frontend/components/StatusBadge.tsx`, `frontend/app/jobs/[id]/page.tsx`.
**Decisions made:** WebSocket auto-reconnect (3s). Chapter locked = disabled editor. `onUpdate` callback pattern.
**Context for this task:** Book Editor complete. Now build the final Export View.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `frontend/components/ExportView.tsx` — paste template exactly.
2. Create `frontend/app/jobs/[id]/export/page.tsx` — paste template exactly.
3. Run: `cd C:/Users/Hp/Desktop/Experiment/book-generation-engine/frontend && npm run build` — verify zero build errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| `getExport()` throws (job not complete) | Show yellow warning: `"Export not ready. Your book may still be generating."` |
| `downloadUrl` is null after loading | Same yellow warning state |
| `filename` not in `FILE_DESCRIPTIONS` | Show `"Included in bundle"` as description |

---

## Acceptance Criteria

- [ ] WHEN the export page loads with a complete job THEN file list and download button are shown
- [ ] WHEN the export page loads with a non-complete job THEN yellow warning is shown
- [ ] WHEN download button is clicked THEN browser downloads `kdp-bundle.zip` from signed URL
- [ ] WHEN `npm run build` runs THEN zero errors

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_

Status: COMPLETE
Completed: 2026-04-17T00:00:00Z
