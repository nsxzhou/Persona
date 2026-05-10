import type { NovelWorkflowListItem } from "@/lib/types";

export const WORKFLOW_INTENT_LABELS: Record<NovelWorkflowListItem["intent_type"], string> = {
  concept_bootstrap: "概念生成",
  memory_refresh: "记忆刷新",
  section_generate: "设定区块生成",
  volume_generate: "分卷生成",
  volume_chapters_generate: "章节细纲生成",
  selection_rewrite: "局部改写",
  chapter_enrichment_rewrite: "章节润色改写",
  imported_chapter_full_rewrite: "导入章节改写",
  beats_generate: "节拍生成",
  beat_expand: "节拍扩写",
  chapter_expand: "本章写作",
  prompt_asset_init: "Prompt 资产初始化",
};

export const WORKFLOW_STATUS_LABELS: Record<NovelWorkflowListItem["status"], string> = {
  pending: "等待中",
  running: "运行中",
  paused: "已暂停",
  succeeded: "成功",
  failed: "失败",
};

export function formatWorkflowDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
