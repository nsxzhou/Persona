export type BibleFieldKey =
  | "inspiration"
  | "world_building"
  | "characters"
  | "outline_master"
  | "outline_detail"
  | "story_bible";

export interface BibleSectionMeta {
  key: BibleFieldKey;
  title: string;
}

/** Ordered metadata for all six story bible sections. */
export const BIBLE_SECTION_META: BibleSectionMeta[] = [
  { key: "inspiration", title: "灵感概述" },
  { key: "world_building", title: "世界观设定" },
  { key: "characters", title: "角色卡" },
  { key: "outline_master", title: "总纲" },
  { key: "outline_detail", title: "分卷与章节细纲" },
  { key: "story_bible", title: "故事圣经补充" },
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
  "story_bible",
]);

/** Recommended prerequisite sections for AI generation quality. */
export const RECOMMENDED_PREREQUISITES: Partial<Record<BibleFieldKey, BibleFieldKey[]>> = {
  world_building: ["inspiration"],
  characters: ["inspiration", "world_building"],
  outline_master: ["inspiration", "world_building", "characters"],
  outline_detail: ["outline_master"],
  story_bible: ["outline_master"],
};
