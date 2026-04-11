import type { StyleSummarySceneStrategy } from "@/lib/types";

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
