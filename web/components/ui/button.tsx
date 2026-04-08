import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
  variant?: "default" | "secondary" | "outline" | "ghost" | "destructive";
};

export function Button({ asChild = false, className, variant = "default", ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(
        "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
        variant === "default" && "bg-primary text-primary-foreground hover:bg-primary/90 shadow",
        variant === "secondary" && "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        variant === "outline" && "border border-border bg-background hover:bg-accent hover:text-accent-foreground",
        variant === "ghost" && "hover:bg-accent hover:text-accent-foreground",
        variant === "destructive" && "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        className,
      )}
      {...props}
    />
  );
}
