"use client";

import { useCallback, useEffect, useState } from "react";
import { ChapterCard } from "./ChapterCard";
import { ProgressBar } from "./ProgressBar";
import { StatusBadge } from "./StatusBadge";
import { listChapters, type ChapterSummary } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";

interface Props {
  jobId: string;
}

export function BookEditorView({ jobId }: Props) {
  const [chapters, setChapters] = useState<ChapterSummary[]>([]);
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState("Initialising...");
  const [status, setStatus] = useState("queued");
  const { latestEvent, connected } = useWebSocket(jobId);

  const fetchChapters = useCallback(async () => {
    try {
      const data = await listChapters(jobId);
      setChapters(data.chapters);
    } catch {
      // Chapters may not exist yet during planning phase
    }
  }, [jobId]);

  useEffect(() => {
    fetchChapters();
  }, [fetchChapters]);

  useEffect(() => {
    if (!latestEvent) return;
    if (latestEvent.progress !== undefined) setProgress(latestEvent.progress as number);
    if (latestEvent.step) setStep(latestEvent.step as string);
    if (latestEvent.status) setStatus(latestEvent.status as string);
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
        {chapters.map((ch) => (
          <ChapterCard
            key={ch.index}
            jobId={jobId}
            chapter={{
              index: ch.index,
              content: ch.content_preview,
              status: ch.status,
            }}
            onUpdate={fetchChapters}
          />
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
