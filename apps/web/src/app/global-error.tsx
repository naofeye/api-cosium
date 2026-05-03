"use client";

import { useEffect } from "react";

import * as Sentry from "@sentry/nextjs";

/**
 * Global error boundary Next.js (capture les erreurs du root layout
 * qui ne sont pas attrapees par error.tsx). Doit avoir son propre
 * <html><body> car le layout root est lui-meme casse.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="fr">
      <body>
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "2rem",
            fontFamily: "system-ui, -apple-system, sans-serif",
            backgroundColor: "#f9fafb",
          }}
        >
          <div
            style={{
              maxWidth: "32rem",
              textAlign: "center",
              padding: "2rem",
              backgroundColor: "white",
              borderRadius: "0.75rem",
              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
              border: "1px solid #fecaca",
            }}
          >
            <div
              style={{
                margin: "0 auto 1.5rem",
                width: "4rem",
                height: "4rem",
                borderRadius: "9999px",
                backgroundColor: "#fef2f2",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.875rem",
              }}
              aria-hidden="true"
            >
              ⚠
            </div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#111827", marginBottom: "0.75rem" }}>
              Erreur critique
            </h1>
            <p style={{ fontSize: "0.875rem", color: "#6b7280", marginBottom: "1.5rem" }}>
              L&apos;application a rencontre un probleme inattendu et n&apos;a pas pu se charger correctement.
              L&apos;equipe technique a ete automatiquement avertie.
            </p>
            {error.digest && (
              <p style={{ fontSize: "0.75rem", color: "#9ca3af", marginBottom: "1rem" }}>
                Ref : <code>{error.digest}</code>
              </p>
            )}
            <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}>
              <button
                type="button"
                onClick={() => (window.location.href = "/actions")}
                style={{
                  padding: "0.625rem 1.25rem",
                  borderRadius: "0.5rem",
                  border: "1px solid #d1d5db",
                  backgroundColor: "white",
                  color: "#374151",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                Retour accueil
              </button>
              <button
                type="button"
                onClick={() => reset()}
                style={{
                  padding: "0.625rem 1.25rem",
                  borderRadius: "0.5rem",
                  border: "none",
                  backgroundColor: "#2563eb",
                  color: "white",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                Recharger
              </button>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
