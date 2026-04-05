"use client";

import { Upload } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";
import { cn } from "@/lib/utils";

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  className?: string;
}

export function FileUpload({ onFileSelect, accept, className }: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      setFileName(file.name);
      onFileSelect(file);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      onFileSelect(file);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={fileName ?? "Glissez vos fichiers ici ou cliquez pour parcourir"}
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
        dragOver ? "border-primary bg-blue-50" : "border-border hover:border-gray-400",
        className,
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <Upload className="h-8 w-8 text-gray-400" aria-hidden="true" />
      <p className="mt-3 text-sm text-text-secondary">
        {fileName ?? "Glissez vos fichiers ici ou cliquez pour parcourir"}
      </p>
      <input ref={inputRef} type="file" className="hidden" accept={accept} onChange={handleChange} aria-hidden="true" />
    </div>
  );
}
