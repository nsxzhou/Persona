"use client";

import Link from "next/link";
import { PropsWithChildren } from "react";
import { BookOpenText, FolderKanban, KeyRound, Sparkles, UserCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/settings/models", label: "Model Configs", icon: KeyRound },
  { href: "/style-lab", label: "Style Lab", icon: Sparkles },
  { href: "/settings/account", label: "Account", icon: UserCircle2 },
];

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(214,211,209,0.42),_transparent_28%),linear-gradient(180deg,#faf7f2_0%,#f4efe7_100%)] text-stone-900">
      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-6 px-4 py-4 lg:px-6">
        <aside className="hidden w-72 shrink-0 rounded-[28px] border border-stone-200 bg-white/80 p-6 shadow-sm backdrop-blur lg:flex lg:flex-col">
          <div className="flex items-center gap-3 border-b border-stone-100 pb-5">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-stone-900 text-stone-50">
              <BookOpenText className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.28em] text-stone-400">Persona</div>
              <div className="text-lg font-semibold">Single-user Studio</div>
            </div>
          </div>
          <nav className="mt-6 space-y-2">
            {navItems.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-stone-600 transition hover:bg-stone-100 hover:text-stone-950",
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </Link>
            ))}
          </nav>
          <div className="mt-auto rounded-2xl border border-stone-200 bg-stone-50 p-4 text-sm text-stone-600">
            基础平台已就绪，后续可直接接入 Style Lab 与 LangGraph 长任务。
          </div>
        </aside>
        <main className="min-w-0 flex-1 rounded-[32px] border border-stone-200 bg-white/70 p-4 shadow-sm backdrop-blur lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

