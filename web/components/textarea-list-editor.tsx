"use client";

import * as React from "react";
import { Textarea } from "@/components/ui/textarea";

export interface TextareaListEditorProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  value: any;
  onChange: (value: any) => void;
  formatter: (value: any) => string;
  parser: (value: string) => any;
}

export function TextareaListEditor({ value, onChange, formatter, parser, ...props }: TextareaListEditorProps) {
  const [localValue, setLocalValue] = React.useState(() => formatter(value));

  React.useEffect(() => {
    setLocalValue(formatter(value));
  }, [value, formatter]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalValue(e.target.value);
  };

  const handleBlur = (e: React.FocusEvent<HTMLTextAreaElement>) => {
    const parsed = parser(localValue);
    onChange(parsed);
    if (props.onBlur) {
      props.onBlur(e);
    }
  };

  return (
    <Textarea
      value={localValue}
      onChange={handleChange}
      onBlur={handleBlur}
      {...props}
    />
  );
}
