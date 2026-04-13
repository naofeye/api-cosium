import { BookOpen, Cookie, Keyboard, type LucideIcon } from "lucide-react";

interface QuickLinkProps {
  href: string;
  icon: LucideIcon;
  iconBg: string;
  iconColor: string;
  title: string;
  subtitle: string;
}

function QuickLink({ href, icon: Icon, iconBg, iconColor, title, subtitle }: QuickLinkProps) {
  return (
    <a
      href={href}
      className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:border-blue-400 hover:shadow-md transition-all"
    >
      <div className={`rounded-lg p-2 ${iconBg}`}>
        <Icon className={`h-5 w-5 ${iconColor}`} aria-hidden="true" />
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-900">{title}</p>
        <p className="text-xs text-gray-500">{subtitle}</p>
      </div>
    </a>
  );
}

export function HelpQuickLinks({
  faqCount,
  shortcutsCount,
}: {
  faqCount: number;
  shortcutsCount: number;
}) {
  return (
    <section>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <QuickLink
          href="#faq"
          icon={BookOpen}
          iconBg="bg-blue-100"
          iconColor="text-blue-600"
          title="Questions fréquentes"
          subtitle={`${faqCount} questions`}
        />
        <QuickLink
          href="#raccourcis"
          icon={Keyboard}
          iconBg="bg-purple-100"
          iconColor="text-purple-600"
          title="Raccourcis clavier"
          subtitle={`${shortcutsCount} raccourcis`}
        />
        <QuickLink
          href="#cosium-cookie"
          icon={Cookie}
          iconBg="bg-amber-100"
          iconColor="text-amber-600"
          title="Cookie Cosium"
          subtitle="Guide de renouvellement"
        />
      </div>
    </section>
  );
}
