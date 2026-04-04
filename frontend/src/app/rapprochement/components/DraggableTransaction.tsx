"use client";

import { type ReactNode } from "react";

interface DraggableTransactionProps {
  id: number;
  children?: ReactNode;
}

export function DraggableTransaction({ id, children }: DraggableTransactionProps) {
  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("transaction_id", String(id));
        e.dataTransfer.effectAllowed = "move";
        (e.currentTarget as HTMLDivElement).style.opacity = "0.5";
      }}
      onDragEnd={(e) => {
        (e.currentTarget as HTMLDivElement).style.opacity = "1";
      }}
      className="cursor-grab active:cursor-grabbing border border-border rounded-lg p-3 bg-white hover:border-blue-400 hover:shadow-sm transition-all"
    >
      {children}
    </div>
  );
}
