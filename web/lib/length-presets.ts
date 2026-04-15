/**
 * 篇幅预设配置 — 与后端 api/app/core/length_presets.py 保持一致。
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
    description: "紧凑叙事，一个核心矛盾，适合单元故事",
    targetMin: 50_000,
    targetMax: 150_000,
    recommendedChapters: [8, 20],
    endingZoneRatio: 0.80,
  },
  medium: {
    label: "中篇",
    description: "多线叙事，2-4 卷结构，可以展开世界观",
    targetMin: 150_000,
    targetMax: 500_000,
    recommendedChapters: [30, 80],
    endingZoneRatio: 0.85,
  },
  long: {
    label: "长篇",
    description: "完整网文体量，分卷推进，深度世界构建",
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
