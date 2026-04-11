import { FileQuestion, ArrowLeft, Search } from "lucide-react";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-4 text-center">
      {/* Big 404 */}
      <div className="relative mb-6">
        <span className="text-[10rem] font-extrabold leading-none text-gray-100 dark:text-gray-800 select-none">
          404
        </span>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="rounded-full bg-blue-50 dark:bg-blue-900/20 p-5">
            <FileQuestion className="h-12 w-12 text-primary" />
          </div>
        </div>
      </div>

      {/* Message */}
      <h1 className="text-2xl font-bold text-text-primary">Page introuvable</h1>
      <p className="mt-2 max-w-md text-sm text-text-secondary">
        La page que vous cherchez n&apos;existe pas ou a ete deplacee.
        Verifiez l&apos;adresse ou retournez au tableau de bord.
      </p>

      {/* Actions */}
      <div className="mt-8 flex flex-col sm:flex-row items-center gap-3">
        <Link
          href="/actions"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Retour au tableau de bord
        </Link>
        <Link
          href="/clients"
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-white dark:bg-gray-800 px-5 py-2.5 text-sm font-semibold text-text-primary hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <Search className="h-4 w-4" />
          Rechercher un client
        </Link>
      </div>

      {/* Helpful links */}
      <div className="mt-10 rounded-xl border border-border bg-bg-card p-6 shadow-sm max-w-md w-full">
        <h2 className="text-sm font-semibold text-text-primary mb-3">Pages utiles</h2>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <Link href="/actions" className="text-primary hover:underline py-1">
            File d&apos;actions
          </Link>
          <Link href="/dashboard" className="text-primary hover:underline py-1">
            Tableau de bord
          </Link>
          <Link href="/cases" className="text-primary hover:underline py-1">
            Dossiers
          </Link>
          <Link href="/clients" className="text-primary hover:underline py-1">
            Clients
          </Link>
          <Link href="/invoices" className="text-primary hover:underline py-1">
            Factures
          </Link>
          <Link href="/settings" className="text-primary hover:underline py-1">
            Parametres
          </Link>
        </div>
      </div>
    </div>
  );
}
