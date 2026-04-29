"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { streamChat } from "@/lib/api";
import type { ChatMessage, Identity } from "@/lib/types";
import { cn, getOrCreateSessionId, resetSessionId } from "@/lib/utils";
import { MessageBubble } from "./MessageBubble";

const SAMPLE_PROMPTS: { label: string; prompt: string; route: "dag" | "react" }[] = [
  { label: "Reset my password", prompt: "reset my password", route: "dag" },
  { label: "Request Figma access", prompt: "I need access to Figma", route: "dag" },
  { label: "VPN keeps dropping", prompt: "my VPN keeps dropping", route: "react" },
  { label: "Email is slow", prompt: "my Outlook is really slow today", route: "react" },
  { label: "Slack search broken", prompt: "Slack search isn't returning anything", route: "react" },
  { label: "Zoom audio echo", prompt: "I'm hearing echo on every Zoom call", route: "react" },
  { label: "Printer queue stuck", prompt: "the office printer is stuck on my job", route: "react" },
  { label: "Git auth failing", prompt: "git push is asking for credentials again", route: "react" },
  { label: "Wifi won't auto-connect", prompt: "my laptop won't reconnect to office wifi after sleep", route: "react" },
  { label: "Teams calls dropping", prompt: "Teams keeps dropping calls", route: "react" },
];

export function ProductChat({
  identity,
  forceRoute,
  onAfterSend,
  attackPrompts,
}: {
  identity: Identity;
  forceRoute?: "dag" | "react";
  onAfterSend?: () => void;
  attackPrompts?: { label: string; prompt: string }[];
}) {
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(getOrCreateSessionId(identity.user_id));
  }, [identity.user_id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, loading]);

  async function send(input: string) {
    if (!input.trim() || loading || !sessionId) return;
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
    };
    const asstId = crypto.randomUUID();
    const asstSeed: ChatMessage = {
      id: asstId,
      role: "assistant",
      content: "",
      streaming: true,
    };
    setMessages((m) => [...m, userMsg, asstSeed]);
    setDraft("");
    setLoading(true);

    try {
      await streamChat({
        tenant: identity.tenant_id,
        user: identity.user_id,
        sessionId,
        input,
        forceRoute,
        onRoute: (route) => {
          setMessages((m) => m.map((msg) => (msg.id === asstId ? { ...msg, route } : msg)));
        },
        onPhase: (phase) => {
          setMessages((m) => m.map((msg) => (msg.id === asstId ? { ...msg, phase } : msg)));
        },
        onDelta: (text) => {
          setMessages((m) =>
            m.map((msg) => (msg.id === asstId ? { ...msg, content: msg.content + text } : msg)),
          );
        },
        onMessage: (final) => {
          setMessages((m) =>
            m.map((msg) =>
              msg.id === asstId
                ? {
                    ...msg,
                    content: final?.content ?? msg.content,
                    latencyMs: final?.latency_ms,
                    messageId: final?.message_id,
                    promptTokens: final?.prompt_tokens,
                    completionTokens: final?.completion_tokens,
                    costUsd: final?.cost_usd,
                    streaming: false,
                    phase: undefined,
                  }
                : msg,
            ),
          );
        },
      });
      onAfterSend?.();
    } catch (e: any) {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === asstId
            ? {
                ...msg,
                content: `[error] ${e?.message ?? "request failed"}`,
                streaming: false,
                phase: undefined,
              }
            : msg,
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  function newConversation() {
    setMessages([]);
    setSessionId(resetSessionId(identity.user_id));
  }

  return (
    <div className="card-elevated flex flex-col min-h-[70vh]">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
        <div>
          <div className="text-sm text-muted">Conversation</div>
          <div className="font-mono text-xs text-subtle truncate max-w-[260px]">
            {sessionId.slice(0, 18)}…
          </div>
        </div>
        <div className="flex items-center gap-2">
          {forceRoute && (
            <span className="pill border-warn/50 text-warn bg-warn/10">
              force: {forceRoute}
            </span>
          )}
          <button onClick={newConversation} className="btn text-xs">
            New conversation
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pr-1 space-y-3 min-h-[280px]">
        {messages.length === 0 && (
          <div className="h-full min-h-[260px] flex flex-col items-center justify-center text-center text-muted gap-3">
            <div className="w-10 h-10 rounded-full bg-accent/10 border border-accent/40 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-accent" />
            </div>
            <div className="space-y-1">
              <div className="text-zinc-200 text-sm font-medium">
                Ask the agent anything about IT.
              </div>
              <div className="text-xs">
                It'll route to a deterministic flow if it can, or reason through ReAct
                if it has to.
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2 max-w-md mx-auto w-full">
              {SAMPLE_PROMPTS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => send(p.prompt)}
                  className={cn(
                    "btn text-xs text-left flex items-center justify-between gap-2",
                    p.route === "dag" && "border-accent/40",
                  )}
                  title={p.prompt}
                >
                  <span className="truncate">{p.label}</span>
                  <span
                    className={cn(
                      "pill text-[10px] shrink-0",
                      p.route === "dag"
                        ? "border-accent/50 text-accent bg-accent/10"
                        : "border-zinc-600 text-zinc-400 bg-zinc-800/40",
                    )}
                  >
                    {p.route === "dag" ? "DAG" : "ReAct"}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            msg={m}
            tenant={identity.tenant_id}
            user={identity.user_id}
            sessionId={sessionId}
          />
        ))}
        {loading && messages[messages.length - 1]?.streaming === true && null}
        <div ref={endRef} />
      </div>

      {attackPrompts && attackPrompts.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="text-xs text-muted mb-1.5">Attack the agent (admin):</div>
          <div className="flex flex-wrap gap-1.5">
            {attackPrompts.map((a) => (
              <button
                key={a.label}
                onClick={() => send(a.prompt)}
                className="btn text-xs border-deny/40 text-deny/90 hover:bg-deny/10"
                title={a.prompt}
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
        className="mt-4 flex gap-2"
      >
        <input
          className="input flex-1"
          placeholder={`Message TrustFlow AI as ${identity.user_id}…`}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !draft.trim()}
          className="btn-accent inline-flex items-center gap-1.5"
        >
          <Send className="w-4 h-4" />
          Send
        </button>
      </form>
    </div>
  );
}
