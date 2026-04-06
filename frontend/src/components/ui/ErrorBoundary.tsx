"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw, Bug } from "lucide-react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  /** Optional name for debugging which boundary caught the error */
  name?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, showDetails: false };

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    if (process.env.NODE_ENV === "development") {
      // eslint-disable-next-line no-console
      console.error(`[ErrorBoundary:${this.props.name ?? "anonymous"}]`, error);
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const sectionLabel = this.props.name
        ? `La section "${this.props.name}" a rencontre un probleme.`
        : "Une section de la page a rencontre un probleme.";

      return (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6" role="alert">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-amber-900">
                Quelque chose ne s&apos;est pas passe comme prevu
              </h3>
              <p className="mt-1 text-sm text-amber-800">{sectionLabel}</p>
              <p className="mt-1 text-xs text-amber-700">
                Vous pouvez essayer de recharger cette section ou la page entiere.
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  onClick={() => this.setState({ hasError: false, error: undefined, showDetails: false })}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                  Reessayer
                </button>
                <button
                  onClick={() => window.location.reload()}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-100 transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                  Recharger la page
                </button>
                <button
                  onClick={() => this.setState((prev) => ({ showDetails: !prev.showDetails }))}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-100 transition-colors"
                >
                  <Bug className="h-3.5 w-3.5" aria-hidden="true" />
                  {this.state.showDetails ? "Masquer les details" : "Signaler cette erreur"}
                </button>
              </div>

              {this.state.showDetails && this.state.error && (
                <div className="mt-4 rounded-lg border border-amber-200 bg-white p-3">
                  <p className="text-xs font-medium text-gray-700 mb-1">Details techniques :</p>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap break-words font-mono max-h-40 overflow-auto">
                    {this.state.error.name}: {this.state.error.message}
                    {this.state.error.stack && (
                      <>
                        {"\n\n"}
                        {this.state.error.stack}
                      </>
                    )}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
