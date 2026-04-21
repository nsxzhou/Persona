import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  Globe,
  Users,
  ScrollText,
  ListTree,
  Activity,
  Link2,
} from "lucide-react";

export type BlueprintFieldKey =
  | "description"
  | "world_building"
  | "characters"
  | "outline_master"
  | "outline_detail";

export type RuntimeFieldKey =
  | "runtime_state"
  | "runtime_threads";

export type BibleFieldKey = BlueprintFieldKey | RuntimeFieldKey;

export type BibleSectionGroup = "blueprint" | "runtime";

export interface BibleSectionMeta {
  key: BibleFieldKey;
  title: string;
  icon: LucideIcon;
  group: BibleSectionGroup;
}

/** Ordered metadata for all story bible sections (blueprint + runtime). */
export const BIBLE_SECTION_META: BibleSectionMeta[] = [
  { key: "description", title: "简介", icon: BookOpen, group: "blueprint" },
  { key: "world_building", title: "世界观设定", icon: Globe, group: "blueprint" },
  { key: "characters", title: "角色卡", icon: Users, group: "blueprint" },
  { key: "outline_master", title: "总纲", icon: ScrollText, group: "blueprint" },
  { key: "outline_detail", title: "分卷与章节细纲", icon: ListTree, group: "blueprint" },
  { key: "runtime_state", title: "运行时状态", icon: Activity, group: "runtime" },
  { key: "runtime_threads", title: "伏笔与线索追踪", icon: Link2, group: "runtime" },
];

export const BIBLE_FIELD_KEYS: readonly BibleFieldKey[] = BIBLE_SECTION_META.map(
  (s) => s.key,
);

/** Bible sections that support AI generation (everything except description). */
export const AI_ENABLED_SECTIONS: ReadonlySet<BibleFieldKey> = new Set([
  "world_building",
  "characters",
  "outline_master",
  "outline_detail",
  "runtime_state",
  "runtime_threads",
]);

/** Runtime fields that AI automatically proposes updates for after writing. */
export const RUNTIME_FIELD_KEYS: readonly RuntimeFieldKey[] = [
  "runtime_state",
  "runtime_threads",
];

/** Recommended prerequisite sections for AI generation quality. */
export const RECOMMENDED_PREREQUISITES: Partial<Record<BibleFieldKey, BibleFieldKey[]>> = {
  world_building: ["description"],
  characters: ["description", "world_building"],
  outline_master: ["description", "world_building", "characters"],
  outline_detail: ["outline_master"],
  runtime_state: ["outline_master"],
  runtime_threads: ["outline_master"],
};
