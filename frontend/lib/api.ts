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
