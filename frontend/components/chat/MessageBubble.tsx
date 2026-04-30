import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { RouteBadge } from "./RouteBadge";
import { LatencyPill } from "./LatencyPill";
import { TracePanel } from "./TracePanel";
import { Markdown } from "./Markdown";
import { WorkflowDiagram } from "./WorkflowDiagram";
import { MemoryWriteSummary } from "./MemoryWriteSummary";
import { RouteExplainer } from "./RouteExplainer";
import { LiveWorkflowStepper } from "./LiveWorkflowStepper";

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
            <LatencyPill
              ms={msg.latencyMs}
              promptTokens={msg.promptTokens}
              completionTokens={msg.completionTokens}
              costUsd={msg.costUsd}
              route={msg.route?.route}
            />
          </div>
        )}
        {!isUser && msg.streaming && msg.route && (
          <LiveWorkflowStepper
            route={msg.route}
            phase={msg.phase}
            phaseHistory={msg.phaseHistory}
          />
        )}
        {!isUser && !msg.streaming && msg.route && (
          <RouteExplainer route={msg.route} />
        )}
        {isUser ? (
          <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
        ) : (
          <div className="relative">
            <Markdown content={msg.content} />
            {msg.streaming && msg.content && (
              <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-accent/70 align-middle animate-pulse" />
            )}
          </div>
        )}
        {!isUser && !msg.streaming && msg.messageId && (
          <>
            <WorkflowDiagram
              route={msg.route}
              tenant={tenant}
              user={user}
              sessionId={sessionId}
              messageId={msg.messageId}
            />
            <MemoryWriteSummary
              tenant={tenant}
              user={user}
              sessionId={sessionId}
              messageId={msg.messageId}
            />
            <TracePanel
              tenant={tenant}
              user={user}
              sessionId={sessionId}
              messageId={msg.messageId}
            />
          </>
        )}
      </div>
    </div>
  );
}
