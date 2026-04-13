"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { FAQItem } from "../data";

export function FAQAccordion({ item }: { item: FAQItem }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg"
        aria-expanded={open}
      >
        <span className="text-sm font-medium text-gray-900">{item.question}</span>
        {open ? (
          <ChevronDown className="h-4 w-4 text-gray-500 shrink-0 ml-4" aria-hidden="true" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-500 shrink-0 ml-4" aria-hidden="true" />
        )}
      </button>
      {open && (
        <div className="px-6 pb-4">
          <p className="text-sm text-gray-600 leading-relaxed">{item.answer}</p>
        </div>
      )}
    </div>
  );
}
