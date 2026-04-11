"use client";

import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface DroppablePaymentProps {
  id: number;
  onMatch: (transactionId: number, paymentId: number) => void;
  children?: ReactNode;
}

export function DroppablePayment({ id, onMatch, children }: DroppablePaymentProps) {
  const [dragOver, setDragOver] = useState(false);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const txId = Number(e.dataTransfer.getData("transaction_id"));
        if (txId) onMatch(txId, id);
      }}
      className={cn(
        "border rounded-lg p-3 transition-all",
        dragOver ? "border-blue-500 bg-blue-50 shadow-md ring-2 ring-blue-500/20" : "border-border bg-white",
      )}
    >
      {children}
    </div>
  );
}
