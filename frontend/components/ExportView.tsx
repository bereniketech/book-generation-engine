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
