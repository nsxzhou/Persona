import React from "react";

import { useEditorStore } from "./editor-context";

type EditorTextareaProps = {
  disabled: boolean;
  placeholder: string;
  className: string;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
};

export const EditorTextarea = React.memo(React.forwardRef<HTMLTextAreaElement, EditorTextareaProps>(({
  disabled,
  placeholder,
  className,
  handleKeyDown,
}, ref) => {
  const content = useEditorStore(s => s.content);
  const setContent = useEditorStore(s => s.setContent);

  return (
    <textarea
      ref={ref}
      value={content}
      onChange={(e) => setContent(e.target.value)}
      onKeyDown={handleKeyDown}
      disabled={disabled}
      placeholder={placeholder}
      className={className}
      style={{ fontFamily: "var(--font-serif), serif" }}
    />
  );
}));
EditorTextarea.displayName = "EditorTextarea";
