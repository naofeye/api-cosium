import { Bot, User, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export type ChatRole = "user" | "assistant" | "error";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  text: string;
  isStreaming?: boolean;
}

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isError = message.role === "error";

  return (
    <div
      className={cn(
        "flex gap-3 w-full",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
          isUser
            ? "bg-primary text-white"
            : isError
              ? "bg-red-100 text-red-600"
              : "bg-gray-100 text-gray-700",
        )}
        aria-hidden="true"
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : isError ? (
          <AlertTriangle className="w-4 h-4" />
        ) : (
          <Bot className="w-4 h-4" />
        )}
      </div>

      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words",
          isUser
            ? "bg-primary text-white rounded-tr-sm"
            : isError
              ? "bg-red-50 text-red-900 border border-red-200 rounded-tl-sm"
              : "bg-gray-100 text-gray-900 rounded-tl-sm",
        )}
        role={isError ? "alert" : undefined}
      >
        {message.text || (message.isStreaming ? <StreamingDots /> : null)}
        {message.isStreaming && message.text && (
          <span className="inline-block w-1.5 h-4 ml-0.5 -mb-0.5 bg-current opacity-60 animate-pulse" />
        )}
      </div>
    </div>
  );
}

function StreamingDots() {
  return (
    <span className="inline-flex gap-1" aria-label="L'assistant rédige une réponse">
      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.3s]" />
      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.15s]" />
      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" />
    </span>
  );
}
