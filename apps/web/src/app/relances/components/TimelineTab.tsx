"use client";

import { Clock, Send, CheckCircle, AlertTriangle, Mail, MessageSquare } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate } from "@/lib/format";

interface ReminderItem {
  id: number;
  target_type: string;
  target_id: number;
  channel: string;
  status: string;
  content: string | null;
  created_at: string;
  customer_name?: string | null;
}

const CHANNEL_ICONS: Record<string, React.ReactNode> = {
  email: <Mail className="h-3.5 w-3.5" />,
  courrier: <MessageSquare className="h-3.5 w-3.5" />,
  telephone: <MessageSquare className="h-3.5 w-3.5" />,
  sms: <Send className="h-3.5 w-3.5" />,
};

interface TimelineTabProps {
  items: ReminderItem[];
}

export function TimelineTab({ items }: TimelineTabProps) {
  if (items.length === 0) {
    return <EmptyState title="Aucune relance" description="L'historique des relances apparaitra ici." />;
  }

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-text-primary mb-6 flex items-center gap-2">
        <Clock className="h-5 w-5" /> Chronologie des relances recentes
      </h3>
      <div className="relative">
        {/* vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

        <div className="space-y-6">
          {items.map((r) => {
            const isSent = r.status === "envoyee" || r.status === "sent";
            const isResponded = r.status === "repondue" || r.status === "responded";
            const isFailed = r.status === "echouee" || r.status === "failed";

            return (
              <div key={r.id} className="relative flex items-start gap-4 pl-2">
                {/* dot */}
                <div
                  className={`relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2 ${
                    isResponded
                      ? "bg-emerald-100 border-emerald-500"
                      : isFailed
                        ? "bg-red-100 border-red-500"
                        : isSent
                          ? "bg-blue-100 border-blue-500"
                          : "bg-gray-100 border-gray-400"
                  }`}
                >
                  {isResponded ? (
                    <CheckCircle className="h-4 w-4 text-emerald-600" />
                  ) : isFailed ? (
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                  ) : (
                    (CHANNEL_ICONS[r.channel] || <Send className="h-4 w-4 text-blue-600" />)
                  )}
                </div>

                {/* content */}
                <div className="flex-1 min-w-0 pb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-text-primary">
                      Relance #{r.id}
                    </span>
                    <StatusBadge status={r.status} />
                    <span className="text-xs text-text-secondary capitalize">{r.channel}</span>
                  </div>
                  {r.content && (
                    <p className="mt-1 text-sm text-text-secondary truncate max-w-md">{r.content}</p>
                  )}
                  <p className="mt-1 text-xs text-text-secondary">
                    {formatDate(r.created_at)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
