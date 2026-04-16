"use client";

import UiwMarkdownPreview from "@uiw/react-markdown-preview";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

interface MarkdownPreviewProps {
  content: string;
  className?: string;
}

export function MarkdownPreview({ content, className }: MarkdownPreviewProps) {
  if (!content.trim()) {
    return <p className="text-muted-foreground text-sm">(empty)</p>;
  }

  return (
    <div className={className}>
      <UiwMarkdownPreview
        source={content}
        rehypePlugins={[
          [
            rehypeSanitize,
            {
              ...defaultSchema,
              attributes: {
                ...defaultSchema.attributes,
                "*": [...(defaultSchema.attributes?.["*"] ?? []), "className"],
              },
            },
          ],
        ]}
        style={{ backgroundColor: "transparent" }}
        wrapperElement={{ "data-color-mode": "light" }}
      />
    </div>
  );
}
