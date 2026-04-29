import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrustFlow AI — Atomicwork Demo",
  description:
    "Hybrid DAG + ReAct IT support agent with 3-tier persistent memory, policy-gated tools, and traceable evaluation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
