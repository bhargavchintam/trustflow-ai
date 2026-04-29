"use client";

import { useState } from "react";
import Link from "next/link";
import { reseedAll, wipeUser, warmup } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/utils";

export function DemoControls({
  forceReact,
  onForceReactChange,
  onAfterReseed,
  onAfterWipe,
}: {
  forceReact: boolean;
  onForceReactChange: (v: boolean) => void;
  onAfterReseed: () => void;
  onAfterWipe: () => void;
}) {
  const [working, setWorking] = useState<string | null>(null);

  async function reseed() {
    setWorking("reseed");
    await reseedAll();
    setWorking(null);
    onAfterReseed();
  }

  async function wipeAll() {
    setWorking("wipe");
    await Promise.all([
      wipeUser("tenant_acme", "alice", getOrCreateSessionId("alice")),
      wipeUser("tenant_acme", "bob", getOrCreateSessionId("bob")),
    ]);
    setWorking(null);
    onAfterWipe();
  }

  return (
    <div className="card flex flex-wrap items-center gap-3">
      <button onClick={reseed} disabled={working !== null} className="btn">
        {working === "reseed" ? "Reseeding…" : "Reseed Bob"}
      </button>
      <button onClick={wipeAll} disabled={working !== null} className="btn">
        {working === "wipe" ? "Wiping…" : "Wipe Alice + Bob"}
      </button>
      <button onClick={() => warmup()} className="btn">
        Warm up
      </button>
      <label className="flex items-center gap-2 text-sm cursor-pointer">
        <input
          type="checkbox"
          checked={forceReact}
          onChange={(e) => onForceReactChange(e.target.checked)}
          className="accent-accent"
        />
        <span>Force ReAct (bypass DAG router)</span>
      </label>
      <div className="grow" />
      <Link href="/eval" className="btn-accent">
        View eval dashboard →
      </Link>
    </div>
  );
}
