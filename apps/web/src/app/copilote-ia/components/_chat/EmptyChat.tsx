import { Sparkles } from "lucide-react";
import { MODE_PLACEHOLDERS, type CopilotMode } from "./modes";

export function EmptyChat({ mode }: { mode: CopilotMode }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center text-text-secondary">
      <div className="w-12 h-12 rounded-full bg-blue-50 text-primary flex items-center justify-center mb-4">
        <Sparkles className="w-6 h-6" aria-hidden="true" />
      </div>
      <h2 className="text-base font-semibold text-text-primary mb-1">
        Posez une question à votre copilote
      </h2>
      <p className="text-sm max-w-md">{MODE_PLACEHOLDERS[mode]}</p>
    </div>
  );
}
