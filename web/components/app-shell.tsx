"use client";

import Link from "next/link";
import { PropsWithChildren } from "react";
import { BookOpenText, FolderKanban, KeyRound, Sparkles, UserCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/projects", label: "项目", icon: FolderKanban },
  { href: "/settings/models", label: "模型配置", icon: KeyRound },
  { href: "/style-lab", label: "风格实验室", icon: Sparkles },
  { href: "/settings/account", label: "账户", icon: UserCircle2 },
];

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="flex min-h-screen bg-zinc-50 text-foreground">
      <aside className="fixed inset-y-0 z-10 flex w-64 flex-col border-r border-border bg-background">
        <div className="flex h-16 items-center px-6 border-b border-border">
          <BookOpenText className="mr-3 h-5 w-5" />
          <span className="font-semibold tracking-tight">Persona Studio</span>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-4">
          {navItems.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-all hover:bg-accent hover:text-accent-foreground hover:translate-x-1 border-l-4 border-transparent hover:border-primary"
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
      </aside>
      <main className="ml-64 flex-1 space-y-10 p-8">
        {children}
      </main>
    </div>
  );
}