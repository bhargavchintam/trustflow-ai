"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

const COMPONENTS: Components = {
  p: ({ node, ...props }) => (
    <p className="mb-2 last:mb-0 leading-relaxed" {...props} />
  ),
  ul: ({ node, ...props }) => (
    <ul className="list-disc list-outside ml-5 space-y-0.5 mb-2 last:mb-0" {...props} />
  ),
  ol: ({ node, ...props }) => (
    <ol className="list-decimal list-outside ml-5 space-y-0.5 mb-2 last:mb-0" {...props} />
  ),
  li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
  strong: ({ node, ...props }) => (
    <strong className="font-semibold text-zinc-100" {...props} />
  ),
  em: ({ node, ...props }) => <em className="italic" {...props} />,
  a: ({ node, ...props }) => (
    <a
      className="text-accent underline underline-offset-2 hover:opacity-90"
      target="_blank"
      rel="noreferrer"
      {...props}
    />
  ),
  code: ({ node, className, children, ...props }: any) => {
    const isBlock = /language-/.test(className ?? "");
    if (isBlock) {
      return (
        <pre className="rounded bg-elevated p-2 my-2 overflow-x-auto text-[12px] border border-border">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      );
    }
    return (
      <code
        className="px-1 py-0.5 rounded bg-elevated text-accent text-[12px] font-mono"
        {...props}
      >
        {children}
      </code>
    );
  },
  blockquote: ({ node, ...props }) => (
    <blockquote
      className="border-l-2 border-accent/40 pl-3 my-2 text-muted italic"
      {...props}
    />
  ),
  table: ({ node, ...props }) => (
    <div className="overflow-x-auto my-2">
      <table className="text-xs border-collapse" {...props} />
    </div>
  ),
  th: ({ node, ...props }) => (
    <th className="border border-border px-2 py-1 bg-elevated text-left" {...props} />
  ),
  td: ({ node, ...props }) => (
    <td className="border border-border px-2 py-1" {...props} />
  ),
  hr: () => <hr className="my-3 border-border" />,
  h1: ({ node, ...props }) => (
    <h1 className="text-base font-semibold mt-3 mb-1.5" {...props} />
  ),
  h2: ({ node, ...props }) => (
    <h2 className="text-sm font-semibold mt-3 mb-1.5" {...props} />
  ),
  h3: ({ node, ...props }) => (
    <h3 className="text-sm font-semibold mt-2 mb-1" {...props} />
  ),
};

export function Markdown({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  return (
    <div className={cn("leading-relaxed text-sm", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTS}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
