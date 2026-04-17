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
      setTimeout(onUpdate, 3000);
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
