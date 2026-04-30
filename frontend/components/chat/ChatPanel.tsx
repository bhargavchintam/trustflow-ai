"use client";

import { useEffect, useRef, useState } from "react";
import { streamChat } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { cn, getOrCreateSessionId, resetSessionId } from "@/lib/utils";
import { MessageBubble } from "./MessageBubble";

export function ChatPanel({
  tenant,
  user,
  label,
  forceRoute,
  onAfterSend,
  attackPrompts,
}: {
  tenant: string;
  user: string;
  label: string;
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
    setSessionId(getOrCreateSessionId(user));
  }, [user]);

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
        tenant,
        user,
        sessionId,
        input,
        forceRoute,
        onRoute: (route) => {
          setMessages((m) =>
            m.map((msg) => (msg.id === asstId ? { ...msg, route } : msg)),
          );
        },
        onPhase: (phase) => {
          setMessages((m) =>
            m.map((msg) => (msg.id === asstId ? { ...msg, phase } : msg)),
          );
        },
        onDelta: (text) => {
          setMessages((m) =>
            m.map((msg) =>
              msg.id === asstId ? { ...msg, content: msg.content + text } : msg,
            ),
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

  function clearLocal() {
    setMessages([]);
    setSessionId(resetSessionId(user));
  }

  const userBadge =
    user === "bob" ? "returning user" : user === "alice" ? "new user" : user;
  const userColor = user === "bob" ? "text-accent" : "text-zinc-300";

  return (
    <div className="flex flex-col h-full card">
      <div className="flex items-center justify-between mb-3 pb-3 border-b border-border">
        <div className="flex items-center gap-3">
          <div className={cn("text-base font-semibold", userColor)}>{label}</div>
          <span className="pill border-zinc-600 text-zinc-400 bg-zinc-800/40">
            {userBadge}
          </span>
          {forceRoute && (
            <span className="pill border-warn/50 text-warn bg-warn/10">
              force: {forceRoute}
            </span>
          )}
        </div>
        <button onClick={clearLocal} className="btn text-xs">
          Reset chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto pr-1 space-y-2 min-h-[200px]">
        {messages.length === 0 && (
          <div className="text-xs text-muted py-4">
            Type a prompt below — or pick a quick test:
            <div className="mt-2 flex flex-wrap gap-1.5">
              <button onClick={() => send("my VPN keeps dropping")} className="btn text-xs">
                my VPN keeps dropping
              </button>
              <button onClick={() => send("reset my password")} className="btn text-xs">
                reset my password
              </button>
              <button onClick={() => send("my email is slow")} className="btn text-xs">
                my email is slow
              </button>
            </div>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            msg={m}
            tenant={tenant}
            user={user}
            sessionId={sessionId}
          />
        ))}
        {loading && (
          <div className="text-xs text-muted px-1 py-2 animate-pulse">thinking…</div>
        )}
        <div ref={endRef} />
      </div>

      {attackPrompts && attackPrompts.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="text-xs text-muted mb-1.5">Red-team prompts:</div>
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
        className="mt-3 flex gap-2"
      >
        <input
          className="input flex-1"
          placeholder={`Message as ${label}…`}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !draft.trim()} className="btn-accent">
          Send
        </button>
      </form>
    </div>
  );
}
