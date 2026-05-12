"use client";

import type { KeyboardEvent, RefObject } from "react";

import { EditorTextarea } from "../editor-textarea";

type EditorContentTextareaProps = {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  handleKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  disabled: boolean;
  placeholder: string;
  editorMaxWidth: string;
};

export function EditorContentTextarea({
  textareaRef,
  handleKeyDown,
  disabled,
  placeholder,
  editorMaxWidth,
}: EditorContentTextareaProps) {
  return (
    <EditorTextarea
      ref={textareaRef}
      handleKeyDown={handleKeyDown}
      disabled={disabled}
      placeholder={placeholder}
      className={`w-full ${editorMaxWidth} h-full p-8 md:p-12 resize-none bg-transparent outline-none text-lg leading-relaxed shadow-none border-none focus:ring-0 text-foreground/90 placeholder:text-muted-foreground/50 disabled:cursor-not-allowed`}
    />
  );
}
