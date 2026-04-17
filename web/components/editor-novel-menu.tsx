"use client";

import Link from "next/link";
import { ArrowLeft, Home, BookOpen } from "lucide-react";

import { BIBLE_SECTION_META } from "@/lib/bible-fields";

type NovelMenuProps = {
  projectId: string;
  projectName: string;
  onNavigate?: () => void;
};

const GROUP_LABELS: Record<"blueprint" | "runtime", string> = {
  blueprint: "本书构思",
  runtime: "活态记忆",
};

export function EditorNovelMenu({ projectId, projectName, onNavigate }: NovelMenuProps) {
  const blueprint = BIBLE_SECTION_META.filter((section) => section.group === "blueprint");
  const runtime = BIBLE_SECTION_META.filter((section) => section.group === "runtime");

  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
        <BookOpen className="h-4 w-4 text-primary shrink-0" />
        <span className="truncate text-sm font-semibold" title={projectName}>
          {projectName}
        </span>
      </div>

      <Section title={GROUP_LABELS.blueprint}>
        {blueprint.map((section) => (
          <MenuLink
            key={section.key}
            href={`/projects/${projectId}?tab=${section.key}`}
            label={section.title}
            icon={section.icon}
            onNavigate={onNavigate}
          />
        ))}
      </Section>

      <Section title={GROUP_LABELS.runtime}>
        {runtime.map((section) => (
          <MenuLink
            key={section.key}
            href={`/projects/${projectId}?tab=${section.key}`}
            label={section.title}
            icon={section.icon}
            onNavigate={onNavigate}
          />
        ))}
      </Section>

      <div className="border-t border-border py-1">
        <MenuLink
          href={`/projects/${projectId}`}
          label="返回项目工作台"
          icon={ArrowLeft}
          onNavigate={onNavigate}
        />
        <MenuLink
          href="/projects"
          label="所有项目"
          icon={Home}
          onNavigate={onNavigate}
        />
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="py-1">
      <p className="px-3 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {title}
      </p>
      {children}
    </div>
  );
}

function MenuLink({
  href,
  label,
  icon: Icon,
  onNavigate,
}: {
  href: string;
  label: string;
  icon: typeof ArrowLeft;
  onNavigate?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="truncate">{label}</span>
    </Link>
  );
}
