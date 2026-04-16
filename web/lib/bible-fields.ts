export type BlueprintFieldKey =
  | "inspiration"
  | "world_building"
  | "characters"
  | "outline_master"
  | "outline_detail";

export type RuntimeFieldKey =
  | "runtime_state"
  | "runtime_threads";

export type BibleFieldKey = BlueprintFieldKey | RuntimeFieldKey;

export interface BibleSectionMeta {
  key: BibleFieldKey;
  title: string;
}

/** Ordered metadata for all story bible sections (blueprint + runtime). */
export const BIBLE_SECTION_META: BibleSectionMeta[] = [
  { key: "inspiration", title: "灵感概述" },
  { key: "world_building", title: "世界观设定" },
  { key: "characters", title: "角色卡" },
  { key: "outline_master", title: "总纲" },
  { key: "outline_detail", title: "分卷与章节细纲" },
  { key: "runtime_state", title: "运行时状态" },
  { key: "runtime_threads", title: "伏笔与线索追踪" },
];

export const BIBLE_FIELD_KEYS: readonly BibleFieldKey[] = BIBLE_SECTION_META.map(
  (s) => s.key,
);

/** Bible sections that support AI generation (everything except inspiration). */
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
  world_building: ["inspiration"],
  characters: ["inspiration", "world_building"],
  outline_master: ["inspiration", "world_building", "characters"],
  outline_detail: ["outline_master"],
  runtime_state: ["outline_master"],
  runtime_threads: ["outline_master"],
};
