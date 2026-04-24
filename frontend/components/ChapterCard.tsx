"use client";

import { useState } from "react";
import { InlineEditor } from "./InlineEditor";
import { StatusBadge } from "./StatusBadge";
import { updateChapter } from "@/lib/api";

interface Chapter {
  index: number;
  title?: string;
  content: string;
  status: string;
}

interface Props {
  jobId: string;
  chapter: Chapter;
  onUpdate: () => void;
}

export function ChapterCard({ jobId, chapter, onUpdate }: Props) {
  const isLocked = chapter.status === "locked";

  const handleSave = async (content: string) => {
    if (isLocked) return;
    await updateChapter(jobId, chapter.index, content);
    onUpdate();
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

      {isLocked && (
        <span className="text-xs text-green-400 self-center">Chapter locked — editing disabled</span>
      )}
    </div>
  );
}
