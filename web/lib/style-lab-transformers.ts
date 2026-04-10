import type { PromptPackFewShotSlot, StyleSummarySceneStrategy } from "@/lib/types";

export function linesToList(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function listToLines(values: string[]) {
  return values.join("\n");
}

export function sceneStrategiesToLines(values: StyleSummarySceneStrategy[]) {
  return values.map((item) => `${item.scene}: ${item.instruction}`).join("\n");
}

export function linesToSceneStrategies(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [scene, ...rest] = line.split(":");
      return {
        scene: scene.trim(),
        instruction: rest.join(":").trim() || "待补充说明",
      };
    });
}

export function fewShotSlotsToLines(values: PromptPackFewShotSlot[]) {
  return values
    .map((item) => `${item.label}|${item.type}|${item.purpose}|${item.text}`)
    .join("\n");
}

export function linesToFewShotSlots(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [label, type, purpose, ...rest] = line.split("|");
      return {
        label: label?.trim() || `slot-${index + 1}`,
        type: type?.trim() || "generic",
        purpose: purpose?.trim() || "补充风格示例",
        text: rest.join("|").trim() || line,
      };
    });
}

