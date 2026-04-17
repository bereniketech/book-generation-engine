"use client";

import { useRef } from "react";

interface Props {
  initialContent: string;
  onSave: (content: string) => void;
  disabled?: boolean;
}

export function InlineEditor({ initialContent, onSave, disabled = false }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const handleBlur = () => {
    if (ref.current) {
      onSave(ref.current.innerText);
    }
  };

  return (
    <div
      ref={ref}
      contentEditable={!disabled}
      suppressContentEditableWarning
      onBlur={handleBlur}
      className={`min-h-24 p-3 rounded bg-gray-700 text-gray-100 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-red-500 whitespace-pre-wrap ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
    >
      {initialContent}
    </div>
  );
}
