"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { PropsWithChildren, useState } from "react";

import { TooltipProvider } from "@/components/ui/tooltip";

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  const scriptProps = typeof window === "undefined" ? undefined : ({ type: "application/json" } as const);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem scriptProps={scriptProps}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={150}>{children}</TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
