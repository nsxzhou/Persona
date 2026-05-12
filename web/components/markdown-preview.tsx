"use client";

import { lazy, Suspense } from "react";

interface MarkdownPreviewProps {
  content: string;
  className?: string;
}

const MarkdownPreviewRenderer = lazy(
  () =>
    import("@/components/markdown-preview-renderer").then(
      (module) => ({ default: module.MarkdownPreviewRenderer }),
    ),
);

export function MarkdownPreview({ content, className }: MarkdownPreviewProps) {
  if (!content.trim()) {
    return <p className="text-muted-foreground text-sm">(empty)</p>;
  }

  return (
    <div className={className} style={{ minHeight: 96 }}>
      <Suspense fallback={<MarkdownPreviewFallback />}>
        <MarkdownPreviewRenderer content={content} />
      </Suspense>
    </div>
  );
}

function MarkdownPreviewFallback() {
  return (
    <div
      className="motion-panel space-y-3 rounded-md border border-dashed p-4"
      style={{ minHeight: 96 }}
      aria-busy="true"
      aria-live="polite"
    >
      <div className="h-3 w-1/2 animate-pulse rounded-sm bg-muted" />
      <div className="h-3 w-full animate-pulse rounded-sm bg-muted motion-delay-1" />
      <div className="h-3 w-4/5 animate-pulse rounded-sm bg-muted motion-delay-2" />
      <span className="sr-only">正在载入预览...</span>
    </div>
  );
}
