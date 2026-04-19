"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

interface CoverData {
  job_id: string;
  cover_url: string | null;
  cover_status: string | null;
}

export default function CoverApprovalPage() {
  const { id: jobId } = useParams<{ id: string }>();
  const [cover, setCover] = useState<CoverData | null>(null);
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  useEffect(() => {
    fetch(`${apiBase}/jobs/${jobId}/cover`)
      .then((r) => r.json())
      .then((data: CoverData) => {
        setCover(data);
        setLoading(false);
      });
  }, [jobId, apiBase]);

  const approve = async () => {
    const resp = await fetch(`${apiBase}/jobs/${jobId}/cover/approve`, { method: "POST" });
    if (resp.ok) {
      setActionMsg("Cover approved. Final assembly started.");
      setCover((prev) => prev ? { ...prev, cover_status: "approved" } : prev);
    } else {
      const err = await resp.json();
      setActionMsg(`Error: ${err?.detail?.error ?? resp.statusText}`);
    }
  };

  const revise = async () => {
    if (!feedback.trim()) {
      setActionMsg("Please enter revision feedback before submitting.");
      return;
    }
    const resp = await fetch(`${apiBase}/jobs/${jobId}/cover/revise`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feedback }),
    });
    if (resp.ok) {
      setActionMsg("Revision requested. New cover will be generated.");
      setCover((prev) => prev ? { ...prev, cover_status: "revising" } : prev);
    } else {
      const err = await resp.json();
      setActionMsg(`Error: ${err?.detail?.error ?? resp.statusText}`);
    }
  };

  if (loading) return <div className="p-8">Loading cover...</div>;
  if (!cover?.cover_url) return <div className="p-8">No cover generated yet for job {jobId}.</div>;

  const isPending = cover.cover_status === "awaiting_approval";

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4">Cover Review — Job {jobId}</h1>
      <p className="text-sm text-gray-500 mb-4">Status: <strong>{cover.cover_status ?? "unknown"}</strong></p>

      <img
        src={cover.cover_url}
        alt="Generated book cover"
        className="w-full rounded-lg shadow mb-6"
      />

      {actionMsg && (
        <p className="mb-4 text-blue-600 font-medium">{actionMsg}</p>
      )}

      {isPending && (
        <>
          <button
            onClick={approve}
            className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold mb-4 hover:bg-green-700"
          >
            Approve Cover
          </button>

          <div className="mt-4">
            <label className="block text-sm font-medium mb-1" htmlFor="feedback">
              Request Revision (describe what to change):
            </label>
            <textarea
              id="feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="w-full border rounded-lg p-3 text-sm mb-2 min-h-[100px]"
              placeholder="e.g. Make the background darker, add a forest scene..."
            />
            <button
              onClick={revise}
              className="w-full bg-yellow-500 text-white py-3 rounded-lg font-semibold hover:bg-yellow-600"
            >
              Request Revision
            </button>
          </div>
        </>
      )}
    </div>
  );
}
