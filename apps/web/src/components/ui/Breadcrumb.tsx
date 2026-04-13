import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { Fragment } from "react";

export type BreadcrumbItem = {
  label: string;
  href?: string;
};

export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  if (items.length === 0) return null;

  return (
    <nav aria-label="Fil d'Ariane" className="flex items-center gap-1 text-sm">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <Fragment key={`${i}-${item.label}`}>
            {i > 0 && (
              <ChevronRight className="h-4 w-4 text-gray-400" aria-hidden="true" />
            )}
            {item.href && !isLast ? (
              <Link
                href={item.href}
                className="text-primary hover:underline"
              >
                {item.label}
              </Link>
            ) : (
              <span
                className="font-medium text-gray-900"
                aria-current={isLast ? "page" : undefined}
              >
                {item.label}
              </span>
            )}
          </Fragment>
        );
      })}
    </nav>
  );
}
