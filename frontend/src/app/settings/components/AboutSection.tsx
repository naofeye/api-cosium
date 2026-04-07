"use client";

import { Info, ExternalLink, HelpCircle } from "lucide-react";

export function AboutSection() {
  return (
    <>
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
            <Info className="h-6 w-6 text-text-secondary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">A propos</h2>
            <p className="text-sm text-text-secondary">Informations sur OptiFlow AI</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Version</span>
              <span className="font-medium text-text-primary">0.1.0 (MVP)</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Backend</span>
              <span className="font-medium text-text-primary">Python 3.12 + FastAPI</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Frontend</span>
              <span className="font-medium text-text-primary">Next.js 15 + React 19</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Base de donnees</span>
              <span className="font-medium text-text-primary">PostgreSQL 16</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Cache</span>
              <span className="font-medium text-text-primary">Redis 7</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Stockage</span>
              <span className="font-medium text-text-primary">MinIO (S3)</span>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
            aria-label="Voir le depot GitHub"
          >
            <ExternalLink className="h-4 w-4" />
            Voir sur GitHub
          </a>
        </div>
      </div>

      {/* Aide */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <HelpCircle className="h-5 w-5 text-text-secondary" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Besoin d&apos;aide ?</h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Contactez le support a support@optiflow.ai ou consultez la documentation.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
