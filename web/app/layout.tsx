import type { Metadata } from "next";

import { AppProviders } from "@/components/app-providers";
import { Toaster } from "@/components/ui/sonner";

import "./globals.css";

export const metadata: Metadata = {
  title: "Persona",
  description: "Single-user AI novel creation platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="font-sans">
        <AppProviders>
          {children}
          <Toaster position="top-center" />
        </AppProviders>
      </body>
    </html>
  );
}
