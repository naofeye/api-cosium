import { Bell, CheckCheck, ExternalLink, Trash2 } from "lucide-react";
import { TYPE_ICONS, type Notification } from "../types";
import { formatRelativeDate, getEntityUrl } from "../utils";

interface Props {
  notif: Notification;
  onNavigate: (notif: Notification) => void;
  onMarkRead: (id: number) => void;
  onDelete: (id: number) => void;
}

export function NotificationCard({ notif, onNavigate, onMarkRead, onDelete }: Props) {
  const typeClass = TYPE_ICONS[notif.type] ?? TYPE_ICONS.info;
  const entityUrl = getEntityUrl(notif.entity_type, notif.entity_id);

  return (
    <div
      className={`rounded-xl border bg-white shadow-sm p-4 flex items-start gap-4 transition-colors ${
        !notif.is_read ? "border-blue-200 bg-blue-50/30" : "border-gray-200"
      }`}
    >
      <div className={`shrink-0 rounded-full p-2 ${typeClass}`} aria-hidden="true">
        <Bell className="h-4 w-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className={`text-sm font-medium ${!notif.is_read ? "text-gray-900" : "text-gray-700"}`}>
            {notif.title}
          </p>
          {!notif.is_read && (
            <span
              className="h-2 w-2 rounded-full bg-blue-600 shrink-0"
              aria-label="Non lue"
              role="status"
            />
          )}
        </div>
        <p className="text-sm text-gray-500 mt-0.5 line-clamp-2">{notif.message}</p>
        <p className="text-xs text-gray-400 mt-1">{formatRelativeDate(notif.created_at)}</p>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {entityUrl && (
          <button
            onClick={() => onNavigate(notif)}
            className="rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
            title="Voir le detail"
            aria-label="Voir le detail"
          >
            <ExternalLink className="h-4 w-4 text-gray-400" />
          </button>
        )}
        {!notif.is_read && (
          <button
            onClick={() => onMarkRead(notif.id)}
            className="rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
            title="Marquer comme lue"
            aria-label="Marquer comme lue"
          >
            <CheckCheck className="h-4 w-4 text-gray-400" />
          </button>
        )}
        <button
          onClick={() => onDelete(notif.id)}
          className="rounded-lg p-1.5 hover:bg-red-50 transition-colors"
          title="Supprimer"
          aria-label="Supprimer la notification"
        >
          <Trash2 className="h-4 w-4 text-gray-400 hover:text-red-500" />
        </button>
      </div>
    </div>
  );
}
