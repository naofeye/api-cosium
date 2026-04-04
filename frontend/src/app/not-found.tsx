import { FileQuestion } from "lucide-react";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="rounded-full bg-gray-100 p-5">
        <FileQuestion className="h-10 w-10 text-text-secondary" />
      </div>
      <h1 className="mt-6 text-xl font-bold text-text-primary">Page introuvable</h1>
      <p className="mt-2 max-w-md text-sm text-text-secondary">Cette page n&apos;existe pas ou a ete deplacee.</p>
      <Link
        href="/actions"
        className="mt-6 inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover transition-colors"
      >
        Retour a l&apos;accueil
      </Link>
    </div>
  );
}
