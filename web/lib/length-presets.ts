/**
 * 篇幅预设配置。
 *
 * 数值范围需与后端 api/app/core/length_presets.py 保持一致；
 * description 展示文案需与 api/app/prompts/novel_shared.py 中的 LENGTH_HINT_LABELS 保持同步。
 */

export type LengthPresetKey = "short" | "medium" | "long";

export type ProgressPhase = "writing" | "ending_zone" | "over_target";

export interface LengthPresetConfig {
  label: string;
  description: string;
  targetMin: number;
  targetMax: number;
  recommendedChapters: [number, number];
  endingZoneRatio: number;
}

export const LENGTH_PRESETS: Record<LengthPresetKey, LengthPresetConfig> = {
  short: {
    label: "短篇",
    description: "预计体量偏短，几万或者十几万字",
    targetMin: 50_000,
    targetMax: 150_000,
    recommendedChapters: [8, 20],
    endingZoneRatio: 0.80,
  },
  medium: {
    label: "中篇",
    description: "预计体量中等，几十万字",
    targetMin: 150_000,
    targetMax: 500_000,
    recommendedChapters: [30, 80],
    endingZoneRatio: 0.85,
  },
  long: {
    label: "长篇",
    description: "预计体量偏长，百万字",
    targetMin: 500_000,
    targetMax: 2_000_000,
    recommendedChapters: [100, 400],
    endingZoneRatio: 0.90,
  },
};

export interface LengthProgress {
  currentChars: number;
  targetMin: number;
  targetMax: number;
  percentage: number;
  phase: ProgressPhase;
}

export function getProgress(
  contentLength: number,
  presetKey: LengthPresetKey,
): LengthProgress {
  const cfg = LENGTH_PRESETS[presetKey];
  const pct = contentLength / cfg.targetMax;
  let phase: ProgressPhase;
  if (pct >= 1.0) {
    phase = "over_target";
  } else if (pct >= cfg.endingZoneRatio) {
    phase = "ending_zone";
  } else {
    phase = "writing";
  }
  return {
    currentChars: contentLength,
    targetMin: cfg.targetMin,
    targetMax: cfg.targetMax,
    percentage: Math.round(pct * 1000) / 10, // 1 decimal place
    phase,
  };
}
