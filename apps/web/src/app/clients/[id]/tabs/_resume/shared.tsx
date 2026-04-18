import {
  Calendar,
  Eye,
  Mail,
  MessageSquare,
  Pencil,
  PhoneCall,
} from "lucide-react";
import { CopyButton } from "@/components/ui/CopyButton";

export const TYPE_ICONS: Record<string, typeof PhoneCall> = {
  appel: PhoneCall,
  email: Mail,
  sms: MessageSquare,
  visite: Eye,
  note: Pencil,
  tache: Calendar,
};

export function InfoRow({
  icon: Icon,
  label,
  value,
  copyValue,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  copyValue?: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="h-4 w-4 text-text-secondary shrink-0" />
      <div className="flex justify-between flex-1">
        <span className="text-text-secondary">{label}</span>
        <span className="font-medium inline-flex items-center gap-1">
          {value}
          {copyValue && <CopyButton text={copyValue} label={label} />}
        </span>
      </div>
    </div>
  );
}

export function formatDiopter(value: number | null): string {
  if (value === null || value === undefined) return "-";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

export function formatAxis(value: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${value}\u00B0`;
}
