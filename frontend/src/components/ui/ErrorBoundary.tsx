"use client";

import { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  /** Optional name for debugging which boundary caught the error */
  name?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
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
      return (
        this.props.fallback || (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-sm text-red-700">Une erreur est survenue dans ce composant.</p>
            <button
              onClick={() => this.setState({ hasError: false })}
              className="mt-2 text-sm text-blue-600 hover:underline"
            >
              Reessayer
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
