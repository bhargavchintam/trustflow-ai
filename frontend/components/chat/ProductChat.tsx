"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { fetchHistory, streamChat } from "@/lib/api";
import type { ChatMessage, Identity, Role } from "@/lib/types";
import { getOrCreateSessionId, resetSessionId } from "@/lib/utils";
import { MessageBubble } from "./MessageBubble";

const SAMPLE_PROMPTS: { label: string; prompt: string }[] = [
  { label: "Reset my password", prompt: "reset my password" },
  { label: "Unlock my account", prompt: "I'm locked out of my account, please unlock it" },
  { label: "Reset MFA / 2FA", prompt: "reset my MFA, I got a new phone" },
  { label: "Request Figma access", prompt: "I need access to Figma" },
  { label: "Join a distribution list", prompt: "add me to the distribution list eng-leads" },
  { label: "VPN keeps dropping", prompt: "my VPN keeps dropping" },
  { label: "Email is slow", prompt: "my Outlook is really slow today" },
  { label: "Slack search broken", prompt: "Slack search isn't returning anything" },
  { label: "Zoom audio echo", prompt: "I'm hearing echo on every Zoom call" },
  { label: "Printer queue stuck", prompt: "the office printer is stuck on my job" },
  { label: "Git auth failing", prompt: "git push is asking for credentials again" },
  { label: "Wifi won't auto-connect", prompt: "my laptop won't reconnect to office wifi after sleep" },
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
    if (!sessionId) return;
    let cancelled = false;
    fetchHistory(identity.tenant_id, identity.user_id, sessionId)
      .then(({ messages: rows }) => {
        if (cancelled || rows.length === 0) return;
        const hydrated: ChatMessage[] = rows.map((r) => ({
          id: r.id,
          role: r.role as Role,
          content: r.content,
          messageId: undefined,
        }));
        setMessages((current) => (current.length === 0 ? hydrated : current));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [sessionId, identity.tenant_id, identity.user_id]);

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
          setMessages((m) =>
            m.map((msg) => {
              if (msg.id !== asstId) return msg;
              const history = msg.phaseHistory ?? [];
              const next = history[history.length - 1] === phase ? history : [...history, phase];
              return { ...msg, phase, phaseHistory: next };
            }),
          );
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
    } catch (e) {
      const message = e instanceof Error ? e.message : "request failed";
      setMessages((m) =>
        m.map((msg) =>
          msg.id === asstId
            ? {
                ...msg,
                content: `[error] ${message}`,
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
                Ask anything about IT.
              </div>
              <div className="text-xs">
                Password resets, software access, VPN issues, account lockouts. Your conversation is saved to memory.
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2 max-w-md mx-auto w-full">
              {SAMPLE_PROMPTS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => send(p.prompt)}
                  className="btn text-xs text-left"
                  title={p.prompt}
                >
                  <span className="truncate">{p.label}</span>
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
          <div className="text-xs text-muted mb-1.5">Red-team prompts (admin only):</div>
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
          placeholder="Ask TrustFlow AI…"
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
