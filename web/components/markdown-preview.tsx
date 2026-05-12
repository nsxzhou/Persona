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
      className="rounded-md border border-dashed p-4 text-sm text-muted-foreground"
      style={{ minHeight: 96 }}
    >
      正在载入预览...
    </div>
  );
}
