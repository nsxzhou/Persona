import * as React from "react";
import { Slot } from "@radix-ui/react-slot";

import { cn } from "@/lib/utils";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
  variant?: "default" | "secondary" | "outline" | "ghost" | "destructive";
};

export function Button({
  asChild = false,
  className,
  variant = "default",
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : "button";

  return (
    <Comp
      className={cn(
        "inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        variant === "default" && "bg-stone-900 text-stone-50 hover:bg-stone-800 focus-visible:ring-stone-400",
        variant === "secondary" && "bg-stone-200 text-stone-900 hover:bg-stone-300 focus-visible:ring-stone-400",
        variant === "outline" && "border border-stone-300 bg-white text-stone-900 hover:bg-stone-100 focus-visible:ring-stone-400",
        variant === "ghost" && "bg-transparent text-stone-700 hover:bg-stone-100 focus-visible:ring-stone-400",
        variant === "destructive" && "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-400",
        className,
      )}
      {...props}
    />
  );
}

