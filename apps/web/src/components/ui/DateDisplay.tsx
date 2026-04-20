import { formatDate } from "@/lib/format";

interface DateDisplayProps {
  date: string | Date | null | undefined;
  className?: string;
}

export function DateDisplay({ date, className }: DateDisplayProps) {
  if (!date) return <span className={className}>—</span>;
  return <span className={className}>{formatDate(date)}</span>;
}
