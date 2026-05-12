"use client";

import UiwMarkdownPreview from "@uiw/react-markdown-preview";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

type MarkdownPreviewRendererProps = {
  content: string;
};

export function MarkdownPreviewRenderer({ content }: MarkdownPreviewRendererProps) {
  return (
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
  );
}
