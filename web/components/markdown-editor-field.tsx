"use client";

import * as React from "react";
import { useController, type Control, type FieldPath } from "react-hook-form";

import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";

type MarkdownEditorFieldProps<TFieldValues extends Record<string, unknown>> = {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
  id: string;
  label: string;
  ariaLabel?: string;
  minHeight: number;
};

export function MarkdownEditorField<TFieldValues extends Record<string, unknown>>({
  control,
  name,
  id,
  label,
  ariaLabel,
  minHeight,
}: MarkdownEditorFieldProps<TFieldValues>) {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const { field } = useController({
    name,
    control,
  });

  const handleRef = React.useCallback(
    (element: HTMLTextAreaElement | null) => {
      field.ref(element);
      textareaRef.current = element;
    },
    [field],
  );

  const handleResize = React.useCallback(() => {
    const target = textareaRef.current;
    if (!target) return;
    target.style.height = "auto";
    target.style.height = `${Math.max(minHeight, target.scrollHeight)}px`;
  }, [minHeight]);

  React.useEffect(() => {
    handleResize();
  }, [field.value, handleResize]);

  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <ScrollArea
        className="w-full rounded-md border border-input bg-background"
        style={{ height: minHeight }}
        type="auto"
      >
        <Textarea
          id={id}
          aria-label={ariaLabel}
          className="w-full resize-none border-0 focus-visible:ring-0 focus-visible:ring-offset-0 p-4 font-mono text-sm overflow-hidden"
          style={{ minHeight }}
          {...field}
          value={(field.value as string | undefined) ?? ""}
          ref={handleRef}
          onInput={(event) => {
            field.onChange(event);
            handleResize();
          }}
        />
      </ScrollArea>
    </div>
  );
}
