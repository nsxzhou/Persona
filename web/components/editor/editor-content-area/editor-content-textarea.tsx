"use client";

import type { KeyboardEvent, RefObject, WheelEvent } from "react";

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
  const handleWheel = (event: WheelEvent<HTMLDivElement>) => {
    const textarea = textareaRef.current;
    if (!textarea || textarea.scrollHeight <= textarea.clientHeight) {
      return;
    }

    const previousScrollTop = textarea.scrollTop;
    textarea.scrollTop += event.deltaY;

    if (textarea.scrollTop !== previousScrollTop) {
      event.preventDefault();
    }
  };

  return (
    <div className="h-full w-full overflow-hidden" onWheel={handleWheel}>
      <EditorTextarea
        ref={textareaRef}
        handleKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        className={`mx-auto block h-full w-full ${editorMaxWidth} p-8 md:p-12 resize-none overflow-y-auto overflow-x-hidden bg-transparent outline-none text-lg leading-relaxed shadow-none border-none focus:ring-0 text-foreground/90 placeholder:text-muted-foreground/50 disabled:pointer-events-none disabled:cursor-not-allowed`}
      />
    </div>
  );
}
