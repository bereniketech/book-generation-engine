"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { listChapters, getChapter, updateChapter, type ChapterSummary, type ChapterDetail } from "@/lib/api";

export default function ChapterEditorPage() {
  const { id: jobId } = useParams<{ id: string }>();
  const [chapters, setChapters] = useState<ChapterSummary[]>([]);
  const [selected, setSelected] = useState<ChapterDetail | null>(null);
  const [editContent, setEditContent] = useState("");
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listChapters(jobId)
      .then((data) => {
        setChapters(data.chapters);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, [jobId]);

  const selectChapter = async (index: number) => {
    try {
      const data = await getChapter(jobId, index);
      setSelected(data);
      setEditContent(data.content);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load chapter";
      setToast(`Error: ${message}`);
      setTimeout(() => setToast(""), 4000);
    }
  };

  const saveChapter = async () => {
    if (!selected) return;
    try {
      await updateChapter(jobId, selected.index, editContent);
      setToast("Chapter saved and locked.");
      setChapters((prev) =>
        prev.map((ch) =>
          ch.index === selected.index ? { ...ch, status: "locked" } : ch
        )
      );
      setSelected((prev) => (prev ? { ...prev, status: "locked" } : prev));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Save failed";
      setToast(`Error: ${message}`);
    }
    setTimeout(() => setToast(""), 4000);
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "locked": return "text-green-600";
      case "generating": return "text-yellow-600";
      case "qa_failed": return "text-red-600";
      default: return "text-gray-500";
    }
  };

  if (loading) return <div className="p-8">Loading chapters...</div>;

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-64 border-r overflow-y-auto p-4">
        <h2 className="font-bold text-lg mb-4">Chapters</h2>
        {chapters.map((ch) => (
          <button
            key={ch.index}
            onClick={() => selectChapter(ch.index)}
            className={`w-full text-left p-3 rounded mb-1 hover:bg-gray-100 ${selected?.index === ch.index ? "bg-gray-200" : ""}`}
          >
            <div className="font-medium">Chapter {ch.index + 1}</div>
            <div className={`text-xs ${statusColor(ch.status)}`}>{ch.status}</div>
            {ch.qa_score !== null && (
              <div className="text-xs text-gray-400">QA: {ch.qa_score.toFixed(1)}</div>
            )}
          </button>
        ))}
      </aside>

      <main className="flex-1 overflow-y-auto p-6">
        {toast && (
          <div className="mb-4 p-3 bg-blue-100 text-blue-800 rounded-lg font-medium">{toast}</div>
        )}
        {selected ? (
          <>
            <div className="flex justify-between items-center mb-4">
              <h1 className="text-2xl font-bold">Chapter {selected.index + 1}</h1>
              <span className={`text-sm font-medium ${statusColor(selected.status)}`}>
                {selected.status}
              </span>
            </div>
            {selected.flesch_kincaid_grade !== null && (
              <p className="text-sm text-gray-500 mb-4">
                Readability — Grade: {selected.flesch_kincaid_grade?.toFixed(1)} · Ease: {selected.flesch_reading_ease?.toFixed(1)}
              </p>
            )}
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full h-[60vh] border rounded-lg p-4 font-mono text-sm resize-none"
            />
            <button
              onClick={saveChapter}
              className="mt-4 w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700"
            >
              Save & Lock Chapter
            </button>
          </>
        ) : (
          <p className="text-gray-500">Select a chapter from the sidebar to edit.</p>
        )}
      </main>
    </div>
  );
}
