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
