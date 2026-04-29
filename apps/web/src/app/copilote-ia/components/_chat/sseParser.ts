export interface SseEvent {
  type: string;
  data: Record<string, unknown>;
}

export function parseSseFrames(buffer: string): { events: SseEvent[]; rest: string } {
  const events: SseEvent[] = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";

  for (const frame of parts) {
    if (!frame.trim()) continue;
    let type = "message";
    let dataLine = "";
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) {
        type = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLine += line.slice(5).trim();
      }
    }
    if (!dataLine) continue;
    try {
      const data = JSON.parse(dataLine) as Record<string, unknown>;
      events.push({ type, data });
    } catch {
      // Ignore malformed frames silently — server should always emit valid JSON.
    }
  }
  return { events, rest };
}
