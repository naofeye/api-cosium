"use client";

import { useEffect, useCallback, useRef } from "react";

/**
 * Warns the user when they try to navigate away with unsaved changes.
 * - Handles `beforeunload` for tab close / reload.
 * - Handles Next.js client-side navigation via patching history.pushState.
 *
 * @param isDirty - Whether there are unsaved changes.
 * @param message - The confirmation message to show (browser may override for beforeunload).
 */
export function useUnsavedChangesWarning(isDirty: boolean, message?: string) {
  const msg = message || "Vous avez des modifications non enregistrees. Voulez-vous quitter sans sauvegarder ?";
  const isDirtyRef = useRef(isDirty);
  isDirtyRef.current = isDirty;

  // beforeunload for tab close / reload
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!isDirtyRef.current) return;
      e.preventDefault();
      // Modern browsers require returnValue to be set
      e.returnValue = msg;
      return msg;
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [msg]);

  // Intercept client-side navigation (Next.js uses pushState)
  useEffect(() => {
    const originalPushState = history.pushState.bind(history);

    const patchedPushState = function (
      this: History,
      ...args: Parameters<typeof history.pushState>
    ) {
      if (isDirtyRef.current) {
        const confirmed = window.confirm(msg);
        if (!confirmed) return;
      }
      return originalPushState(...args);
    };

    history.pushState = patchedPushState;

    return () => {
      history.pushState = originalPushState;
    };
  }, [msg]);

  // Also intercept popstate (back button)
  const handlePopState = useCallback(
    (e: PopStateEvent) => {
      if (!isDirtyRef.current) return;
      const confirmed = window.confirm(msg);
      if (!confirmed) {
        // Go forward to counteract the back navigation.
        // e.preventDefault() is a no-op on popstate, and pushState would create a duplicate entry.
        history.go(1);
      }
    },
    [msg],
  );

  useEffect(() => {
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [handlePopState]);
}
