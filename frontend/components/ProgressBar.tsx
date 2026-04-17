interface Props {
  progress: number;
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
