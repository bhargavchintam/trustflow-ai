import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { RouteBadge } from "./RouteBadge";
import { LatencyPill } from "./LatencyPill";
import { TracePanel } from "./TracePanel";

export function MessageBubble({
  msg,
  tenant,
  user,
  sessionId,
}: {
  msg: ChatMessage;
  tenant: string;
  user: string;
  sessionId: string;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[88%] rounded-lg px-3 py-2 text-sm",
          isUser
            ? "bg-accent/20 border border-accent/40 text-zinc-100"
            : "bg-panel border border-border text-zinc-100",
        )}
      >
        {!isUser && (msg.route || msg.latencyMs != null) && (
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            <RouteBadge route={msg.route} />
            <LatencyPill ms={msg.latencyMs} />
          </div>
        )}
        <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
        {!isUser && msg.messageId && (
          <TracePanel
            tenant={tenant}
            user={user}
            sessionId={sessionId}
            messageId={msg.messageId}
          />
        )}
      </div>
    </div>
  );
}
