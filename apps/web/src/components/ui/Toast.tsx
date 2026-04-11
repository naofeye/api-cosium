"use client";

import { CheckCircle, AlertTriangle, Info, XCircle, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type ToastVariant = "success" | "error" | "warning" | "info";

interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
  exiting: boolean;
}

interface ToastContextType {
  toast: (message: string, variant?: ToastVariant) => void;
}

const ToastContext = createContext<ToastContextType>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

const icons: Record<ToastVariant, typeof CheckCircle> = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const colors: Record<ToastVariant, string> = {
  success: "border-l-success bg-emerald-50 text-emerald-800",
  error: "border-l-danger bg-red-50 text-red-800",
  warning: "border-l-warning bg-amber-50 text-amber-800",
  info: "border-l-info bg-sky-50 text-sky-800",
};

const TOAST_DURATION_MS = 5000;
const EXIT_ANIMATION_MS = 150;

let nextId = 0;

function ToastCard({
  item,
  onRemove,
}: {
  item: ToastItem;
  onRemove: (id: number) => void;
}) {
  const Icon = icons[item.variant];

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border-l-4 p-4 shadow-lg transition-all",
        item.exiting
          ? "translate-x-full opacity-0 duration-150 ease-in"
          : "translate-x-0 opacity-100 duration-200 ease-out animate-slide-in-right",
        colors[item.variant],
      )}
    >
      <Icon className="h-5 w-5 shrink-0 mt-0.5" />
      <p className="flex-1 text-sm font-medium">{item.message}</p>
      <button onClick={() => onRemove(item.id)} aria-label="Fermer">
        <X className="h-4 w-4 opacity-60 hover:opacity-100" />
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const dismissToast = useCallback((id: number) => {
    // Mark as exiting (starts slide-out animation)
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));
    // Remove from DOM after the exit animation completes
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, EXIT_ANIMATION_MS);
  }, []);

  const addToast = useCallback(
    (message: string, variant: ToastVariant = "info") => {
      const id = nextId++;
      setToasts((prev) => [...prev, { id, message, variant, exiting: false }]);
      const timer = setTimeout(() => {
        dismissToast(id);
        timersRef.current.delete(id);
      }, TOAST_DURATION_MS);
      timersRef.current.set(id, timer);
    },
    [dismissToast],
  );

  const removeToast = useCallback(
    (id: number) => {
      // Clear the auto-dismiss timer if the user closes manually
      const timer = timersRef.current.get(id);
      if (timer) {
        clearTimeout(timer);
        timersRef.current.delete(id);
      }
      dismissToast(id);
    },
    [dismissToast],
  );

  // Listen for global API error events
  useEffect(() => {
    function handleApiError(e: Event) {
      const detail = (e as CustomEvent<{ message: string; status: number }>).detail;
      if (detail && detail.message) {
        addToast(detail.message, "error");
      }
    }
    window.addEventListener("api-error", handleApiError);
    return () => {
      window.removeEventListener("api-error", handleApiError);
    };
  }, [addToast]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      timersRef.current.forEach((timer) => clearTimeout(timer));
    };
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80" aria-live="polite" aria-atomic="true">
        {toasts.map((t) => (
          <ToastCard key={t.id} item={t} onRemove={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
